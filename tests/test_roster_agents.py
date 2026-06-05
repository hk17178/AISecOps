"""Phase1.2：补齐的 Agent（Enrichment/Intel/Responder/Reporter）+ 统一编排端到端。"""

from __future__ import annotations

from aisecops.L02_agents import (
    AgentContext,
    EnrichmentAgent,
    IntelAgent,
    InvestigationAgent,
    Orchestrator,
    ReporterAgent,
    ResponderAgent,
    Task,
    TriageAgent,
)
from aisecops.L02_agents.correlation import CorrelationAgent
from aisecops.L02_agents.tickets import InMemoryTicketStore
from aisecops.L05_gateway.llm_gateway import LLMGateway, StubProvider
from aisecops.L07_secops_capabilities import AlertTriageService
from aisecops.L08_analytics_engines import build_ioc_store, seed_demo_iocs


class _Asset:
    def __init__(self, importance: str, role: str) -> None:
        self.importance = importance
        self.role = role


def _ctx() -> AgentContext:
    return AgentContext(llm=LLMGateway([StubProvider()]))


async def test_intel_agent_matches_iocs() -> None:
    iocs = build_ioc_store("")
    seed_demo_iocs(iocs)
    sample = iocs.all()[0]
    res = await IntelAgent(iocs).run(Task(kind="intel", payload={"host": "h", "title": f"外联 {sample.value}"}), _ctx())
    assert res.data["hit_count"] >= 1


async def test_enrichment_aggregates_asset_and_ioc() -> None:
    iocs = build_ioc_store("")

    def lookup(host: str) -> _Asset | None:
        return _Asset("关键", "域控") if host == "DC-01" else None

    res = await EnrichmentAgent(lookup, iocs).run(Task(kind="enrichment", payload={"host": "DC-01"}), _ctx())
    assert res.data["context"]["asset"]["importance"] == "关键"


async def test_responder_creates_hitl_ticket_with_audit() -> None:
    tickets = InMemoryTicketStore()
    ctx = _ctx()
    res = await ResponderAgent(tickets).run(
        Task(kind="respond", payload={"action": "隔离主机", "target": "WIN-9", "source_alert": "ALERT-1"}), ctx
    )
    assert tickets.pending_count() == 1
    assert res.data["ticket_id"]
    # C-23：建单留痕（修 #22）
    assert any(e.action == "ticket_auto_create" for e in ctx.audit.entries)


async def test_reporter_offline_auto_summary() -> None:
    res = await ReporterAgent().run(
        Task(kind="report", payload={"report_kind": "daily", "data": {"alerts_total": 5, "threats": 2}}), _ctx()
    )
    assert res.data["by_llm"] is False  # 离线 stub
    assert "告警 5 条" in res.data["summary"]


async def test_triage_flow_enriches_and_responds_via_orchestrator() -> None:
    # 关键资产 + 真威胁 → Enrichment 升级高风险、Responder 自动建单（全经 Orchestrator）
    iocs = build_ioc_store("")
    tickets = InMemoryTicketStore()
    ctx = AgentContext(llm=LLMGateway([StubProvider(canned='{"verdict":"真威胁","confidence":0.95,"evidence":[]}')]))

    def lookup(host: str) -> _Asset | None:
        return _Asset("关键", "域控") if host == "DC-01" else None

    agents = {
        "alert_triage": TriageAgent(),
        "investigation": InvestigationAgent(),
        "correlation": CorrelationAgent(),
        "enrichment": EnrichmentAgent(lookup, iocs),
        "intel": IntelAgent(iocs),
        "respond": ResponderAgent(tickets),
        "report": ReporterAgent(),
    }
    svc = AlertTriageService(Orchestrator(agents, ctx), tickets)
    result = await svc.triage({"host": "DC-01", "title": "可疑登录"})
    assert result.data["verdict"] == "真威胁"
    assert tickets.pending_count() == 1  # Responder 建了单
    # 审计含富化 + 研判 + 建单
    actions = {e.action for e in ctx.audit.entries}
    assert {"enrich", "verdict", "ticket_auto_create"} <= actions


def test_feedback_flywheel_end_to_end() -> None:
    # 反馈飞轮：批准工单 → Tuning 自动沉淀知识 → 知识库可检索到该案例（回流）
    from fastapi.testclient import TestClient

    from aisecops.L01_human_interface.api import app

    client = TestClient(app)
    before = client.get("/api/knowledge").json()["docs"]
    before_ids = {d["id"] for d in before}

    pending = [t for t in client.get("/api/tickets").json()["tickets"] if t["status"] == "待审"]
    assert pending, "需要至少一个待审工单"
    tid = pending[0]["id"]
    target = pending[0]["target"]
    r = client.post(f"/api/tickets/{tid}/approve", json={"reason": "确认处置"})
    assert r.status_code == 200

    # 知识库多了一篇来源为该工单的案例
    after = client.get("/api/knowledge").json()["docs"]
    new = [d for d in after if d["id"] not in before_ids]
    assert any(d.get("category") == "历史告警处理记录" for d in new)
    # 能被检索召回（飞轮回流的消费端）
    hits = client.post("/api/knowledge/search", json={"query": f"{target} 处置", "top_k": 5}).json()["hits"]
    assert any("处置案例" in h["title"] for h in hits)
