"""L01 /api/triage 端到端接口测试 —— 用 stub 服务隔离，不打真 LLM/ES。"""

from fastapi.testclient import TestClient

from aisecops.L01_human_interface.api import app, get_triage_service
from aisecops.L02_agents import AgentContext, Orchestrator, TriageAgent
from aisecops.L05_gateway.llm_gateway import LLMGateway, StubProvider
from aisecops.L06_mcp_servers import StubLogSource, ToolRegistry
from aisecops.L07_secops_capabilities import AlertTriageService


def _stub_service() -> AlertTriageService:
    registry = ToolRegistry()
    registry.register_log_source(StubLogSource())
    canned = '{"verdict":"真威胁","confidence":0.9,"evidence":["PsExec"]}'
    ctx = AgentContext(llm=LLMGateway([StubProvider(canned=canned)]), tools=registry)
    return AlertTriageService(Orchestrator({"alert_triage": TriageAgent()}, ctx))


app.dependency_overrides[get_triage_service] = _stub_service
client = TestClient(app)


def test_triage_endpoint() -> None:
    resp = client.post("/api/triage", json={"host": "WIN-APP-07", "title": "PsExec 横移"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["agent"] == "triage"
    assert data["data"]["verdict"] == "真威胁"
