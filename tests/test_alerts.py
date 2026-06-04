"""L09 告警库 + L10 入库 + 端点测试。"""

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from aisecops.L01_human_interface.api import app
from aisecops.L09_data_platform.alert_store import (
    InMemoryAlertStore,
    alert_stats,
    build_alert_store,
    seed_demo_alerts,
)
from aisecops.L10_data_collection.ingest import normalize_alert


def _clock() -> datetime:
    return datetime(2026, 6, 4, 17, 30, tzinfo=timezone.utc)


def test_store_add_and_list() -> None:
    s = InMemoryAlertStore(clock=_clock)
    a = s.add({"host": "H1", "title": "t", "severity": "严重"})
    assert a.id == "ALERT-0001"
    assert a.host == "H1"
    s.add({"host": "H2"})
    assert s.count() == 2
    assert s.recent()[0].host == "H2"  # 倒序，最新在前


def test_build_alert_store_falls_back_to_memory() -> None:
    # 无 DATABASE_URL（CI 路径）→ 内存实现；连不上的 PG 串也回退，不让平台起不来
    assert isinstance(build_alert_store(""), InMemoryAlertStore)
    assert isinstance(build_alert_store("postgresql://nobody@127.0.0.1:1/nope"), InMemoryAlertStore)


def test_normalize_alert() -> None:
    f = normalize_alert({"hostname": "WIN-07", "level": "Critical", "message": "PsExec"})
    assert f["host"] == "WIN-07"
    assert f["severity"] == "严重"
    assert f["title"] == "PsExec"


def test_alert_stats() -> None:
    s = InMemoryAlertStore(clock=_clock)
    seed_demo_alerts(s)
    st = alert_stats(s)
    assert st["total"] == 6
    assert st["threats"] == 3
    assert "严重" in st["by_severity"]


client = TestClient(app)


def test_ingest_list_dashboard_flow() -> None:
    before = client.get("/api/dashboard").json()["total"]
    r = client.post(
        "/api/ingest/alert",
        json={"hostname": "WIN-99", "level": "high", "message": "测试入库"},
    )
    assert r.status_code == 200
    assert r.json()["host"] == "WIN-99"
    after = client.get("/api/dashboard").json()
    assert after["total"] == before + 1
    alerts = client.get("/api/alerts").json()["alerts"]
    assert any(a["host"] == "WIN-99" for a in alerts)
