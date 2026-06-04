"""L02 Agent 测试 —— Orchestrator 路由 + Triage 研判/abstain/cross-check。全 stub。"""

import pytest

from aisecops.L02_agents import (
    AgentContext,
    Orchestrator,
    OrchestratorError,
    Task,
    TriageAgent,
)
from aisecops.L05_gateway.llm_gateway import LLMGateway, StubProvider


def _ctx(canned: str) -> AgentContext:
    return AgentContext(llm=LLMGateway([StubProvider(canned=canned)]))


async def test_orchestrator_routes_to_triage() -> None:
    ctx = _ctx('{"verdict":"真威胁","confidence":0.94,"evidence":["PsExec 横移"]}')
    orch = Orchestrator({"alert_triage": TriageAgent()}, ctx)
    result = await orch.dispatch(Task(kind="alert_triage", payload={"host": "WIN-APP-07"}))
    assert result.agent == "triage"
    assert result.ok is True
    assert result.data["verdict"] == "真威胁"
    assert result.abstained is False


async def test_orchestrator_unknown_kind_raises() -> None:
    ctx = _ctx('{"verdict":"误报","confidence":0.1,"evidence":[]}')
    orch = Orchestrator({"alert_triage": TriageAgent()}, ctx)
    with pytest.raises(OrchestratorError):
        await orch.dispatch(Task(kind="nope"))


async def test_triage_abstains_on_low_confidence() -> None:
    ctx = _ctx('{"verdict":"真威胁","confidence":0.2,"evidence":[]}')
    agent = TriageAgent(confidence_threshold=0.5)
    result = await agent.run(Task(kind="alert_triage", payload={"x": 1}), ctx)
    assert result.abstained is True
    assert result.data["verdict"] == "待研判"


async def test_triage_passes_high_confidence() -> None:
    ctx = _ctx('{"verdict":"误报","confidence":0.85,"evidence":["已知扫描器"]}')
    agent = TriageAgent(confidence_threshold=0.5)
    result = await agent.run(Task(kind="alert_triage", payload={}), ctx)
    assert result.abstained is False
    assert result.data["verdict"] == "误报"


async def test_triage_abstains_on_cross_check_disagree() -> None:
    # 两个 provider 给不同研判 + 高风险触发 cross-check → 不一致 → 转人工
    gw = LLMGateway(
        [
            StubProvider(model="a", canned='{"verdict":"真威胁","confidence":0.9,"evidence":[]}'),
            StubProvider(model="b", canned='{"verdict":"误报","confidence":0.9,"evidence":[]}'),
        ]
    )
    ctx = AgentContext(llm=gw)
    agent = TriageAgent()
    result = await agent.run(Task(kind="alert_triage", payload={}, high_risk=True), ctx)
    assert result.abstained is True
    assert result.data["verdict"] == "待研判"
