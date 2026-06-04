"""L07 · 告警分诊业务能力（alert_triage）—— 端到端出口。

组合：L02 Orchestrator + Triage Agent（经 L06 ES 富化、L05 LLM 研判）。
跨层（ADR-0008）：L07 是编排层，可调 L02。
"""

from __future__ import annotations

from typing import Any

from aisecops.L02_agents import (
    AgentContext,
    AgentResult,
    Orchestrator,
    Task,
    TriageAgent,
)
from aisecops.L02_agents.tickets import TicketStore
from aisecops.L05_gateway.llm_gateway import build_gateway
from aisecops.L06_mcp_servers import build_tool_registry


class AlertTriageService:
    """告警分诊业务出口：一条告警进 → 研判结果出。

    真威胁 → 自动建 HITL 工单（C-8：写动作必经人审）。
    """

    def __init__(self, orchestrator: Orchestrator, ticket_store: TicketStore | None = None) -> None:
        self.orchestrator = orchestrator
        self.ticket_store = ticket_store

    async def triage(self, alert: dict[str, Any], high_risk: bool = False) -> AgentResult:
        """对一条告警做端到端分诊；真威胁自动建 HITL 工单。"""
        task = Task(kind="alert_triage", payload=alert, high_risk=high_risk)
        result = await self.orchestrator.dispatch(task)
        if self.ticket_store is not None and result.data.get("verdict") == "真威胁":
            host = str(alert.get("host", "unknown"))
            self.ticket_store.create(action="隔离主机", target=host, risk="高", source_alert=host)
        return result


def build_alert_triage_service(
    ctx: AgentContext | None = None, ticket_store: TicketStore | None = None
) -> AlertTriageService:
    """按 .env 组装端到端分诊服务（真 LLM/ES 或 stub，取决于配置）。"""
    if ctx is None:
        ctx = AgentContext(llm=build_gateway(), tools=build_tool_registry())
    orchestrator = Orchestrator({"alert_triage": TriageAgent()}, ctx)
    return AlertTriageService(orchestrator, ticket_store=ticket_store)
