from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from aisecops.L02_agents import Principal

from ..auth_deps import ADMIN, WRITE, require_role
from ..runtime import rt

router = APIRouter()


@router.get("/api/playbooks")
async def get_playbooks() -> dict[str, Any]:
    return {
        "playbooks": [p.model_dump() for p in rt.playbooks.all()],
        "action_kinds": ["封禁 IP", "隔离主机", "禁用账号"],
    }


class PlaybookIn(BaseModel):
    """新建剧本。"""

    name: str
    actions: list[str] = []
    risk: str = "高"
    trigger_verdict: str = "真威胁"
    trigger_severity: str = ""
    trigger_keyword: str = ""
    actor: str = "未知"


@router.post("/api/playbooks")
async def create_playbook(body: PlaybookIn, principal: Principal = Depends(require_role(*ADMIN))) -> dict[str, Any]:
    """新建处置剧本（写审计）。"""
    if not body.name.strip() or not body.actions:
        raise HTTPException(status_code=400, detail="剧本名与至少一个动作不能为空")
    bad = [a for a in body.actions if a not in ("封禁 IP", "隔离主机", "禁用账号")]
    if bad:
        raise HTTPException(status_code=400, detail=f"不支持的动作：{bad}")
    pb = rt.playbooks.create(
        body.name.strip(), body.actions, body.risk, body.trigger_verdict, body.trigger_severity, body.trigger_keyword
    )
    rt.ctx.audit.append(actor=principal.username, action="playbook_create", target=pb.id, details={"name": pb.name})
    return pb.model_dump()


class PlaybookToggleIn(BaseModel):
    enabled: bool
    actor: str = "未知"


@router.put("/api/playbooks/{playbook_id}")
async def toggle_playbook(
    playbook_id: str, body: PlaybookToggleIn, principal: Principal = Depends(require_role(*ADMIN))
) -> dict[str, Any]:
    pb = rt.playbooks.set_enabled(playbook_id, body.enabled)
    if pb is None:
        raise HTTPException(status_code=404, detail=f"剧本 {playbook_id} 不存在")
    rt.ctx.audit.append(
        actor=principal.username, action="playbook_toggle", target=playbook_id, details={"enabled": body.enabled}
    )
    return pb.model_dump()


@router.delete("/api/playbooks/{playbook_id}")
async def delete_playbook(playbook_id: str, principal: Principal = Depends(require_role(*ADMIN))) -> dict[str, Any]:
    removed = rt.playbooks.remove(playbook_id)
    if removed:
        rt.ctx.audit.append(actor=principal.username, action="playbook_delete", target=playbook_id, details={})
    return {"status": "deleted" if removed else "not_found", "id": playbook_id}


class SoarTriggerIn(BaseModel):
    """手动触发剧本：对某条告警执行。"""

    playbook_id: str
    alert_id: str = ""
    target: str = ""
    actor: str = "未知"


@router.post("/api/soar/trigger")
async def soar_trigger(body: SoarTriggerIn, principal: Principal = Depends(require_role(*WRITE))) -> dict[str, Any]:
    """触发剧本 → 建 HITL 工单（C-8，高风险必经人审）+ 记执行（待审）。"""
    pb = rt.playbooks.get(body.playbook_id)
    if pb is None:
        raise HTTPException(status_code=404, detail=f"剧本 {body.playbook_id} 不存在")
    if not pb.enabled:
        raise HTTPException(status_code=400, detail="剧本已停用，无法触发")
    # 目标：显式传入或从告警主机取
    target = body.target.strip()
    if not target and body.alert_id:
        hit = next((a for a in rt.alerts.recent(500) if a.id == body.alert_id), None)
        target = hit.host if hit else ""
    target = target or "(未指定目标)"
    action = "、".join(pb.actions)
    ticket = rt.tickets.create(action=pb.actions[0], target=target, risk=pb.risk, source_alert=body.alert_id)
    run = rt.runs.create(pb, target=target, action=action, ticket_id=ticket.id, alert_id=body.alert_id)
    rt.ctx.audit.append(
        actor=principal.username,
        action="soar_trigger",
        target=run.id,
        details={"playbook": pb.name, "ticket": ticket.id, "action": action, "target": target},
    )
    return {"run": run.model_dump(), "ticket": ticket.model_dump()}


@router.get("/api/soar/runs")
async def get_runs() -> dict[str, Any]:
    return {"runs": [r.model_dump() for r in rt.runs.all()]}


@router.post("/api/soar/runs/{run_id}/undo")
async def undo_run(run_id: str, principal: Principal = Depends(require_role(*WRITE))) -> dict[str, Any]:
    """撤销已执行的处置（标记可撤销，留痕）。"""
    run = next((r for r in rt.runs.all() if r.id == run_id), None)
    if run is None:
        raise HTTPException(status_code=404, detail=f"执行 {run_id} 不存在")
    if run.status != "已执行":
        raise HTTPException(status_code=400, detail=f"仅「已执行」可撤销（当前 {run.status}）")
    updated = rt.runs.set_status(run_id, "已撤销")
    rt.ctx.audit.append(
        actor=principal.username,
        action="soar_undo",
        target=run_id,
        details={"action": run.action, "target": run.target},
    )
    return (updated or run).model_dump()
