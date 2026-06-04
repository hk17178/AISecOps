"""L02 Investigation Agent + L07 调查服务 + 端点测试。"""

from fastapi.testclient import TestClient

from aisecops.L01_human_interface.api import app
from aisecops.L02_agents import AgentContext
from aisecops.L05_gateway.llm_gateway import LLMGateway, StubProvider
from aisecops.L06_mcp_servers import StubLogSource, ToolRegistry
from aisecops.L07_secops_capabilities import build_investigation_service


async def test_investigation_builds_timeline_from_logs() -> None:
    registry = ToolRegistry()
    registry.register_log_source(StubLogSource())
    ctx = AgentContext(llm=LLMGateway([StubProvider()]), tools=registry)
    svc = build_investigation_service(ctx)

    result = await svc.investigate("WIN-APP-07")
    assert result.agent == "investigation"
    # 时间线来自 ES（stub）真实日志
    assert result.data["log_count"] >= 1
    assert len(result.data["timeline"]) >= 1
    # 离线 stub LLM 出不了摘要 → abstain
    assert result.abstained is True


client = TestClient(app)


def test_investigate_endpoint() -> None:
    resp = client.post("/api/investigate", json={"host": "WIN-APP-07", "question": "攻击链？"})
    assert resp.status_code == 200
    data = resp.json()
    assert "timeline" in data["data"]
    assert data["agent"] == "investigation"
