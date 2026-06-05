"""Phase 3.2 · Skills(SOP) 库（L04，ADR-0013）：匹配 + CRUD + 调查附 SOP。"""

from __future__ import annotations

from fastapi.testclient import TestClient

from aisecops.L01_human_interface.api import app
from aisecops.L04_ai_assets_models import build_skill_store, match_skills, seed_demo_skills

client = TestClient(app)


def test_match_skills_by_scenario() -> None:
    s = build_skill_store("")
    seed_demo_skills(s)
    hits = match_skills("主机疑似遭遇勒索软件加密", s.all())
    assert any(h.scenario == "勒索" for h in hits)
    assert match_skills("一切正常无异常", s.all()) == []


def test_skills_api_crud_and_audit() -> None:
    lst = client.get("/api/skills").json()
    assert "调查SOP" in lst["categories"] and len(lst["skills"]) >= 2  # 种子两条

    created = client.post(
        "/api/skills",
        json={"name": "钓鱼应急SOP", "category": "处置SOP", "scenario": "钓鱼", "steps": ["重置口令", "排查外联"]},
    ).json()
    sid = created["id"]
    assert client.post("/api/skills", json={"name": "空", "steps": []}).status_code == 400  # 步骤必填
    upd = client.put(f"/api/skills/{sid}", json={"enabled": False}).json()
    assert upd["enabled"] is False
    assert client.delete(f"/api/skills/{sid}").json()["status"] == "deleted"
    audit = client.get("/api/audit").json()
    assert any(e["action"] == "skill_create" and e["target"] == sid for e in audit["entries"])


async def test_investigation_attaches_matching_sop() -> None:
    from aisecops.L02_agents import AgentContext, InvestigationAgent, Task
    from aisecops.L05_gateway.llm_gateway import LLMGateway, StubProvider

    skills = build_skill_store("")
    seed_demo_skills(skills)
    ctx = AgentContext(llm=LLMGateway([StubProvider()]), skills=skills)
    res = await InvestigationAgent().run(
        Task(kind="investigation", payload={"host": "H1", "question": "这次横向移动怎么查"}), ctx
    )
    sop = res.data.get("sop", [])
    assert any("横向移动" in s["name"] for s in sop)  # 附上了匹配的 SOP 步骤
