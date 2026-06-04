"""L05 · 场景路由表的持久化（仓储模式，与告警/工单一致）。

路由是用户配置（非密钥），改了要留得住（P-18）。有 DATABASE_URL 用 PG，否则内存。
接口稳定；ScenarioRouter 从这里加载、写回。
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from .routing import DEFAULT_ROUTES


class RouteStore(ABC):
    """场景→provider 路由表存储。"""

    @abstractmethod
    def all(self) -> dict[str, str]:
        raise NotImplementedError

    @abstractmethod
    def set(self, scenario: str, provider: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def remove(self, scenario: str) -> bool:
        raise NotImplementedError


class InMemoryRouteStore(RouteStore):
    def __init__(self) -> None:
        self._routes: dict[str, str] = {}

    def all(self) -> dict[str, str]:
        return dict(self._routes)

    def set(self, scenario: str, provider: str) -> None:
        self._routes[scenario] = provider

    def remove(self, scenario: str) -> bool:
        return self._routes.pop(scenario, None) is not None


class PgRouteStore(RouteStore):
    """PostgreSQL 实现（持久化，P-18）。表 llm_routes(scenario PK, provider)。"""

    def __init__(self, database_url: str) -> None:
        from aisecops.L12_core_support.db import get_pool

        self._pool = get_pool(database_url)
        with self._pool.connection() as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS llm_routes (scenario text PRIMARY KEY, provider text)")

    def all(self) -> dict[str, str]:
        with self._pool.connection() as conn:
            rows = conn.execute("SELECT scenario, provider FROM llm_routes ORDER BY scenario").fetchall()
        return {r[0]: r[1] for r in rows}

    def set(self, scenario: str, provider: str) -> None:
        with self._pool.connection() as conn:
            conn.execute(
                "INSERT INTO llm_routes (scenario, provider) VALUES (%s,%s) "
                "ON CONFLICT (scenario) DO UPDATE SET provider=EXCLUDED.provider",
                (scenario, provider),
            )

    def remove(self, scenario: str) -> bool:
        with self._pool.connection() as conn:
            cur = conn.execute("DELETE FROM llm_routes WHERE scenario=%s", (scenario,))
            return bool(cur.rowcount)


def build_route_store(database_url: str = "") -> RouteStore:
    """有 database_url 用 PG（连不上回退内存）；否则内存。"""
    if database_url:
        try:
            return PgRouteStore(database_url)
        except Exception:
            pass
    return InMemoryRouteStore()


def seed_default_routes(store: RouteStore) -> None:
    """空表时写入默认分档路由（仅首次；用户后续在 UI 改）。"""
    if not store.all():
        for scenario, provider in DEFAULT_ROUTES.items():
            store.set(scenario, provider)
