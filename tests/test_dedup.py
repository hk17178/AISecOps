"""L08 告警降噪：指纹/抑制规则/引擎决策 + 入库降噪端到端。"""

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from aisecops.L01_human_interface.api import app
from aisecops.L08_analytics_engines import (
    DedupEngine,
    InMemorySuppressionStore,
    SuppressionRule,
    fingerprint,
    rule_matches,
)
from aisecops.L09_data_platform.alert_store import InMemoryAlertStore


def _clock() -> datetime:
    return datetime(2026, 6, 4, 17, 30, tzinfo=timezone.utc)


def test_fingerprint_stable_and_distinguishes() -> None:
    a = {"source": "EDR", "host": "WIN-1", "title": "横向移动"}
    assert fingerprint(a) == fingerprint({"source": "edr", "host": "win-1", "title": "横向移动"})  # 归一化
    assert fingerprint(a) != fingerprint({**a, "host": "WIN-2"})


def test_rule_matches_kinds() -> None:
    assert rule_matches(SuppressionRule(id="1", name="t", kind="host", pattern="DEV-*"), {"host": "DEV-03"})
    assert not rule_matches(SuppressionRule(id="1", name="t", kind="host", pattern="DEV-*"), {"host": "WIN-1"})
    assert rule_matches(SuppressionRule(id="2", name="t", kind="keyword", pattern="心跳"), {"title": "健康检查心跳"})
    assert rule_matches(SuppressionRule(id="3", name="t", kind="source", pattern="scanner"), {"source": "scanner"})
    # 停用规则不命中
    assert not rule_matches(
        SuppressionRule(id="4", name="t", kind="keyword", pattern="x", enabled=False), {"title": "x"}
    )


def test_engine_suppress_merge_new() -> None:
    rules = InMemorySuppressionStore()
    rules.create("测试机", "host", "DEV-*")
    eng = DedupEngine(rules)
    store = InMemoryAlertStore(clock=_clock)

    # 抑制：DEV-* 命中
    d = eng.evaluate({"host": "DEV-03", "source": "S", "title": "t"}, store.recent(50))
    assert d.action == "suppress" and d.rule_id

    # 新建：第一条真告警
    fields = {"host": "WIN-1", "source": "EDR", "title": "横向移动"}
    d1 = eng.evaluate(fields, store.recent(50))
    assert d1.action == "new"
    store.add({**fields, "fingerprint": d1.fingerprint})

    # 归并：同指纹、时间窗内
    d2 = eng.evaluate(fields, store.recent(50), now=_clock())
    assert d2.action == "merge" and d2.target_id == "ALERT-0001"


def test_engine_outside_window_is_new() -> None:
    eng = DedupEngine(InMemorySuppressionStore(), window_secs=300)
    store = InMemoryAlertStore(clock=_clock)
    fields = {"host": "WIN-1", "source": "EDR", "title": "横向移动"}
    store.add({**fields, "fingerprint": fingerprint(fields)})
    # 10 分钟后（超 5min 窗）→ 不归并
    later = datetime(2026, 6, 4, 17, 40, tzinfo=timezone.utc)
    assert eng.evaluate(fields, store.recent(50), now=later).action == "new"


client = TestClient(app)


def test_ingest_dedup_and_stats_flow() -> None:
    before = client.get("/api/dedupe/stats").json()
    base = {"hostname": "WIN-DUP", "level": "high", "message": "重复测试告警-唯一"}
    # 连灌 3 条完全相同 → 第 1 条 new，后 2 条 merge
    r1 = client.post("/api/ingest/alert", json=base).json()
    assert r1["deduped"] == "new"
    r2 = client.post("/api/ingest/alert", json=base).json()
    assert r2["deduped"] == "merged"
    client.post("/api/ingest/alert", json=base)

    # 噪声：DEV-* 主机被 seed 的"测试环境主机"规则抑制
    rs = client.post("/api/ingest/alert", json={"hostname": "DEV-99", "message": "噪声"}).json()
    assert rs["deduped"] == "suppressed"

    after = client.get("/api/dedupe/stats").json()
    assert after["raw_total"] >= before["raw_total"] + 4  # 进了 4 个事件
    assert after["breakdown"]["exact_window_merged"] >= 2  # 折叠掉 2 条
    assert after["breakdown"]["suppressed"] >= 1
    assert any(s["host"] == "DEV-99" for s in after["suppressed_recent"])  # 可回溯


def test_suppression_rule_crud_audited() -> None:
    created = client.post(
        "/api/suppression-rules", json={"name": "压测扫描", "kind": "keyword", "pattern": "loadtest", "actor": "admin"}
    ).json()
    rid = created["id"]
    # 灌一条命中关键字 → 被抑制
    sup = client.post("/api/ingest/alert", json={"hostname": "H", "message": "loadtest probe"}).json()
    assert sup["deduped"] == "suppressed"
    # 停用后同样告警不再抑制 → new
    client.put(f"/api/suppression-rules/{rid}", json={"enabled": False, "actor": "admin"})
    again = client.post("/api/ingest/alert", json={"hostname": "H2", "message": "loadtest probe"}).json()
    assert again["deduped"] in ("new", "merged")
    # 审计留痕
    audit = client.get("/api/audit").json()
    assert any(e["action"] == "suppression_create" and e["target"] == rid for e in audit["entries"])
    # 删除
    assert client.delete(f"/api/suppression-rules/{rid}").json()["status"] == "deleted"
