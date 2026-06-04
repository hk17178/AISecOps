"""L08 关联聚类 + L02 关联 Agent + 关联分析端到端 + 安全事件确认。"""

from fastapi.testclient import TestClient

from aisecops.L01_human_interface.api import app
from aisecops.L08_analytics_engines import correlate
from aisecops.L09_data_platform.alert_store import Alert
from aisecops.L09_data_platform.event_store import InMemoryEventStore


def _a(id_: str, host: str, title: str, ts: str = "2026-06-04 17:30:00", suppressed: bool = False) -> Alert:
    return Alert(id=id_, ts=ts, host=host, title=title, source="EDR", suppressed=suppressed)


def test_cluster_by_same_host() -> None:
    alerts = [
        _a("ALERT-0001", "WIN-7", "横向移动"),
        _a("ALERT-0002", "WIN-7", "凭证滥用"),
        _a("ALERT-0003", "DEV-1", "孤立告警"),
    ]
    clusters = correlate(alerts)
    assert len(clusters) == 1
    assert set(clusters[0].alert_ids) == {"ALERT-0001", "ALERT-0002"}
    assert "WIN-7" in clusters[0].reason


def test_cluster_by_shared_ip() -> None:
    alerts = [
        _a("ALERT-0001", "h1", "出站到 185.10.0.9"),
        _a("ALERT-0002", "h2", "C2 185.10.0.9 回连"),
    ]
    clusters = correlate(alerts)
    assert len(clusters) == 1 and "185.10.0.9" in clusters[0].reason


def test_suppressed_excluded_and_time_window() -> None:
    # 被抑制的不参与
    assert correlate([_a("A1", "h", "x", suppressed=True), _a("A2", "h", "y", suppressed=True)]) == []
    # 超时间窗（默认 1800s）不关联
    far = [_a("A1", "h", "x", ts="2026-06-04 10:00:00"), _a("A2", "h", "y", ts="2026-06-04 18:00:00")]
    assert correlate(far) == []


def test_event_store_crud() -> None:
    s = InMemoryEventStore()
    ev = s.create("勒索前兆", "高", "WIN-7 横移+凭证", ["ALERT-0001", "ALERT-0002"])
    assert ev.id == "EVT-101" and ev.alert_ids == ["ALERT-0001", "ALERT-0002"]
    assert s.count() == 1 and s.all()[0].title == "勒索前兆"


client = TestClient(app)


def test_correlate_api_and_confirm_event_audited() -> None:
    # seed 里 WIN-APP-07 有两条告警 → 至少一个候选簇
    res = client.post("/api/correlate").json()
    assert res["count"] >= 1
    cand = res["candidates"][0]
    assert "cluster" in cand and "conclusion" in cand
    assert cand["cluster"]["size"] >= 2
    # 离线 stub 出 schema 合法占位 → abstain（诚实），结构在
    assert "attack_chain" in cand["conclusion"] and "citations" in cand["conclusion"]

    # 人工确认 → 建安全事件 + 审计
    ids = cand["cluster"]["alert_ids"]
    ev = client.post(
        "/api/events/confirm",
        json={"title": "WIN-APP-07 疑似勒索前兆", "severity": "严重", "alert_ids": ids, "actor": "admin"},
    ).json()
    assert ev["id"].startswith("EVT-")
    events = client.get("/api/events").json()["events"]
    assert any(e["id"] == ev["id"] for e in events)
    audit = client.get("/api/audit").json()
    assert any(e["action"] == "event_confirm" and e["target"] == ev["id"] for e in audit["entries"])


def test_confirm_event_requires_title() -> None:
    assert client.post("/api/events/confirm", json={"title": "  ", "alert_ids": []}).status_code == 400
