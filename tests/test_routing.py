"""L05 场景→模型路由（§4.4 按功能分配大模型）测试。"""

from fastapi.testclient import TestClient

from aisecops.L01_human_interface.api import app
from aisecops.L05_gateway.llm_gateway import (
    InMemoryRouteStore,
    LLMGateway,
    ScenarioRouter,
    StubProvider,
    seed_default_routes,
)


def _gw() -> LLMGateway:
    # 三个不同名的 provider（离线 stub，metadata 仍标 stub，但 provider 名/model 可区分）
    fast = StubProvider(model="qwen-turbo", name="快")
    strong = StubProvider(model="qwen-max", name="强")
    fallback = StubProvider()  # name=stub，末位兜底
    router = ScenarioRouter(
        {"L07/alert_triage": "快", "L07/investigation": "强"},
        default="快",
    )
    return LLMGateway([fast, strong, fallback], router=router)


# ---- 路由表本体 ----


def test_router_exact_and_prefix_and_default() -> None:
    r = ScenarioRouter({"L07/alert_triage": "快", "L08": "强"}, default="d")
    assert r.provider_name_for("L07/alert_triage") == "快"  # 精确
    assert r.provider_name_for("L08/correlation") == "强"  # 前缀
    assert r.provider_name_for("L07/unknown") == "d"  # 默认


def test_router_order_promotes_hit_and_keeps_rest() -> None:
    a, b, c = StubProvider(name="a"), StubProvider(name="b"), StubProvider(name="c")
    r = ScenarioRouter({"x": "b"})
    ordered = r.order("x", [a, b, c])
    assert ordered[0].name == "b"  # 命中的排队首
    assert [p.name for p in ordered[1:]] == ["a", "c"]  # 其余保序作降级
    # 路由指向不存在的 provider → 原序（走默认降级，不报错）
    assert [p.name for p in ScenarioRouter({"x": "zzz"}).order("x", [a, b, c])] == ["a", "b", "c"]


async def test_different_scenarios_hit_different_models() -> None:
    """§4.4 验收：分诊 vs 调查 路由到不同模型，metadata 体现不同 provider/model。"""
    gw = _gw()
    triage = await gw.call("有横向移动", scenario="L07/alert_triage")
    invest = await gw.call("调查这台主机", scenario="L07/investigation")
    assert triage.metadata.provider == "快" and triage.metadata.model == "qwen-turbo"
    assert invest.metadata.provider == "强" and invest.metadata.model == "qwen-max"


# ---- 存储 ----


def test_route_store_crud_and_seed() -> None:
    s = InMemoryRouteStore()
    assert s.all() == {}
    seed_default_routes(s)
    assert s.all()  # 写入了默认分档
    s.set("L07/x", "强")
    assert s.all()["L07/x"] == "强"
    assert s.remove("L07/x") is True
    assert s.remove("L07/x") is False


# ---- API ----

client = TestClient(app)


def test_routing_api_get_put_delete_audited() -> None:
    got = client.get("/api/routing").json()
    assert "routes" in got and "providers" in got
    assert len(got["routes"]) >= 1

    # 增改：指向已存在的 provider 才行
    prov = got["providers"][0]["name"]
    r = client.put("/api/routing", json={"scenario": "L07/test_scenario", "provider": prov, "actor": "admin"})
    assert r.status_code == 200
    after = client.get("/api/routing").json()["routes"]
    assert any(x["scenario"] == "L07/test_scenario" and x["provider"] == prov for x in after)

    # 审计留痕（C-23）
    audit = client.get("/api/audit").json()
    assert any(e["action"] == "routing_set" and e["target"] == "L07/test_scenario" for e in audit["entries"])

    # 不存在的 provider → 400
    bad = client.put("/api/routing", json={"scenario": "x", "provider": "不存在的模型"})
    assert bad.status_code == 400

    # 删除
    d = client.delete("/api/routing/L07/test_scenario")
    assert d.status_code == 200 and d.json()["status"] == "deleted"
