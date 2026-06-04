"""L08 · 威胁情报 IoC（ioc_correlation 的数据 + 匹配）。

IoC（域名 / IP / 哈希 / URL）维护 + 与告警匹配。命中即在告警上标红、给 IoC 计数。
自用阶段手维护（可后续接 TI 源）。仓储模式，与告警/工单一致。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel

IOC_TYPES = ("域名", "IP", "哈希", "URL")


class IoC(BaseModel):
    id: str
    value: str
    type: str = "IP"  # 域名 / IP / 哈希 / URL
    severity: str = "高"  # 高 / 中 / 低
    note: str = ""
    hits: int = 0


def match_iocs(fields: dict[str, Any], iocs: list[IoC]) -> list[IoC]:
    """该告警命中的 IoC（值出现在 主机/标题 文本里）。"""
    haystack = f"{fields.get('host', '')} {fields.get('title', '')} {fields.get('source', '')}".lower()
    return [i for i in iocs if i.value and i.value.lower() in haystack]


class IocStore(ABC):
    @abstractmethod
    def all(self) -> list[IoC]:
        raise NotImplementedError

    @abstractmethod
    def create(self, value: str, type: str, severity: str, note: str) -> IoC:
        raise NotImplementedError

    @abstractmethod
    def remove(self, ioc_id: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def bump_hit(self, ioc_id: str) -> None:
        raise NotImplementedError


class InMemoryIocStore(IocStore):
    def __init__(self) -> None:
        self._items: list[IoC] = []

    def all(self) -> list[IoC]:
        return list(self._items)

    def create(self, value: str, type: str, severity: str, note: str) -> IoC:
        seq = len(self._items) + 1
        i = IoC(id=f"IOC-{seq}", value=value, type=type, severity=severity, note=note)
        self._items.append(i)
        return i

    def remove(self, ioc_id: str) -> bool:
        before = len(self._items)
        self._items = [x for x in self._items if x.id != ioc_id]
        return len(self._items) < before

    def bump_hit(self, ioc_id: str) -> None:
        i = next((x for x in self._items if x.id == ioc_id), None)
        if i is not None:
            i.hits += 1


class PgIocStore(IocStore):
    _COLS = "seq, value, type, severity, note, hits"

    def __init__(self, database_url: str) -> None:
        from aisecops.L12_core_support.db import get_pool

        self._pool = get_pool(database_url)
        with self._pool.connection() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS iocs ("
                "seq SERIAL PRIMARY KEY, value text, type text, severity text, note text, hits integer DEFAULT 0)"
            )

    @staticmethod
    def _to_ioc(r: Any) -> IoC:
        return IoC(
            id=f"IOC-{int(r[0])}", value=r[1], type=r[2], severity=r[3] or "高", note=r[4] or "", hits=int(r[5] or 0)
        )

    @staticmethod
    def _seq_of(iid: str) -> int:
        try:
            return int(iid.split("-")[1])
        except (ValueError, IndexError):
            return -1

    def all(self) -> list[IoC]:
        with self._pool.connection() as conn:
            rows = conn.execute(f"SELECT {self._COLS} FROM iocs ORDER BY seq DESC").fetchall()
        return [self._to_ioc(r) for r in rows]

    def create(self, value: str, type: str, severity: str, note: str) -> IoC:
        with self._pool.connection() as conn:
            row = conn.execute(
                "INSERT INTO iocs (value, type, severity, note) VALUES (%s,%s,%s,%s) RETURNING seq",
                (value, type, severity, note),
            ).fetchone()
        seq = int(row[0]) if row else 0
        return IoC(id=f"IOC-{seq}", value=value, type=type, severity=severity, note=note)

    def remove(self, ioc_id: str) -> bool:
        with self._pool.connection() as conn:
            cur = conn.execute("DELETE FROM iocs WHERE seq=%s", (self._seq_of(ioc_id),))
            return bool(cur.rowcount)

    def bump_hit(self, ioc_id: str) -> None:
        with self._pool.connection() as conn:
            conn.execute("UPDATE iocs SET hits = hits + 1 WHERE seq=%s", (self._seq_of(ioc_id),))


def build_ioc_store(database_url: str = "") -> IocStore:
    if database_url:
        try:
            return PgIocStore(database_url)
        except Exception:
            pass
    return InMemoryIocStore()


def seed_demo_iocs(store: IocStore) -> None:
    if store.all():
        return
    store.create("evil-c2.top", "域名", "高", "已知 C2 域名")
    store.create("185.220", "IP", "高", "Tor 出口段")
    store.create("PsExec", "哈希", "中", "横向移动工具特征")
