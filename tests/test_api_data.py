"""L01 只读数据端点测试：/api/agents、/api/tools、/api/cost。"""

from fastapi.testclient import TestClient

from aisecops.L01_human_interface.api import app

client = TestClient(app)


def test_agents_roster() -> None:
    resp = client.get("/api/agents")
    assert resp.status_code == 200
    agents = resp.json()["agents"]
    # 7+1 Agent 群全部已编码（含 Tuning 反馈飞轮）
    for name in ("Triage", "Investigation", "Correlation", "Enrichment", "Intel", "Responder", "Reporter", "Tuning"):
        assert any(a["name"] == name and a["status"] == "实现" for a in agents), name


def test_tools_registry() -> None:
    resp = client.get("/api/tools")
    assert resp.status_code == 200
    adapters = resp.json()["adapters"]
    # 默认 seed 了 ES 适配器
    assert any("Elasticsearch" in a["name"] for a in adapters)


def test_cost_summary() -> None:
    resp = client.get("/api/cost")
    assert resp.status_code == 200
    data = resp.json()
    assert "spent_cny" in data
    assert "providers" in data
    assert data["monthly_cap_cny"] >= 0
