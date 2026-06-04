"""L02 SOAR：剧本匹配/CRUD + 触发→HITL→执行→撤销 端到端。"""

from fastapi.testclient import TestClient

from aisecops.L01_human_interface.api import app
from aisecops.L02_agents import (
    InMemoryPlaybookStore,
    match_playbooks,
    seed_demo_playbooks,
)


def test_match_playbooks_by_verdict_and_keyword() -> None:
    s = InMemoryPlaybookStore()
    seed_demo_playbooks(s)
    # 真威胁 + 标题含"横向" → 命中"横移主机隔离"
    hit = match_playbooks({"verdict": "真威胁", "title": "检测到横向移动"}, s.all())
    assert any(p.name == "横移主机隔离" for p in hit)
    # 误报不触发
    assert match_playbooks({"verdict": "误报", "title": "横向移动"}, s.all()) == []
    # 停用的不触发
    pb = s.all()[0]
    s.set_enabled(pb.id, False)
    assert all(p.id != pb.id for p in match_playbooks({"verdict": "真威胁", "title": pb.trigger_keyword}, s.all()))


def test_playbook_store_crud() -> None:
    s = InMemoryPlaybookStore()
    pb = s.create("测试剧本", ["隔离主机"], "高", "真威胁", "", "x")
    assert pb.id == "PB-1" and pb.actions == ["隔离主机"]
    assert s.set_enabled(pb.id, False).enabled is False
    s.bump_runs(pb.id)
    assert s.get(pb.id).runs == 1
    assert s.remove(pb.id) is True


client = TestClient(app)


def test_soar_trigger_hitl_execute_undo_flow() -> None:
    pbs = client.get("/api/playbooks").json()["playbooks"]
    pb = pbs[0]

    # 触发 → 建 HITL 工单 + 执行记录(待审)
    res = client.post("/api/soar/trigger", json={"playbook_id": pb["id"], "target": "WIN-9", "actor": "admin"}).json()
    run_id = res["run"]["id"]
    ticket_id = res["ticket"]["id"]
    assert res["run"]["status"] == "待审" and res["ticket"]["status"] == "待审"

    # 批准工单 → 执行记录变"已执行"，并写 soar_execute 审计
    client.post(f"/api/tickets/{ticket_id}/approve", json={"reason": "确认处置", "actor": "admin"})
    runs = client.get("/api/soar/runs").json()["runs"]
    run = next(r for r in runs if r["id"] == run_id)
    assert run["status"] == "已执行"
    audit = client.get("/api/audit").json()
    assert any(e["action"] == "soar_execute" and e["target"] == run_id for e in audit["entries"])

    # 撤销 → "已撤销"
    undo = client.post(f"/api/soar/runs/{run_id}/undo", json={}).json()
    assert undo["status"] == "已撤销"
    # 重复撤销被拒
    assert client.post(f"/api/soar/runs/{run_id}/undo").status_code == 400


def test_soar_reject_marks_run_rejected() -> None:
    pb = client.get("/api/playbooks").json()["playbooks"][0]
    res = client.post("/api/soar/trigger", json={"playbook_id": pb["id"], "target": "WIN-X"}).json()
    client.post(f"/api/tickets/{res['ticket']['id']}/reject", json={"reason": "误判", "actor": "admin"})
    run = next(r for r in client.get("/api/soar/runs").json()["runs"] if r["id"] == res["run"]["id"])
    assert run["status"] == "已驳回"


def test_playbook_crud_api_audited() -> None:
    created = client.post(
        "/api/playbooks", json={"name": "压测剧本", "actions": ["封禁 IP"], "risk": "高", "actor": "admin"}
    ).json()
    pid = created["id"]
    assert client.put(f"/api/playbooks/{pid}", json={"enabled": False}).json()["enabled"] is False
    # 停用后不能触发
    assert client.post("/api/soar/trigger", json={"playbook_id": pid, "target": "H"}).status_code == 400
    audit = client.get("/api/audit").json()
    assert any(e["action"] == "playbook_create" and e["target"] == pid for e in audit["entries"])
    assert client.delete(f"/api/playbooks/{pid}").json()["status"] == "deleted"


def test_create_playbook_validates() -> None:
    assert client.post("/api/playbooks", json={"name": "", "actions": ["封禁 IP"]}).status_code == 400
    assert client.post("/api/playbooks", json={"name": "x", "actions": []}).status_code == 400
    assert client.post("/api/playbooks", json={"name": "x", "actions": ["乱来"]}).status_code == 400
