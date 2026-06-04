"""L02 Agent 运行时配置：阈值/cross-check/启停即时生效 + 换模型走路由。"""

from fastapi.testclient import TestClient

from aisecops.L01_human_interface.api import app
from aisecops.L02_agents import (
    AgentContext,
    InMemoryAgentConfigStore,
    Orchestrator,
    Task,
    TriageAgent,
    resolve_cross_check,
    seed_agent_configs,
)
from aisecops.L05_gateway.llm_gateway import LLMGateway, StubProvider


def test_resolve_cross_check() -> None:
    assert resolve_cross_check("on", False) is True
    assert resolve_cross_check("off", True) is False
    assert resolve_cross_check("auto", True) is True
    assert resolve_cross_check("auto", False) is False


async def test_threshold_change_takes_effect_live() -> None:
    # canned 置信度 0.6：阈值 0.5 → 真威胁；改阈值到 0.7 → abstain（待研判）
    cfgs = InMemoryAgentConfigStore()
    seed_agent_configs(cfgs)
    canned = '{"verdict":"真威胁","confidence":0.6,"evidence":[]}'
    ctx = AgentContext(llm=LLMGateway([StubProvider(canned=canned)]), agent_configs=cfgs)
    orch = Orchestrator({"alert_triage": TriageAgent()}, ctx)

    r1 = await orch.dispatch(Task(kind="alert_triage", payload={"host": "H"}))
    assert r1.data["verdict"] == "真威胁" and not r1.abstained

    cfgs.update("triage", {"confidence_threshold": 0.7})  # 即时生效
    r2 = await orch.dispatch(Task(kind="alert_triage", payload={"host": "H"}))
    assert r2.abstained and r2.data["verdict"] == "待研判"


client = TestClient(app)


def test_agents_api_exposes_config() -> None:
    data = client.get("/api/agents").json()
    triage = next(a for a in data["agents"] if a["name"] == "Triage")
    assert "config" in triage
    assert triage["config"]["scenario"] == "L07/alert_triage"
    assert "providers" in data


def test_update_agent_config_and_model_routing_audited() -> None:
    providers = client.get("/api/agents").json()["providers"]
    # 改阈值 + cross-check + 换模型
    upd = client.put(
        "/api/agents/triage",
        json={"confidence_threshold": 0.8, "cross_check_mode": "on", "model": providers[0], "actor": "admin"},
    ).json()
    assert upd["confidence_threshold"] == 0.8 and upd["cross_check_mode"] == "on"
    assert upd["model"] == providers[0]
    # 路由表确实被改（§4.4 单一事实源）
    routes = client.get("/api/routing").json()["routes"]
    assert any(r["scenario"] == "L07/alert_triage" and r["provider"] == providers[0] for r in routes)
    # 审计
    audit = client.get("/api/audit").json()
    assert any(e["action"] == "agent_config_update" and e["target"] == "triage" for e in audit["entries"])


def test_disabled_agent_refuses() -> None:
    client.put("/api/agents/triage", json={"enabled": False, "actor": "admin"})
    assert client.post("/api/triage", json={"host": "DEV-12"}).status_code == 403
    client.put("/api/agents/triage", json={"enabled": True, "actor": "admin"})  # 恢复
    assert client.post("/api/triage", json={"host": "DEV-12"}).status_code == 200
