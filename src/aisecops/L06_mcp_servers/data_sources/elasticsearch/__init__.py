"""L06 · Elasticsearch 日志源适配器（薄适配器，ADR-0004 / ADR-0009）。"""

from .adapter import ESLogSource, StubLogSource

__all__ = ["ESLogSource", "StubLogSource"]
