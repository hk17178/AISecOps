"""L07 · 安全事件关联分析业务能力（§1.5）—— 端到端出口。

组合：L08 关联引擎（候选事件簇）+ L02 Correlation Agent（经 L05 LLM 出攻击链结论）。
跨层（ADR-0008）：L07 可调 L02、L08。
"""

from __future__ import annotations

from typing import Any

from aisecops.L02_agents import AgentContext, Orchestrator, Task
from aisecops.L02_agents.correlation import CorrelationAgent
from aisecops.L05_gateway.llm_gateway import build_gateway
from aisecops.L06_mcp_servers import build_tool_registry
from aisecops.L08_analytics_engines import correlate
from aisecops.L09_data_platform.alert_store import Alert


class CorrelationService:
    """关联分析业务出口：一批告警进 → 候选事件簇 + 每簇 LLM 攻击链结论出。"""

    def __init__(self, orchestrator: Orchestrator) -> None:
        self.orchestrator = orchestrator

    async def correlate(self, alerts: list[Alert], high_risk: bool = False) -> list[dict[str, Any]]:
        """对告警做关联：L08 聚簇 → 每个多告警簇调 LLM 出结论（带引用）。"""
        clusters = correlate(alerts)
        by_id = {a.id: a for a in alerts}
        results: list[dict[str, Any]] = []
        for cl in clusters:
            members = [by_id[i].model_dump() for i in cl.alert_ids if i in by_id]
            task = Task(
                kind="correlation",
                payload={"cluster_id": cl.id, "alerts": members},
                high_risk=high_risk,
            )
            res = await self.orchestrator.dispatch(task)
            results.append({"cluster": cl.model_dump(), "conclusion": res.data})
        return results


def build_correlation_service(ctx: AgentContext | None = None) -> CorrelationService:
    """按 .env 组装关联分析服务（真 LLM 或 stub，取决于配置）。"""
    if ctx is None:
        ctx = AgentContext(llm=build_gateway(), tools=build_tool_registry())
    orchestrator = Orchestrator({"correlation": CorrelationAgent()}, ctx)
    return CorrelationService(orchestrator)
