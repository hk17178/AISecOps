"""L01 · AI 资产合规 / Shadow AI 治理 router（L11，C-3）。

清单 CRUD（鉴权+审计）+ 一次性合规体检：对每项资产跑确定性规则，并把平台实际在用的
LLM provider（L05 网关）与已审批清单比对，发现影子 AI。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from aisecops.L02_agents import Principal
from aisecops.L11_target_estate import check_compliance, discover_shadow_ai
from aisecops.L11_target_estate.ai_compliance import KINDS, RISK_CLASS, SENSITIVITY, STATUS

from ..auth_deps import WRITE, require_role
from ..runtime import rt

router = APIRouter()


def _in_use_providers() -> list[dict[str, Any]]:
    """平台实际在用的 LLM provider（来自 L05 网关），用于影子 AI 比对。"""
    return [{"name": p.name, "model": p.model, "outbound": p.outbound, "stub": p.is_stub} for p in rt.gateway.providers]


@router.get("/api/ai-compliance")
async def get_ai_compliance() -> dict[str, Any]:
    """AI 资产清单 + 合规体检（findings）+ Shadow AI 发现 + 计数。"""
    assets = rt.ai_assets.all()
    outbound_enabled = rt.settings.allow_outbound
    findings: list[dict[str, Any]] = []
    for a in assets:
        findings.extend(f.model_dump() for f in check_compliance(a, outbound_enabled=outbound_enabled))
    shadow = discover_shadow_ai(_in_use_providers(), assets)
    counts = {
        "total": len(assets),
        "approved": sum(1 for a in assets if a.status == "已批准"),
        "pending": sum(1 for a in assets if a.status == "待评审"),
        "shadow": sum(1 for a in assets if a.status == "影子"),
        "p0": sum(1 for f in findings if f["severity"] == "P0"),
        "p1": sum(1 for f in findings if f["severity"] == "P1"),
        "shadow_candidates": len(shadow),
    }
    return {
        "assets": [a.model_dump() for a in assets],
        "findings": findings,
        "shadow_candidates": shadow,
        "counts": counts,
        "options": {
            "kinds": list(KINDS),
            "status": list(STATUS),
            "sensitivity": list(SENSITIVITY),
            "risk_class": list(RISK_CLASS),
        },
    }


class AiAssetIn(BaseModel):
    name: str
    kind: str = "LLM"
    provider: str = ""
    endpoint: str = ""
    status: str = "待评审"
    owner: str = ""
    outbound: bool = False
    sensitivity: str = "内部"
    risk_class: str = "有限"
    note: str = ""


@router.post("/api/ai-compliance")
async def create_ai_asset(body: AiAssetIn, principal: Principal = Depends(require_role(*WRITE))) -> dict[str, Any]:
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="AI 资产名不能为空")
    a = rt.ai_assets.create(body.model_dump())
    rt.ctx.audit.append(
        actor=principal.username, action="ai_asset_create", target=a.id, details={"name": a.name, "status": a.status}
    )
    return a.model_dump()


class AiAssetUpdateIn(BaseModel):
    name: str | None = None
    kind: str | None = None
    provider: str | None = None
    endpoint: str | None = None
    status: str | None = None
    owner: str | None = None
    outbound: bool | None = None
    sensitivity: str | None = None
    risk_class: str | None = None
    note: str | None = None


@router.put("/api/ai-compliance/{asset_id}")
async def update_ai_asset(
    asset_id: str, body: AiAssetUpdateIn, principal: Principal = Depends(require_role(*WRITE))
) -> dict[str, Any]:
    a = rt.ai_assets.update(asset_id, body.model_dump(exclude_none=True))
    if a is None:
        raise HTTPException(status_code=404, detail=f"AI 资产 {asset_id} 不存在")
    rt.ctx.audit.append(
        actor=principal.username, action="ai_asset_update", target=asset_id, details={"status": a.status}
    )
    return a.model_dump()


@router.delete("/api/ai-compliance/{asset_id}")
async def delete_ai_asset(asset_id: str, principal: Principal = Depends(require_role(*WRITE))) -> dict[str, Any]:
    removed = rt.ai_assets.remove(asset_id)
    if removed:
        rt.ctx.audit.append(actor=principal.username, action="ai_asset_delete", target=asset_id, details={})
    return {"status": "deleted" if removed else "not_found", "id": asset_id}
