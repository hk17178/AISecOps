from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from aisecops.L02_agents import TicketError

from ..runtime import rt

router = APIRouter()


@router.get("/api/tickets")
async def get_tickets() -> dict[str, Any]:
    return {"tickets": [t.model_dump() for t in rt.tickets.all()]}


class DecisionIn(BaseModel):
    """HITL 审批入参：理由 + 操作人。"""

    reason: str = ""
    actor: str = "未知"


def _decide(ticket_id: str, status: str, audit_action: str, body: DecisionIn) -> dict[str, Any]:
    try:
        ticket = rt.tickets.decide(ticket_id, status, body.reason, body.actor)
    except TicketError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    # C-23：HITL 决策写入不可篡改审计链(谁、为什么)
    rt.ctx.audit.append(
        actor=body.actor,
        action=audit_action,
        target=ticket_id,
        details={
            "reason": body.reason,
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
                actor=body.actor,
                action="soar_execute",
                target=run.id,
                details={"playbook": run.playbook_name, "action": run.action, "target": run.target},
            )
        else:
            rt.runs.set_status(run.id, "已驳回")
    return ticket.model_dump()


@router.post("/api/tickets/{ticket_id}/approve")
async def approve_ticket(ticket_id: str, body: DecisionIn) -> dict[str, Any]:
    return _decide(ticket_id, "已批准", "ticket_approve", body)


@router.post("/api/tickets/{ticket_id}/reject")
async def reject_ticket(ticket_id: str, body: DecisionIn) -> dict[str, Any]:
    return _decide(ticket_id, "已驳回", "ticket_reject", body)
