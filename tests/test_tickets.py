"""L02 工单/HITL 工作流 + triage 自动建单 + 端点测试。"""

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from aisecops.L01_human_interface.api import app
from aisecops.L02_agents import (
    AgentContext,
    InMemoryTicketStore,
    TicketError,
    build_ticket_store,
)
from aisecops.L05_gateway.llm_gateway import LLMGateway, StubProvider
from aisecops.L07_secops_capabilities import build_alert_triage_service


def _clock() -> datetime:
    return datetime(2026, 6, 4, 17, 30, tzinfo=timezone.utc)


def test_ticket_workflow() -> None:
    s = InMemoryTicketStore(clock=_clock)
    t = s.create("隔离主机", "H1")
    assert t.status == "待审"
    assert s.pending_count() == 1
    s.decide(t.id, "已批准")
    assert s.all()[0].status == "已批准"
    assert s.pending_count() == 0
    with pytest.raises(TicketError):
        s.decide(t.id, "已驳回")  # 已处理
    with pytest.raises(TicketError):
        s.decide("TKT-999", "已批准")  # 不存在


def test_build_ticket_store_falls_back_to_memory() -> None:
    # 无 DATABASE_URL（CI 路径）→ 内存实现，可用且不依赖 PG
    s = build_ticket_store("")
    assert isinstance(s, InMemoryTicketStore)
    # 连不上的 PG 串也回退内存，不让平台起不来
    s2 = build_ticket_store("postgresql://nobody@127.0.0.1:1/nope")
    assert isinstance(s2, InMemoryTicketStore)


async def test_triage_creates_hitl_ticket_on_threat() -> None:
    store = InMemoryTicketStore(clock=_clock)
    canned = '{"verdict":"真威胁","confidence":0.95,"evidence":[]}'
    ctx = AgentContext(llm=LLMGateway([StubProvider(canned=canned)]))
    svc = build_alert_triage_service(ctx, store)
    await svc.triage({"host": "WIN-APP-07"})
    assert store.pending_count() == 1
    assert store.all()[0].action == "隔离主机"
    assert store.all()[0].target == "WIN-APP-07"


async def test_triage_no_ticket_when_abstain() -> None:
    store = InMemoryTicketStore(clock=_clock)
    # 默认 stub 回显非 JSON → 离线占位 confidence 0 → abstain（待研判），不建单
    ctx = AgentContext(llm=LLMGateway([StubProvider()]))
    svc = build_alert_triage_service(ctx, store)
    await svc.triage({"host": "X"})
    assert store.pending_count() == 0


client = TestClient(app)


def test_ticket_endpoints_with_reason_and_audit() -> None:
    tickets = client.get("/api/tickets").json()["tickets"]
    pending = [t for t in tickets if t["status"] == "待审"]
    assert len(pending) >= 1
    tid = pending[0]["id"]
    r = client.post(f"/api/tickets/{tid}/approve", json={"reason": "确认属实", "actor": "admin"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "已批准"
    assert body["reason"] == "确认属实"
    assert body["decided_by"] == "admin"
    # 审计链记录了这次决策且校验通过（C-23）
    audit = client.get("/api/audit").json()
    assert audit["verified"] is True
    assert any(e["target"] == tid and e["action"] == "ticket_approve" for e in audit["entries"])
    # 重复审批被拒
    assert client.post(f"/api/tickets/{tid}/approve", json={"reason": "x", "actor": "admin"}).status_code == 400
