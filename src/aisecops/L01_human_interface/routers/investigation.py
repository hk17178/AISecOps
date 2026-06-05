from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from aisecops.L02_agents import Principal
from aisecops.L07_secops_capabilities import CorrelationService, InvestigationService

from ..auth_deps import WRITE, require_role
from ..runtime import get_corr_service, get_invest_service, rt

router = APIRouter()


class InvestigateIn(BaseModel):
    host: str = ""
    question: str = ""


@router.post("/api/investigate")
async def investigate(
    body: InvestigateIn,
    svc: InvestigationService = Depends(get_invest_service),
    _: Principal = Depends(require_role(*WRITE)),
) -> dict[str, Any]:
    """事件调查：查 ES 日志建时间线 + LLM 推断攻击链。"""
    result = await svc.investigate(body.host, body.question)
    return result.model_dump()


@router.post("/api/correlate")
async def correlate_alerts(
    svc: CorrelationService = Depends(get_corr_service),
    _: Principal = Depends(require_role(*WRITE)),
) -> dict[str, Any]:
    """关联分析：L08 把当前告警聚成候选事件簇 → 每簇 LLM 出攻击链结论（带引用 C-24）。"""
    cfg = rt.agent_configs.get("correlation")
    if cfg is not None and not cfg.enabled:
        raise HTTPException(status_code=403, detail="Correlation Agent 已停用")
    alerts = rt.alerts.recent(200)
    results = await svc.correlate(alerts)
    return {"candidates": results, "count": len(results)}


@router.get("/api/events")
async def get_events() -> dict[str, Any]:
    """已确认的安全事件列表。"""
    return {"events": [e.model_dump() for e in rt.events.all()]}


class EventConfirmIn(BaseModel):
    """把一个关联簇确认升级为安全事件。"""

    title: str
    severity: str = "高"
    summary: str = ""
    alert_ids: list[str] = []
    actor: str = "未知"


@router.post("/api/events/confirm")
async def confirm_event(body: EventConfirmIn, principal: Principal = Depends(require_role(*WRITE))) -> dict[str, Any]:
    """人工确认关联结论 → 创建安全事件（持久化 + 审计 C-23）。"""
    if not body.title.strip():
        raise HTTPException(status_code=400, detail="事件标题不能为空")
    ev = rt.events.create(body.title.strip(), body.severity, body.summary, body.alert_ids)
    rt.ctx.audit.append(
        actor=principal.username,
        action="event_confirm",
        target=ev.id,
        details={"title": ev.title, "alert_ids": body.alert_ids, "severity": body.severity},
    )
    return ev.model_dump()
