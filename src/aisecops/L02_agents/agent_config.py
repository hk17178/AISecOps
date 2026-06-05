"""L02 · Agent 运行时配置（可在 UI 改、即时生效）。

Agent 是代码（类+逻辑），UI 不"凭空新建 agent"；可调的是**配置**：启停、置信度阈值、
cross-check 模式、关联的 prompt key。模型分配复用 §4.4 路由表（scenario→provider），
不在这里重复存。Agent 在 run() 里经 ctx 读这里的活配置，所以改了即时生效。
仓储模式：默认内存，配 DATABASE_URL 用 PG。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel

CROSS_CHECK_MODES = ("auto", "on", "off")  # auto=按任务高风险；on=强制双模型；off=不双模型


class AgentConfig(BaseModel):
    name: str  # = agent.role，如 triage / correlation
    scenario: str  # 对应的 L05 场景（模型路由 key），如 L07/alert_triage
    prompt_key: str = ""  # 关联的 Prompt 治理 key，如 triage/system
    enabled: bool = True
    confidence_threshold: float = 0.5
    cross_check_mode: str = "auto"


class AgentConfigStore(ABC):
    @abstractmethod
    def all(self) -> list[AgentConfig]:
        raise NotImplementedError

    @abstractmethod
    def get(self, name: str) -> AgentConfig | None:
        raise NotImplementedError

    @abstractmethod
    def upsert(self, name: str, scenario: str, prompt_key: str) -> AgentConfig:
        """没有则建默认配置（用于 seed/首次）。"""
        raise NotImplementedError

    @abstractmethod
    def update(self, name: str, fields: dict[str, Any]) -> AgentConfig | None:
        raise NotImplementedError


_EDITABLE = ("enabled", "confidence_threshold", "cross_check_mode", "prompt_key")


def _apply(cfg: AgentConfig, fields: dict[str, Any]) -> None:
    if "enabled" in fields and fields["enabled"] is not None:
        cfg.enabled = bool(fields["enabled"])
    if fields.get("confidence_threshold") is not None:
        cfg.confidence_threshold = max(0.0, min(1.0, float(fields["confidence_threshold"])))
    if fields.get("cross_check_mode") in CROSS_CHECK_MODES:
        cfg.cross_check_mode = str(fields["cross_check_mode"])
    if fields.get("prompt_key") is not None:
        cfg.prompt_key = str(fields["prompt_key"])


class InMemoryAgentConfigStore(AgentConfigStore):
    def __init__(self) -> None:
        self._items: dict[str, AgentConfig] = {}

    def all(self) -> list[AgentConfig]:
        return list(self._items.values())

    def get(self, name: str) -> AgentConfig | None:
        return self._items.get(name)

    def upsert(self, name: str, scenario: str, prompt_key: str) -> AgentConfig:
        cfg = self._items.get(name)
        if cfg is None:
            cfg = AgentConfig(name=name, scenario=scenario, prompt_key=prompt_key)
            self._items[name] = cfg
        return cfg

    def update(self, name: str, fields: dict[str, Any]) -> AgentConfig | None:
        cfg = self._items.get(name)
        if cfg is None:
            return None
        _apply(cfg, fields)
        return cfg


class PgAgentConfigStore(AgentConfigStore):
    _COLS = "name, scenario, prompt_key, enabled, confidence_threshold, cross_check_mode"

    def __init__(self, database_url: str) -> None:
        from aisecops.L12_core_support.db import get_pool

        self._pool = get_pool(database_url)
        with self._pool.connection() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS agent_configs ("
                "name text PRIMARY KEY, scenario text, prompt_key text, enabled boolean DEFAULT true, "
                "confidence_threshold double precision DEFAULT 0.5, cross_check_mode text DEFAULT 'auto')"
            )

    @staticmethod
    def _to_cfg(r: Any) -> AgentConfig:
        return AgentConfig(
            name=r[0],
            scenario=r[1] or "",
            prompt_key=r[2] or "",
            enabled=bool(r[3]),
            confidence_threshold=float(r[4]) if r[4] is not None else 0.5,
            cross_check_mode=r[5] or "auto",
        )

    def all(self) -> list[AgentConfig]:
        with self._pool.connection() as conn:
            rows = conn.execute(f"SELECT {self._COLS} FROM agent_configs ORDER BY name").fetchall()
        return [self._to_cfg(r) for r in rows]

    def get(self, name: str) -> AgentConfig | None:
        with self._pool.connection() as conn:
            row = conn.execute(f"SELECT {self._COLS} FROM agent_configs WHERE name=%s", (name,)).fetchone()
        return self._to_cfg(row) if row else None

    def upsert(self, name: str, scenario: str, prompt_key: str) -> AgentConfig:
        with self._pool.connection() as conn:
            conn.execute(
                "INSERT INTO agent_configs (name, scenario, prompt_key) VALUES (%s,%s,%s) "
                "ON CONFLICT (name) DO NOTHING",
                (name, scenario, prompt_key),
            )
            row = conn.execute(f"SELECT {self._COLS} FROM agent_configs WHERE name=%s", (name,)).fetchone()
        return self._to_cfg(row) if row else AgentConfig(name=name, scenario=scenario, prompt_key=prompt_key)

    def update(self, name: str, fields: dict[str, Any]) -> AgentConfig | None:
        cfg = self.get(name)
        if cfg is None:
            return None
        _apply(cfg, fields)
        with self._pool.connection() as conn:
            conn.execute(
                "UPDATE agent_configs SET enabled=%s, confidence_threshold=%s, cross_check_mode=%s, prompt_key=%s WHERE name=%s",
                (cfg.enabled, cfg.confidence_threshold, cfg.cross_check_mode, cfg.prompt_key, name),
            )
        return cfg


def build_agent_config_store(database_url: str = "") -> AgentConfigStore:
    if database_url:
        try:
            return PgAgentConfigStore(database_url)
        except Exception:
            pass
    return InMemoryAgentConfigStore()


# 已编码 agent 的默认配置（名→场景→prompt key）
_SEED = [
    ("triage", "L07/alert_triage", "triage/system"),
    ("investigation", "L07/investigation", "investigation/system"),
    ("correlation", "L08/correlation", "correlation/system"),
]


def seed_agent_configs(store: AgentConfigStore) -> None:
    for name, scenario, prompt_key in _SEED:
        store.upsert(name, scenario, prompt_key)


def resolve_cross_check(mode: str, high_risk: bool) -> bool:
    """按配置决定是否 cross-check。"""
    if mode == "on":
        return True
    if mode == "off":
        return False
    return high_risk
