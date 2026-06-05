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
    OrchestratorError,
    Task,
    TriageAgent,
)
from aisecops.L02_agents.tickets import TicketStore
from aisecops.L05_gateway.llm_gateway import build_gateway
from aisecops.L06_mcp_servers import build_tool_registry


class AlertTriageService:
    """告警分诊业务出口：一条告警进 → 研判结果出。

    编排链（经 Orchestrator，C-5）：Enrichment 富化 → Triage 研判 → 真威胁 Responder 建 HITL 工单。
    Enrichment/Responder 不可用时（如单测的精简编排）优雅降级，不影响主研判。
    """

    def __init__(self, orchestrator: Orchestrator, ticket_store: TicketStore | None = None) -> None:
        self.orchestrator = orchestrator
        self.ticket_store = ticket_store

    async def triage(self, alert: dict[str, Any], high_risk: bool = False) -> AgentResult:
        """端到端分诊：富化 → 研判 → 真威胁经 Responder 建 HITL 工单。"""
        payload = dict(alert)
        # ① Enrichment 富化（CMDB/IoC/RAG）：有该 Agent 才做；关键/高资产升级高风险
        try:
            enr = await self.orchestrator.dispatch(Task(kind="enrichment", payload=alert))
            context = enr.data.get("context", {})
            asset = context.get("asset")
            if asset:
                payload["asset_importance"] = asset.get("importance", "")
                payload["asset_role"] = asset.get("role", "")
                if asset.get("importance") in ("关键", "高"):
                    high_risk = True
        except OrchestratorError:
            pass

        # ② Triage 研判
        result = await self.orchestrator.dispatch(Task(kind="alert_triage", payload=payload, high_risk=high_risk))

        # ③ 真威胁 → 经 Responder 建 HITL 工单（C-8 + C-23 留痕，修审查 #22）
        if result.data.get("verdict") == "真威胁":
            host = str(alert.get("host", "unknown"))
            disposition = {
                "action": "隔离主机",
                "target": host,
                "risk": "高",
                "source_alert": str(alert.get("id", host)),
            }
            try:
                await self.orchestrator.dispatch(Task(kind="respond", payload=disposition))
            except OrchestratorError:
                # 无 Responder（精简编排）→ 直接建单并补审计
                if self.ticket_store is not None:
                    t = self.ticket_store.create(
                        action="隔离主机", target=host, risk="高", source_alert=disposition["source_alert"]
                    )
                    self.orchestrator.ctx.audit.append(
                        actor="alert_triage", action="ticket_auto_create", target=t.id, details={"target": host}
                    )
        return result


def build_alert_triage_service(
    ctx: AgentContext | None = None, ticket_store: TicketStore | None = None
) -> AlertTriageService:
    """按 .env 组装端到端分诊服务（真 LLM/ES 或 stub，取决于配置）。"""
    if ctx is None:
        ctx = AgentContext(llm=build_gateway(), tools=build_tool_registry())
    orchestrator = Orchestrator({"alert_triage": TriageAgent()}, ctx)
    return AlertTriageService(orchestrator, ticket_store=ticket_store)
