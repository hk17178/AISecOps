"""L01 FastAPI 测试台接口测试 —— 用 stub 网关隔离，绝不打真实 LLM。"""

from fastapi.testclient import TestClient

from aisecops.L01_human_interface.api import app, get_gateway
from aisecops.L05_gateway.llm_gateway import LLMGateway, StubProvider

# 覆盖网关依赖：无论 .env 是否配了真 key，测试都只用 stub
app.dependency_overrides[get_gateway] = lambda: LLMGateway([StubProvider()])

client = TestClient(app)


def test_health() -> None:
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_index_page_served() -> None:
    resp = client.get("/")
    assert resp.status_code == 200
    assert "L05 Gateway 测试台" in resp.text


def test_llm_call_via_stub() -> None:
    resp = client.post("/api/llm/call", json={"prompt": "测试告警", "scenario": "L01/test"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["content"].startswith("[stub:L01/test]")
    assert data["metadata"]["provider"] == "stub"
    assert data["metadata"]["total_tokens"] > 0
