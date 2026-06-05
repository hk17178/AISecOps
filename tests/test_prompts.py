"""L04 Prompt 治理：版本化 save/rollback + API。"""

from fastapi.testclient import TestClient

from aisecops.L01_human_interface.api import app
from aisecops.L04_ai_assets_models import InMemoryPromptStore, seed_demo_prompts


def test_prompt_versioning_and_rollback() -> None:
    s = InMemoryPromptStore()
    seed_demo_prompts(s)
    assert "triage/system" in s.keys()
    v1 = s.active("triage/system")
    assert v1.version == 1
    v2 = s.save("triage/system", "新内容 v2", "调整口径", "muzi")
    assert v2.version == 2 and v2.active
    assert s.active("triage/system").version == 2
    assert len(s.versions("triage/system")) == 2
    # 回滚到 v1
    rb = s.rollback("triage/system", 1, "muzi")
    assert rb.version == 1
    assert s.active("triage/system").version == 1
    assert s.rollback("triage/system", 99, "x") is None


client = TestClient(app)


def test_prompt_api_edit_history_rollback_audited() -> None:
    detail = client.get("/api/prompts/triage/system").json()
    base = detail["active_version"]
    # 编辑保存新版本
    saved = client.post(
        "/api/prompts/triage/system", json={"content": "测试新版本内容", "note": "test", "actor": "admin"}
    ).json()
    assert saved["version"] == base + 1 and saved["active"]
    # 历史里有两个以上版本
    d2 = client.get("/api/prompts/triage/system").json()
    assert d2["active_version"] == base + 1 and len(d2["versions"]) >= 2
    # 回滚到 base
    rb = client.post("/api/prompts/triage/system/rollback", json={"version": base, "actor": "admin"}).json()
    assert rb["version"] == base
    assert client.get("/api/prompts/triage/system").json()["active_version"] == base
    # 审计
    audit = client.get("/api/audit").json()
    assert any(e["action"] == "prompt_save" and e["target"] == "triage/system" for e in audit["entries"])
    assert any(e["action"] == "prompt_rollback" and e["target"] == "triage/system" for e in audit["entries"])


def test_prompt_list_and_validation() -> None:
    lst = client.get("/api/prompts").json()["prompts"]
    assert any(p["key"] == "chat/system" for p in lst)
    assert client.post("/api/prompts/triage/system", json={"content": "  "}).status_code == 400
    assert client.get("/api/prompts/nonexistent/key").status_code == 404


def test_agent_prompt_hot_load() -> None:
    # 改 Prompt → Agent governed_prompt 即时变；安全脚手架始终在（不可被改掉）⑤
    from aisecops.L02_agents import AgentContext, build_agent_config_store, seed_agent_configs
    from aisecops.L02_agents.triage import _GUIDANCE, _SCAFFOLD
    from aisecops.L04_ai_assets_models import build_prompt_store, seed_demo_prompts
    from aisecops.L05_gateway.llm_gateway import LLMGateway, StubProvider

    cfgs = build_agent_config_store("")
    seed_agent_configs(cfgs)
    prompts = build_prompt_store("")
    seed_demo_prompts(prompts)
    ctx = AgentContext(llm=LLMGateway([StubProvider()]), agent_configs=cfgs, prompts=prompts)

    # 默认 = 种子 guidance
    assert ctx.governed_prompt("triage", _GUIDANCE).startswith("你是安全告警分诊助手")
    # 改 prompt → 立刻生效
    prompts.save("triage/system", "只关注勒索软件迹象。", note="t", author="tester")
    assert ctx.governed_prompt("triage", _GUIDANCE) == "只关注勒索软件迹象。"
    # 无 prompts store → 回退代码默认
    assert AgentContext(llm=LLMGateway([StubProvider()])).governed_prompt("triage", _GUIDANCE) == _GUIDANCE
    # 安全脚手架（防注入/JSON schema）始终独立存在
    assert "防提示注入" in _SCAFFOLD and "JSON" in _SCAFFOLD
