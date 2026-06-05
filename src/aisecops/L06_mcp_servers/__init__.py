"""L06 · 工具适配层（ADR-0004：薄适配器 + 统一注册表）。

对外暴露 ToolRegistry；按 .env 组装（有 ES 凭证用真 ES，否则离线 Stub）。
"""

from __future__ import annotations

from aisecops.L12_core_support.config import Settings, get_settings

from .adapter_store import (
    LOG_SOURCE_KINDS,
    QUERYABLE_KINDS,
    Adapter,
    AdapterStore,
    InMemoryAdapterStore,
    PgAdapterStore,
    build_adapter_store,
    seed_demo_adapters,
    test_connectivity,
)
from .data_sources.elasticsearch import ESLogSource, StubLogSource
from .notifier import HttpNotifier, Notifier, StubNotifier, build_notifier
from .registry import LogSource, ToolRegistry

__all__ = [
    "ToolRegistry",
    "LogSource",
    "ESLogSource",
    "StubLogSource",
    "build_tool_registry",
    "Notifier",
    "StubNotifier",
    "HttpNotifier",
    "build_notifier",
    "Adapter",
    "AdapterStore",
    "InMemoryAdapterStore",
    "PgAdapterStore",
    "build_adapter_store",
    "seed_demo_adapters",
    "test_connectivity",
    "LOG_SOURCE_KINDS",
    "QUERYABLE_KINDS",
]


def build_tool_registry(settings: Settings | None = None) -> ToolRegistry:
    """按配置组装工具注册表。有 ES 凭证 → 真 ES；否则离线 Stub。"""
    settings = settings or get_settings()
    registry = ToolRegistry()

    if settings.es_api_key or (settings.es_username and settings.es_password):
        registry.register_log_source(
            ESLogSource(
                hosts=settings.es_hosts,
                api_key=settings.es_api_key or None,
                username=settings.es_username or None,
                password=settings.es_password or None,
                index=settings.es_index,
            )
        )
    else:
        registry.register_log_source(StubLogSource())

    return registry
