"""L11 · 资产 CMDB（被监测资产清单）。

自用阶段手填（ADR-0010：CMDB 暂不接外部，先手维护）。资产的「重要度」会被分诊引用——
关键资产上的告警自动升级为高风险（走双模型 cross-check），这是"分诊用到重要度"的落点。
仓储模式，与告警/工单一致。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel

IMPORTANCE = ("关键", "高", "中", "低")
STATUS = ("正常", "观察", "已隔离", "下线")


class Asset(BaseModel):
    id: str
    host: str
    ip: str = ""
    role: str = ""  # 域控 / 应用服务器 / 开发机 ...
    importance: str = "中"  # 关键 / 高 / 中 / 低
    status: str = "正常"  # 正常 / 观察 / 已隔离 / 下线
    owner: str = ""
    note: str = ""


class AssetStore(ABC):
    @abstractmethod
    def all(self) -> list[Asset]:
        raise NotImplementedError

    @abstractmethod
    def get_by_host(self, host: str) -> Asset | None:
        """按主机名查（分诊富化用）。"""
        raise NotImplementedError

    @abstractmethod
    def create(self, host: str, ip: str, role: str, importance: str, status: str, owner: str, note: str) -> Asset:
        raise NotImplementedError

    @abstractmethod
    def update(self, asset_id: str, fields: dict[str, Any]) -> Asset | None:
        raise NotImplementedError

    @abstractmethod
    def remove(self, asset_id: str) -> bool:
        raise NotImplementedError


_EDITABLE = ("host", "ip", "role", "importance", "status", "owner", "note")


class InMemoryAssetStore(AssetStore):
    def __init__(self) -> None:
        self._items: list[Asset] = []

    def all(self) -> list[Asset]:
        return list(self._items)

    def get_by_host(self, host: str) -> Asset | None:
        return next((a for a in self._items if a.host == host), None)

    def create(self, host: str, ip: str, role: str, importance: str, status: str, owner: str, note: str) -> Asset:
        seq = len(self._items) + 1
        a = Asset(
            id=f"AST-{seq}", host=host, ip=ip, role=role, importance=importance, status=status, owner=owner, note=note
        )
        self._items.append(a)
        return a

    def update(self, asset_id: str, fields: dict[str, Any]) -> Asset | None:
        a = next((x for x in self._items if x.id == asset_id), None)
        if a is None:
            return None
        for k in _EDITABLE:
            if k in fields and fields[k] is not None:
                setattr(a, k, str(fields[k]))
        return a

    def remove(self, asset_id: str) -> bool:
        before = len(self._items)
        self._items = [x for x in self._items if x.id != asset_id]
        return len(self._items) < before


class PgAssetStore(AssetStore):
    _COLS = "seq, host, ip, role, importance, status, owner, note"

    def __init__(self, database_url: str) -> None:
        from aisecops.L12_core_support.db import get_pool

        self._pool = get_pool(database_url)
        with self._pool.connection() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS assets ("
                "seq SERIAL PRIMARY KEY, host text, ip text, role text, importance text, "
                "status text, owner text, note text)"
            )

    @staticmethod
    def _to_asset(r: Any) -> Asset:
        return Asset(
            id=f"AST-{int(r[0])}",
            host=r[1],
            ip=r[2] or "",
            role=r[3] or "",
            importance=r[4] or "中",
            status=r[5] or "正常",
            owner=r[6] or "",
            note=r[7] or "",
        )

    @staticmethod
    def _seq_of(aid: str) -> int:
        try:
            return int(aid.split("-")[1])
        except (ValueError, IndexError):
            return -1

    def all(self) -> list[Asset]:
        with self._pool.connection() as conn:
            rows = conn.execute(f"SELECT {self._COLS} FROM assets ORDER BY seq").fetchall()
        return [self._to_asset(r) for r in rows]

    def get_by_host(self, host: str) -> Asset | None:
        with self._pool.connection() as conn:
            row = conn.execute(f"SELECT {self._COLS} FROM assets WHERE host=%s LIMIT 1", (host,)).fetchone()
        return self._to_asset(row) if row else None

    def create(self, host: str, ip: str, role: str, importance: str, status: str, owner: str, note: str) -> Asset:
        with self._pool.connection() as conn:
            row = conn.execute(
                "INSERT INTO assets (host, ip, role, importance, status, owner, note) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING seq",
                (host, ip, role, importance, status, owner, note),
            ).fetchone()
        seq = int(row[0]) if row else 0
        return Asset(
            id=f"AST-{seq}", host=host, ip=ip, role=role, importance=importance, status=status, owner=owner, note=note
        )

    def update(self, asset_id: str, fields: dict[str, Any]) -> Asset | None:
        seq = self._seq_of(asset_id)
        sets = [(k, str(fields[k])) for k in _EDITABLE if k in fields and fields[k] is not None]
        if not sets:
            with self._pool.connection() as conn:
                row = conn.execute(f"SELECT {self._COLS} FROM assets WHERE seq=%s", (seq,)).fetchone()
            return self._to_asset(row) if row else None
        clause = ", ".join(f"{k}=%s" for k, _ in sets)
        params = [v for _, v in sets] + [seq]
        with self._pool.connection() as conn:
            conn.execute(f"UPDATE assets SET {clause} WHERE seq=%s", params)
            row = conn.execute(f"SELECT {self._COLS} FROM assets WHERE seq=%s", (seq,)).fetchone()
        return self._to_asset(row) if row else None

    def remove(self, asset_id: str) -> bool:
        with self._pool.connection() as conn:
            cur = conn.execute("DELETE FROM assets WHERE seq=%s", (self._seq_of(asset_id),))
            return bool(cur.rowcount)


def build_asset_store(database_url: str = "") -> AssetStore:
    if database_url:
        try:
            return PgAssetStore(database_url)
        except Exception:
            pass
    return InMemoryAssetStore()


def seed_demo_assets(store: AssetStore) -> None:
    if store.all():
        return
    store.create("DC-01", "10.0.0.10", "域控", "关键", "正常", "运维组", "AD 域控，最高优先级")
    store.create("WIN-APP-07", "10.0.2.7", "应用服务器", "高", "已隔离", "应用组", "核心业务应用")
    store.create("DEV-12", "10.0.3.12", "开发机", "中", "观察", "研发组", "")
