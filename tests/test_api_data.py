"""L01 只读数据端点测试：/api/agents、/api/tools、/api/cost。"""

from fastapi.testclient import TestClient

from aisecops.L01_human_interface.api import app

client = TestClient(app)


def test_agents_roster() -> None:
    resp = client.get("/api/agents")
    assert resp.status_code == 200
    agents = resp.json()["agents"]
    # Triage / Investigation 已实现
    assert any(a["name"] == "Triage" and a["status"] == "实现" for a in agents)
    assert any(a["name"] == "Investigation" and a["status"] == "实现" for a in agents)
    # Responder 仍是规划
    assert any(a["name"] == "Responder" and a["status"] == "规划" for a in agents)


def test_tools_registry() -> None:
    resp = client.get("/api/tools")
    assert resp.status_code == 200
    tools = resp.json()["tools"]
    # 默认无 ES 凭证 → 注册了 ES（stub）日志源
    assert any("Elasticsearch" in t["name"] for t in tools)


def test_cost_summary() -> None:
    resp = client.get("/api/cost")
    assert resp.status_code == 200
    data = resp.json()
    assert "spent_cny" in data
    assert "providers" in data
    assert data["monthly_cap_cny"] >= 0
