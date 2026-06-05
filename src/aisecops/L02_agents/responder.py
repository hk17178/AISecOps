"""L02 · Responder Agent —— 处置执行，写操作必经 HITL（C-8）。

Responder 不直接动生产：把"建议的处置动作"落成 HITL 工单（人审节点），审批后才执行
（执行经 SOAR/L06，当前占位）。建单即写不可篡改审计（C-23，顺带补审查 #22 的留痕缺口）。
跨层：依赖 L02 工单引擎（同层），DAG 合规。
"""

from __future__ import annotations

from .base import Agent, AgentContext, AgentResult, Task
from .tickets import TicketStore


class ResponderAgent(Agent):
    """处置执行 Agent（经 HITL）。"""

    role = "responder"

    def __init__(self, ticket_store: TicketStore) -> None:
        self._tickets = ticket_store

    async def run(self, task: Task, ctx: AgentContext) -> AgentResult:
        action = str(task.payload.get("action", "隔离主机"))
        target = str(task.payload.get("target", ""))
        risk = str(task.payload.get("risk", "高"))
        source_alert = str(task.payload.get("source_alert", ""))
        ticket = self._tickets.create(action=action, target=target, risk=risk, source_alert=source_alert)
        # C-23：建单即留痕（修审查 #22 自动建单不写审计）
        ctx.audit.append(
            actor=self.role,
            action="ticket_auto_create",
            target=ticket.id,
            details={"action": action, "target": target, "risk": risk, "source_alert": source_alert},
        )
        return AgentResult(
            agent=self.role, ok=True, data={"ticket_id": ticket.id, "status": ticket.status, "action": action}
        )
