"""L02 · Memory Store —— Agent 的结构化记忆（P-8：存结构化状态，不存自然语言）。

源无关：接口稳定，默认内存实现；将来可换 PG/SQLite（配置走 P-18），调用方不变。
按 namespace 作用域隔离（如 "triage_history" / "investigation"）。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class MemoryStore(ABC):
    """Agent 记忆存储接口。"""

    @abstractmethod
    def put(self, namespace: str, key: str, value: dict[str, Any]) -> None:
        """写入（同 namespace+key 覆盖）。"""
        raise NotImplementedError

    @abstractmethod
    def get(self, namespace: str, key: str) -> dict[str, Any] | None:
        """读取，不存在返回 None。"""
        raise NotImplementedError

    @abstractmethod
    def list(self, namespace: str) -> list[dict[str, Any]]:
        """列出某 namespace 下所有值（按写入顺序）。"""
        raise NotImplementedError


class InMemoryMemoryStore(MemoryStore):
    """默认内存实现（进程内，重启即失）。生产换持久化后端。"""

    def __init__(self) -> None:
        self._data: dict[tuple[str, str], dict[str, Any]] = {}

    def put(self, namespace: str, key: str, value: dict[str, Any]) -> None:
        self._data[(namespace, key)] = dict(value)

    def get(self, namespace: str, key: str) -> dict[str, Any] | None:
        return self._data.get((namespace, key))

    def list(self, namespace: str) -> list[dict[str, Any]]:
        return [v for (ns, _k), v in self._data.items() if ns == namespace]
