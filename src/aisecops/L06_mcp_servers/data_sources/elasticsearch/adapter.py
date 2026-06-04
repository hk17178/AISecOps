"""Elasticsearch 日志源 —— 真实 ES 8.x 适配器 + 离线 Stub。

就地查询（ADR-0009）：不抽取入库，要日志时查 ES。
ES 客户端用 elasticsearch-py 8（同步），用 asyncio.to_thread 包成异步，避免阻塞事件循环。
"""

from __future__ import annotations

import asyncio
from typing import Any

from ...registry import LogSource

# 离线演示用的假日志
_DEFAULT_LOGS: list[dict[str, Any]] = [
    {
        "host": "WIN-APP-07",
        "time": "09:42:10",
        "event": "PsExec service install",
        "user": "svc_backup",
    },
    {
        "host": "WIN-APP-07",
        "time": "09:42:15",
        "event": "remote exec -> 6 hosts",
        "user": "svc_backup",
    },
    {"host": "DC-01", "time": "09:43:01", "event": "auth attempt", "src_ip": "10.0.2.7"},
]


class StubLogSource(LogSource):
    """内存假日志源（不连 ES，离线/测试用）。"""

    name = "es-stub"

    def __init__(self, logs: list[dict[str, Any]] | None = None) -> None:
        self._logs = logs if logs is not None else _DEFAULT_LOGS
        self.last_query: dict[str, Any] | None = None  # 记录最近一次查询（便于测试断言）

    async def search_logs(
        self,
        *,
        host: str | None = None,
        ip: str | None = None,
        size: int = 10,
    ) -> list[dict[str, Any]]:
        self.last_query = {"host": host, "ip": ip, "size": size}
        out = [
            log
            for log in self._logs
            if (host is None or log.get("host") == host) and (ip is None or log.get("src_ip") == ip)
        ]
        return out[:size]


class ESLogSource(LogSource):
    """真实 Elasticsearch 8.x 适配器。"""

    name = "elasticsearch"

    def __init__(
        self,
        hosts: str,
        api_key: str | None = None,
        username: str | None = None,
        password: str | None = None,
        index: str = "*",
        timeout: float = 10.0,
    ) -> None:
        from elasticsearch import Elasticsearch  # 延迟导入，避免离线时也加载

        kwargs: dict[str, Any] = {"request_timeout": timeout}
        if api_key:
            kwargs["api_key"] = api_key
        elif username and password:
            kwargs["basic_auth"] = (username, password)
        self._client = Elasticsearch(hosts, **kwargs)
        self._index = index

    async def search_logs(
        self,
        *,
        host: str | None = None,
        ip: str | None = None,
        size: int = 10,
    ) -> list[dict[str, Any]]:
        must: list[dict[str, Any]] = []
        if host:
            must.append({"match": {"host": host}})
        if ip:
            must.append({"match": {"src_ip": ip}})
        query: dict[str, Any] = {"bool": {"must": must}} if must else {"match_all": {}}
        # 同步客户端放线程池，避免阻塞 async 事件循环
        resp = await asyncio.to_thread(self._client.search, index=self._index, query=query, size=size)
        return [hit["_source"] for hit in resp["hits"]["hits"]]
