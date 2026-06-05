from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from aisecops.L02_agents import OrchestratorError, Principal, Task, TicketError

from ..auth_deps import WRITE, require_role
from ..runtime import rt

router = APIRouter()


async def _sink_feedback(ticket: Any, status: str, reason: str) -> None:
    """反馈飞轮：结案 ──事件──▶ Tuning Agent 沉淀进知识库（去重）。失败不阻塞审批。"""
    verdict = "确认处置" if status == "已批准" else "判为无需处置/误判"
    case = {
        "title": f"处置案例：{ticket.target} · {ticket.action}",
        "category": "历史告警处理记录",
        "content": (
            f"现象：针对资产 {ticket.target} 的告警（来源 {ticket.source_alert or '—'}）经研判需要处置。"
            f"处置动作：{ticket.action}（风险 {ticket.risk}）。人工{status}——{verdict}"
            f"{('，理由：' + reason) if reason else ''}。"
        ),
        "source": f"ticket:{ticket.id}",
    }
    try:
        await rt.orchestrator.dispatch(Task(kind="tuning", payload=case))
    except OrchestratorError:
        pass


@router.get("/api/tickets")
async def get_tickets() -> dict[str, Any]:
    return {"tickets": [t.model_dump() for t in rt.tickets.all()]}


class DecisionIn(BaseModel):
    """HITL 审批入参：理由（操作人由会话令牌解析，不信任客户端自报）。"""

    reason: str = ""


async def _decide(ticket_id: str, status: str, audit_action: str, reason: str, actor: str) -> dict[str, Any]:
    try:
        ticket = rt.tickets.decide(ticket_id, status, reason, actor)
    except TicketError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    # C-23：HITL 决策写入不可篡改审计链(谁、为什么)；actor 来自已认证身份
    rt.ctx.audit.append(
        actor=actor,
        action=audit_action,
        target=ticket_id,
        details={
            "reason": reason,
            "ticket_action": ticket.action,
            "ticket_target": ticket.target,
        },
    )
    # 若该工单由 SOAR 剧本触发：批准→执行动作，驳回→标记驳回(执行留痕)
    run = rt.runs.find_by_ticket(ticket_id)
    if run is not None and run.status == "待审":
        if status == "已批准":
            rt.runs.set_status(run.id, "已执行")  # 占位执行(真实经 L06 调外部工具)
            rt.playbooks.bump_runs(run.playbook_id)
            rt.ctx.audit.append(
                actor=actor,
                action="soar_execute",
                target=run.id,
                details={"playbook": run.playbook_name, "action": run.action, "target": run.target},
            )
        else:
            rt.runs.set_status(run.id, "已驳回")
    # 反馈飞轮：结案沉淀知识（回流下一轮分诊 RAG 召回）
    await _sink_feedback(ticket, status, reason)
    return ticket.model_dump()


@router.post("/api/tickets/{ticket_id}/approve")
async def approve_ticket(
    ticket_id: str, body: DecisionIn, principal: Principal = Depends(require_role(*WRITE))
) -> dict[str, Any]:
    return await _decide(ticket_id, "已批准", "ticket_approve", body.reason, principal.username)


@router.post("/api/tickets/{ticket_id}/reject")
async def reject_ticket(
    ticket_id: str, body: DecisionIn, principal: Principal = Depends(require_role(*WRITE))
) -> dict[str, Any]:
    return await _decide(ticket_id, "已驳回", "ticket_reject", body.reason, principal.username)
