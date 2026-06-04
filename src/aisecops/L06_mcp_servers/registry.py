"""L06 · 工具注册表 + 适配器接口（ADR-0004：薄适配器 + 统一注册表）。

L02/L07/L08 经注册表调外部工具，不直连。是所有出站调用的治理边界
（白名单/审计/凭证，CONSTRAINTS 第 164/175 行；P-3）。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class LogSource(ABC):
    """日志源适配器接口（如 ES）。薄适配器形态见 ADR-0004。"""

    name: str = "logsource"

    @abstractmethod
    async def search_logs(
        self,
        *,
        host: str | None = None,
        ip: str | None = None,
        size: int = 10,
    ) -> list[dict[str, Any]]:
        """按主机/IP 查最近若干条日志。返回结构化记录列表。"""
        raise NotImplementedError


class ToolRegistry:
    """L06 统一工具注册表。Agent / 业务层只认它，不关心底层是 ES 还是别的。"""

    def __init__(self) -> None:
        self._log_source: LogSource | None = None

    def register_log_source(self, source: LogSource) -> None:
        self._log_source = source

    @property
    def log_source(self) -> LogSource | None:
        return self._log_source
