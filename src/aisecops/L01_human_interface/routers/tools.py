from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from aisecops.L06_mcp_servers import test_connectivity

from ..runtime import rt

router = APIRouter()


@router.get("/api/tools")
async def get_tools() -> dict[str, Any]:
    """适配器清单（增删/启停/测连）。ES 适配器额外标注是否真接入。"""
    ls = rt.registry.log_source
    es_real = ls is not None and ls.name == "elasticsearch"
    adapters = []
    for a in rt.adapters.all():
        d = a.model_dump()
        if a.kind == "elasticsearch":
            d["runtime"] = "已接入真 ES" if es_real else "Stub（未配凭证，离线）"
        adapters.append(d)
    return {
        "adapters": adapters,
        "categories": ["data_sources", "security_tools", "protocols", "vendors", "aiops", "custom"],
        "outbound_enabled": rt.settings.allow_outbound,
    }


class AdapterIn(BaseModel):
    name: str
    category: str = "data_sources"
    kind: str = ""
    endpoint: str = ""
    actor: str = "未知"


class ToggleIn(BaseModel):
    """通用启停入参（defined-before-use，避免 future-annotations 前向引用问题）。"""

    enabled: bool
    actor: str = "未知"


@router.post("/api/tools")
async def create_adapter(body: AdapterIn) -> dict[str, Any]:
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="适配器名不能为空")
    a = rt.adapters.create(body.name.strip(), body.category, body.kind.strip(), body.endpoint.strip())
    rt.ctx.audit.append(
        actor=body.actor, action="adapter_create", target=a.id, details={"name": a.name, "kind": a.kind}
    )
    return a.model_dump()


@router.put("/api/tools/{adapter_id}")
async def toggle_adapter(adapter_id: str, body: ToggleIn) -> dict[str, Any]:
    a = rt.adapters.set_enabled(adapter_id, body.enabled)
    if a is None:
        raise HTTPException(status_code=404, detail=f"适配器 {adapter_id} 不存在")
    rt.ctx.audit.append(actor=body.actor, action="adapter_toggle", target=adapter_id, details={"enabled": body.enabled})
    return a.model_dump()


@router.delete("/api/tools/{adapter_id}")
async def delete_adapter(adapter_id: str, actor: str = "未知") -> dict[str, Any]:
    removed = rt.adapters.remove(adapter_id)
    if removed:
        rt.ctx.audit.append(actor=actor, action="adapter_delete", target=adapter_id, details={})
    return {"status": "deleted" if removed else "not_found", "id": adapter_id}


@router.post("/api/tools/{adapter_id}/test")
async def test_adapter(adapter_id: str, actor: str = "未知") -> dict[str, Any]:
    """连通测试：真探一次（外网端点受出域开关约束）。"""
    a = rt.adapters.get(adapter_id)
    if a is None:
        raise HTTPException(status_code=404, detail=f"适配器 {adapter_id} 不存在")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    status = test_connectivity(a, rt.settings.allow_outbound, now)
    updated = rt.adapters.set_status(adapter_id, status, now)
    rt.ctx.audit.append(actor=actor, action="adapter_test", target=adapter_id, details={"status": status})
    return (updated or a).model_dump()
