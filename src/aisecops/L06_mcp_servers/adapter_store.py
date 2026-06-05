"""L06 · 工具适配器注册（增删改 / 启停 / 连通测试）。

L06 是所有出站调用的治理边界（ADR-0004 薄适配器）。这里把"有哪些适配器、启停、能不能
连通"做成可维护的清单。连通测试是真发一次轻量探测（受出域开关约束，外网端点关时不探）。
仓储模式，与告警/工单一致。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import httpx
from pydantic import BaseModel

from aisecops.L12_core_support.net_guard import is_outbound_url, ssrf_guard

# 出域判定与 L05 同口径（C-32），统一走 L12 net_guard（修正 10.example.com 误判）
_is_outbound = is_outbound_url


# 六大类（ADR-0004）：数据源 / 安全工具 / 协议 / 厂商 / AIOps / 自定义
CATEGORIES = ("data_sources", "security_tools", "protocols", "vendors", "aiops", "custom")

# 日志/数据源接入的已知种类（接入管理 catalog）
LOG_SOURCE_KINDS = ("elasticsearch", "opensearch", "zabbix", "syslog", "kafka", "loki", "generic_http")
# 已具备真实查询适配器的种类；其余为"已登记 + 可连通测试"，查询适配器随用随接（ADR-0009 日志留到最后）
QUERYABLE_KINDS = ("elasticsearch",)


class Adapter(BaseModel):
    id: str
    name: str
    category: str = "data_sources"
    kind: str = ""  # elasticsearch / siem / edr / firewall / wechat ...
    endpoint: str = ""  # 探测地址（密钥不在此）
    enabled: bool = True
    last_status: str = "未测"  # 未测 / 已连 / 失败 / 未配置
    last_tested: str = ""


class AdapterStore(ABC):
    @abstractmethod
    def all(self) -> list[Adapter]:
        raise NotImplementedError

    @abstractmethod
    def get(self, adapter_id: str) -> Adapter | None:
        raise NotImplementedError

    @abstractmethod
    def create(self, name: str, category: str, kind: str, endpoint: str) -> Adapter:
        raise NotImplementedError

    @abstractmethod
    def set_enabled(self, adapter_id: str, enabled: bool) -> Adapter | None:
        raise NotImplementedError

    @abstractmethod
    def set_status(self, adapter_id: str, status: str, ts: str) -> Adapter | None:
        raise NotImplementedError

    @abstractmethod
    def remove(self, adapter_id: str) -> bool:
        raise NotImplementedError


class InMemoryAdapterStore(AdapterStore):
    def __init__(self) -> None:
        self._items: list[Adapter] = []

    def all(self) -> list[Adapter]:
        return list(self._items)

    def get(self, adapter_id: str) -> Adapter | None:
        return next((a for a in self._items if a.id == adapter_id), None)

    def create(self, name: str, category: str, kind: str, endpoint: str) -> Adapter:
        seq = len(self._items) + 1
        a = Adapter(id=f"ADP-{seq}", name=name, category=category, kind=kind, endpoint=endpoint)
        self._items.append(a)
        return a

    def set_enabled(self, adapter_id: str, enabled: bool) -> Adapter | None:
        a = self.get(adapter_id)
        if a is not None:
            a.enabled = enabled
        return a

    def set_status(self, adapter_id: str, status: str, ts: str) -> Adapter | None:
        a = self.get(adapter_id)
        if a is not None:
            a.last_status = status
            a.last_tested = ts
        return a

    def remove(self, adapter_id: str) -> bool:
        before = len(self._items)
        self._items = [a for a in self._items if a.id != adapter_id]
        return len(self._items) < before


class PgAdapterStore(AdapterStore):
    _COLS = "seq, name, category, kind, endpoint, enabled, last_status, last_tested"

    def __init__(self, database_url: str) -> None:
        from aisecops.L12_core_support.db import get_pool

        self._pool = get_pool(database_url)
        with self._pool.connection() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS adapters ("
                "seq SERIAL PRIMARY KEY, name text, category text, kind text, endpoint text, "
                "enabled boolean DEFAULT true, last_status text DEFAULT '未测', last_tested text DEFAULT '')"
            )

    @staticmethod
    def _to_adapter(r: Any) -> Adapter:
        return Adapter(
            id=f"ADP-{int(r[0])}",
            name=r[1],
            category=r[2] or "data_sources",
            kind=r[3] or "",
            endpoint=r[4] or "",
            enabled=bool(r[5]),
            last_status=r[6] or "未测",
            last_tested=r[7] or "",
        )

    @staticmethod
    def _seq_of(aid: str) -> int:
        try:
            return int(aid.split("-")[1])
        except (ValueError, IndexError):
            return -1

    def all(self) -> list[Adapter]:
        with self._pool.connection() as conn:
            rows = conn.execute(f"SELECT {self._COLS} FROM adapters ORDER BY seq").fetchall()
        return [self._to_adapter(r) for r in rows]

    def get(self, adapter_id: str) -> Adapter | None:
        with self._pool.connection() as conn:
            row = conn.execute(
                f"SELECT {self._COLS} FROM adapters WHERE seq=%s", (self._seq_of(adapter_id),)
            ).fetchone()
        return self._to_adapter(row) if row else None

    def create(self, name: str, category: str, kind: str, endpoint: str) -> Adapter:
        with self._pool.connection() as conn:
            row = conn.execute(
                "INSERT INTO adapters (name, category, kind, endpoint) VALUES (%s,%s,%s,%s) RETURNING seq",
                (name, category, kind, endpoint),
            ).fetchone()
        seq = int(row[0]) if row else 0
        return Adapter(id=f"ADP-{seq}", name=name, category=category, kind=kind, endpoint=endpoint)

    def set_enabled(self, adapter_id: str, enabled: bool) -> Adapter | None:
        seq = self._seq_of(adapter_id)
        with self._pool.connection() as conn:
            conn.execute("UPDATE adapters SET enabled=%s WHERE seq=%s", (enabled, seq))
            row = conn.execute(f"SELECT {self._COLS} FROM adapters WHERE seq=%s", (seq,)).fetchone()
        return self._to_adapter(row) if row else None

    def set_status(self, adapter_id: str, status: str, ts: str) -> Adapter | None:
        seq = self._seq_of(adapter_id)
        with self._pool.connection() as conn:
            conn.execute("UPDATE adapters SET last_status=%s, last_tested=%s WHERE seq=%s", (status, ts, seq))
            row = conn.execute(f"SELECT {self._COLS} FROM adapters WHERE seq=%s", (seq,)).fetchone()
        return self._to_adapter(row) if row else None

    def remove(self, adapter_id: str) -> bool:
        with self._pool.connection() as conn:
            cur = conn.execute("DELETE FROM adapters WHERE seq=%s", (self._seq_of(adapter_id),))
            return bool(cur.rowcount)


def test_connectivity(adapter: Adapter, outbound_enabled: bool, now: str) -> str:
    """轻量连通探测。无端点→未配置；外网端点但出域关→跳过；否则真探一次。"""
    if not adapter.endpoint:
        return "未配置"
    if _is_outbound(adapter.endpoint) and not outbound_enabled:
        return "跳过（出域关）"
    # C-22 防 SSRF：内部数据源(ES/SIEM 多在内网)放行私网，但仍拒链路本地/云元数据(169.254.x)
    ok, _reason = ssrf_guard(adapter.endpoint, allow_private=True)
    if not ok:
        return "拒绝（SSRF 防护）"
    try:
        resp = httpx.get(adapter.endpoint, timeout=3.0)
        return "已连" if resp.status_code < 500 else "失败"
    except httpx.HTTPError:
        return "失败"


def build_adapter_store(database_url: str = "") -> AdapterStore:
    if database_url:
        try:
            return PgAdapterStore(database_url)
        except Exception:
            pass
    return InMemoryAdapterStore()


def seed_demo_adapters(store: AdapterStore, es_hosts: str = "") -> None:
    if store.all():
        return
    store.create("Elasticsearch（日志源）", "data_sources", "elasticsearch", es_hosts)
    store.create("Zabbix（监控告警源）", "data_sources", "zabbix", "")
    store.create("SIEM（待接）", "security_tools", "siem", "")
    store.create("EDR（待接）", "security_tools", "edr", "")
