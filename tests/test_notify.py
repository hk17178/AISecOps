"""L02 通知中枢 + L06 发送适配器：渠道/规则 CRUD + 命中即发 + 发送记录。"""

from fastapi.testclient import TestClient

from aisecops.L01_human_interface.api import app
from aisecops.L02_agents import DispatchRule, mask_url, match_dispatch_rules
from aisecops.L06_mcp_servers import HttpNotifier, StubNotifier, build_notifier


def test_mask_url() -> None:
    assert mask_url("") == ""
    assert mask_url("https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=abcdef123456").endswith("123456")
    assert "qyapi" not in mask_url("https://qyapi.weixin.qq.com/x/abcdef123456")  # 不泄露主体


def test_build_notifier_gated_by_outbound() -> None:
    assert isinstance(build_notifier(False), StubNotifier)  # 出域关 → 安全默认
    assert isinstance(build_notifier(True), HttpNotifier)


def test_stub_notifier_no_network() -> None:
    n = StubNotifier()
    ok, err, note = n.send("wechat", "https://x/y", "标题", "正文")
    assert ok and "stub" in note
    ok2, err2, _ = n.send("wechat", "", "t", "c")  # 无地址 → 失败
    assert not ok2 and err2


def test_match_dispatch_rules() -> None:
    rules = [
        DispatchRule(id="DR-1", name="严重真威胁", trigger_verdict="真威胁", trigger_severity="严重", channel_id="CH-1"),
        DispatchRule(id="DR-2", name="停用", trigger_verdict="真威胁", channel_id="CH-1", enabled=False),
    ]
    assert [r.id for r in match_dispatch_rules({"verdict": "真威胁", "severity": "严重"}, rules)] == ["DR-1"]
    assert match_dispatch_rules({"verdict": "误报", "severity": "严重"}, rules) == []


client = TestClient(app)


def test_channel_crud_and_test_send_audited() -> None:
    created = client.post(
        "/api/channels", json={"name": "测试企微", "kind": "wechat", "url": "https://x/key123456", "actor": "admin"}
    ).json()
    cid = created["id"]
    assert created["configured"] is True
    # 列表不回明文
    chans = client.get("/api/channels").json()["channels"]
    ch = next(c for c in chans if c["id"] == cid)
    assert "key123456" not in str(ch) and ch["url_masked"]
    # 测试发送（离线 stub → 成功但未真实出域）
    rec = client.post(f"/api/channels/{cid}/test").json()
    assert rec["status"] == "成功" and "stub" in rec["note"]
    # 记录可查
    assert any(r["title"] == "AISECOPS 测试通知" for r in client.get("/api/dispatch/records").json()["records"])
    # 审计
    audit = client.get("/api/audit").json()
    assert any(e["action"] == "channel_create" and e["target"] == cid for e in audit["entries"])
    assert client.delete(f"/api/channels/{cid}").json()["status"] == "deleted"


def test_dispatch_rule_crud_and_run() -> None:
    ch = client.get("/api/channels").json()["channels"][0]["id"]
    rule = client.post(
        "/api/dispatch-rules",
        json={"name": "全部真威胁", "channel_id": ch, "trigger_verdict": "真威胁", "actor": "admin"},
    ).json()
    assert rule["id"].startswith("DR-")
    # 找一条真威胁告警，按规则分发
    alerts = client.get("/api/alerts").json()["alerts"]
    threat = next((a for a in alerts if a["verdict"] == "真威胁"), None)
    assert threat is not None
    res = client.post("/api/dispatch/run", json={"alert_id": threat["id"], "actor": "admin"}).json()
    assert res["matched"] >= 1 and len(res["sent"]) >= 1
    # 发送记录里有这条
    recs = client.get("/api/dispatch/records").json()["records"]
    assert any(threat["host"] in r["title"] for r in recs)
    client.delete(f"/api/dispatch-rules/{rule['id']}")


def test_create_channel_and_rule_validation() -> None:
    assert client.post("/api/channels", json={"name": "", "kind": "wechat"}).status_code == 400
    assert client.post("/api/channels", json={"name": "x", "kind": "sms"}).status_code == 400
    assert client.post("/api/dispatch-rules", json={"name": "x", "channel_id": "CH-999"}).status_code == 400
