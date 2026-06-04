"""L07 alert_triage 端到端测试 —— Orchestrator→Triage→ES 富化→研判。全 stub。"""

from aisecops.L02_agents import AgentContext, Orchestrator, TriageAgent
from aisecops.L05_gateway.llm_gateway import LLMGateway, StubProvider
from aisecops.L06_mcp_servers import StubLogSource, ToolRegistry
from aisecops.L07_secops_capabilities import AlertTriageService


def _service(canned: str, log_src: StubLogSource) -> tuple[AlertTriageService, AgentContext]:
    registry = ToolRegistry()
    registry.register_log_source(log_src)
    ctx = AgentContext(llm=LLMGateway([StubProvider(canned=canned)]), tools=registry)
    svc = AlertTriageService(Orchestrator({"alert_triage": TriageAgent()}, ctx))
    return svc, ctx


async def test_end_to_end_triage_with_enrichment() -> None:
    log_src = StubLogSource()
    svc, ctx = _service('{"verdict":"真威胁","confidence":0.91,"evidence":["PsExec"]}', log_src)

    result = await svc.triage({"host": "WIN-APP-07", "title": "PsExec 横移"})

    # 研判结果
    assert result.agent == "triage"
    assert result.data["verdict"] == "真威胁"
    assert result.abstained is False
    # 富化确实发生：ES（stub）被查询了该主机
    assert log_src.last_query is not None
    assert log_src.last_query["host"] == "WIN-APP-07"
    # 审计链完整 + 记忆已写
    assert ctx.audit.verify() is True
    assert ctx.memory.get("triage_history", "WIN-APP-07") is not None
