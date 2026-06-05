from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from aisecops.L02_agents import Principal

from ..auth_deps import ADMIN, require_role
from ..runtime import rt

router = APIRouter()


@router.get("/api/routing")
async def get_routing() -> dict[str, Any]:
    """场景→模型路由表（§4.4）。列出可用 provider + 当前映射 + 每条命中的 model。"""
    providers = [
        {"name": p.name, "model": p.model, "stub": p.is_stub, "outbound": p.outbound} for p in rt.gateway.providers
    ]
    by_name = {p.name: p for p in rt.gateway.providers}
    routes = []
    for scenario, prov in sorted(rt.route_store.all().items()):
        hit = by_name.get(prov)
        routes.append(
            {
                "scenario": scenario,
                "provider": prov,
                "model": hit.model if hit else "（该模型未配置，回退默认）",
                "available": hit is not None,
            }
        )
    return {
        "routes": routes,
        "providers": providers,
        "default": rt.gateway.router.default if rt.gateway.router else None,
    }


class RouteIn(BaseModel):
    """新增/修改一条路由：场景 → provider 名。"""

    scenario: str
    provider: str
    actor: str = "未知"


@router.put("/api/routing")
async def put_routing(body: RouteIn, principal: Principal = Depends(require_role(*ADMIN))) -> dict[str, Any]:
    """增改一条场景路由：写存储（持久化）+ 更新在线网关 + 审计留痕（C-23）。"""
    if not body.scenario.strip():
        raise HTTPException(status_code=400, detail="scenario 不能为空")
    names = {p.name for p in rt.gateway.providers}
    if body.provider not in names:
        raise HTTPException(status_code=400, detail=f"provider「{body.provider}」不存在，可选：{sorted(names)}")
    rt.route_store.set(body.scenario, body.provider)
    if rt.gateway.router is not None:
        rt.gateway.router.set_route(body.scenario, body.provider)
    rt.ctx.audit.append(
        actor=principal.username,
        action="routing_set",
        target=body.scenario,
        details={"provider": body.provider},
    )
    return {"status": "saved", "scenario": body.scenario, "provider": body.provider}


@router.delete("/api/routing/{scenario:path}")
async def delete_routing(scenario: str, principal: Principal = Depends(require_role(*ADMIN))) -> dict[str, Any]:
    """删除一条场景路由：该场景回退默认 provider。"""
    removed = rt.route_store.remove(scenario)
    if rt.gateway.router is not None:
        rt.gateway.router.remove_route(scenario)
    if removed:
        rt.ctx.audit.append(actor=principal.username, action="routing_delete", target=scenario, details={})
    return {"status": "deleted" if removed else "not_found", "scenario": scenario}
