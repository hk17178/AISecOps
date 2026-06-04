"""L07 · 事件调查业务能力（investigation）。

组合：L02 Orchestrator + Investigation Agent（经 L06 ES 取日志、L05 LLM 推断）。
"""

from __future__ import annotations

from aisecops.L02_agents import AgentContext, AgentResult, Orchestrator, Task
from aisecops.L02_agents.investigation import InvestigationAgent
from aisecops.L05_gateway.llm_gateway import build_gateway
from aisecops.L06_mcp_servers import build_tool_registry


class InvestigationService:
    """事件调查业务出口。"""

    def __init__(self, orchestrator: Orchestrator) -> None:
        self.orchestrator = orchestrator

    async def investigate(self, host: str, question: str = "") -> AgentResult:
        task = Task(kind="investigation", payload={"host": host, "question": question})
        return await self.orchestrator.dispatch(task)


def build_investigation_service(ctx: AgentContext | None = None) -> InvestigationService:
    if ctx is None:
        ctx = AgentContext(llm=build_gateway(), tools=build_tool_registry())
    orchestrator = Orchestrator({"investigation": InvestigationAgent()}, ctx)
    return InvestigationService(orchestrator)
