"""L01 · 日志/数据源接入管理（L06 data_sources + L10 采集，对标 Splunk「Data inputs」）。

聚焦视图：把 data_sources 类适配器作为"日志/数据源"呈现，给出种类目录与每个源的"是否可查询"。
增删/启停/连通测试复用通用适配器端点 /api/tools（已带鉴权+审计），本路由只提供聚焦读。

诚实标注（ADR-0009 日志留到最后）：ES 已有真实查询适配器=可查询；其余种类登记+连通测试可用，
查询适配器随用随接，不做假按钮。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from aisecops.L06_mcp_servers import LOG_SOURCE_KINDS, QUERYABLE_KINDS

from ..runtime import rt

router = APIRouter()


@router.get("/api/log-sources")
async def get_log_sources() -> dict[str, Any]:
    """日志/数据源清单（data_sources）+ 种类目录 + 可查询标记。"""
    ls = rt.registry.log_source
    es_real = ls is not None and ls.name == "elasticsearch"
    sources: list[dict[str, Any]] = []
    for a in rt.adapters.all():
        if a.category != "data_sources":
            continue
        d = a.model_dump()
        queryable = a.kind in QUERYABLE_KINDS
        d["queryable"] = queryable
        if a.kind == "elasticsearch":
            d["runtime"] = "已接入真 ES（可查询）" if es_real else "Stub（未配凭证，离线）"
        elif queryable:
            d["runtime"] = "可查询"
        else:
            d["runtime"] = "已登记（连通测试可用；查询适配器待接）"
        sources.append(d)
    return {
        "sources": sources,
        "kinds": list(LOG_SOURCE_KINDS),
        "queryable_kinds": list(QUERYABLE_KINDS),
        "outbound_enabled": rt.settings.allow_outbound,
    }
