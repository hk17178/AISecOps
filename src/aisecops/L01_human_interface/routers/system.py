from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel

from aisecops.L02_agents import Principal
from aisecops.L05_gateway.llm_gateway import LLMGateway

from ..auth_deps import ADMIN, require_role
from ..runtime import STATIC, get_gateway, rt

router = APIRouter()


class CallIn(BaseModel):
    """测试台调用入参。"""

    prompt: str
    scenario: str = "L01/test"


@router.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/api/llm/call")
async def llm_call(
    body: CallIn,
    gateway: LLMGateway = Depends(get_gateway),
    _: Principal = Depends(require_role(*ADMIN)),
) -> dict[str, Any]:
    resp = await gateway.call(body.prompt, scenario=body.scenario)
    return {"content": resp.content, "metadata": resp.metadata.model_dump()}


@router.get("/api/cost")
async def get_cost() -> dict[str, Any]:
    history = rt.gateway.recorder.history
    budget = rt.gateway.budget
    by_provider: dict[str, int] = {}
    by_scenario: dict[str, int] = {}
    for m in history:
        by_provider[m.provider] = by_provider.get(m.provider, 0) + 1
        by_scenario[m.scenario] = by_scenario.get(m.scenario, 0) + 1
    return {
        "monthly_cap_cny": budget.monthly_cap_cny if budget else 0.0,
        "spent_cny": round(budget.spent(), 4) if budget else 0.0,
        "remaining_cny": round(budget.remaining(), 4) if budget else 0.0,
        "total_calls": len(history),
        "total_tokens": sum(m.total_tokens for m in history),
        "by_provider": by_provider,
        "by_scenario": by_scenario,
        "providers": [{"name": p.name, "model": p.model, "outbound": p.outbound} for p in rt.gateway.providers],
    }


@router.get("/api/audit")
async def get_audit() -> dict[str, Any]:
    """审计链（C-23）：最近记录 + 链完整性校验。"""
    entries = list(reversed(rt.ctx.audit.entries))[:50]
    return {
        "entries": [e.model_dump() for e in entries],
        "verified": rt.ctx.audit.verify(),
    }


@router.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")
