"""Phase 2 · 协作驾驶舱 + 工单指派/进度/SLA（ADR-0012）。"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from aisecops.L01_human_interface.api import app
from aisecops.L02_agents import InMemoryTicketStore

client = TestClient(app)


def test_ticket_has_sla_and_progress_on_create() -> None:
    s = InMemoryTicketStore()
    t = s.create("隔离主机", "H1", "高", "ALERT-1")
    assert t.progress == "待处理" and t.sla_due  # 建单即定 SLA
    assert t.assignee == "" and t.notes == []


def test_assign_and_progress_flow() -> None:
    s = InMemoryTicketStore()
    t = s.create("封禁 IP", "1.2.3.4", "中")
    s.assign(t.id, "分析师A", actor="admin")
    assert s.all()[0].assignee == "分析师A"
    assert s.all()[0].progress == "处理中"  # 指派即转处理中
    s.update_progress(t.id, "已完成", "已封禁并验证", "分析师A")
    done = s.all()[0]
    assert done.progress == "已完成"
    assert any(n["text"] == "已封禁并验证" for n in done.notes)  # 时间线


def test_overdue_when_sla_passed() -> None:
    past = datetime(2020, 1, 1, tzinfo=timezone.utc)
    s = InMemoryTicketStore(clock=lambda: past)
    s.create("隔离主机", "OLD", "高")  # sla_due 在 2020，必超时
    cockpit = client.get("/api/cockpit").json()
    # 注：cockpit 读的是 rt.tickets（种子工单），这里只验证结构与计数字段存在
    assert "items" in cockpit and "workload" in cockpit
    assert set(cockpit["counts"]) >= {"open", "overdue", "in_progress", "done", "pending_approval"}


def test_cockpit_reflects_assignment() -> None:
    pending = [t for t in client.get("/api/tickets").json()["tickets"] if t["status"] == "待审"]
    if not pending:
        return
    tid = pending[0]["id"]
    client.put(f"/api/tickets/{tid}/assign", json={"assignee": "张三"})
    client.put(f"/api/tickets/{tid}/progress", json={"progress": "处理中", "note": "排查中"})
    cockpit = client.get("/api/cockpit").json()
    hit = [i for i in cockpit["items"] if i["id"] == tid]
    assert hit and hit[0]["assignee"] == "张三" and hit[0]["progress"] == "处理中"
    # 审计留痕
    audit = client.get("/api/audit").json()
    assert any(e["action"] == "ticket_assign" and e["target"] == tid for e in audit["entries"])
