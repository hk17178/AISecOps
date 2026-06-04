"""L02 Agent 与 Memory/审计 的集成 —— dispatch 后审计链完整、记忆已写。"""

from aisecops.L02_agents import (
    AgentContext,
    Orchestrator,
    Task,
    TriageAgent,
)
from aisecops.L05_gateway.llm_gateway import LLMGateway, StubProvider


async def test_dispatch_writes_audit_and_memory() -> None:
    canned = '{"verdict":"真威胁","confidence":0.9,"evidence":["PsExec"]}'
    ctx = AgentContext(llm=LLMGateway([StubProvider(canned=canned)]))
    orch = Orchestrator({"alert_triage": TriageAgent()}, ctx)

    await orch.dispatch(Task(kind="alert_triage", payload={"host": "H1"}))

    # 审计：orchestrator.dispatch + triage.verdict 两条，链完整不可篡改
    assert len(ctx.audit.entries) == 2
    assert ctx.audit.entries[0].action == "dispatch"
    assert ctx.audit.entries[1].action == "verdict"
    assert ctx.audit.verify() is True

    # 记忆：triage_history 记下了 H1 的研判
    stored = ctx.memory.get("triage_history", "H1")
    assert stored is not None
    assert stored["verdict"] == "真威胁"
