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
from aisecops.L05_gateway.llm_gateway import build_gateway
from aisecops.L06_mcp_servers import build_tool_registry


class AlertTriageService:
    """告警分诊业务出口：一条告警进 → 研判结果出。"""

    def __init__(self, orchestrator: Orchestrator) -> None:
        self.orchestrator = orchestrator

    async def triage(self, alert: dict[str, Any], high_risk: bool = False) -> AgentResult:
        """对一条告警做端到端分诊。"""
        task = Task(kind="alert_triage", payload=alert, high_risk=high_risk)
        return await self.orchestrator.dispatch(task)


def build_alert_triage_service(ctx: AgentContext | None = None) -> AlertTriageService:
    """按 .env 组装端到端分诊服务（真 LLM/ES 或 stub，取决于配置）。"""
    if ctx is None:
        ctx = AgentContext(llm=build_gateway(), tools=build_tool_registry())
    orchestrator = Orchestrator({"alert_triage": TriageAgent()}, ctx)
    return AlertTriageService(orchestrator)
