"""L08 威胁情报 IoC：匹配 + CRUD + 入库命中标红/计数。"""

from fastapi.testclient import TestClient

from aisecops.L01_human_interface.api import app
from aisecops.L08_analytics_engines import InMemoryIocStore, match_iocs, seed_demo_iocs


def test_match_iocs() -> None:
    s = InMemoryIocStore()
    seed_demo_iocs(s)
    hits = match_iocs({"host": "h1", "title": "出站到 evil-c2.top 域名"}, s.all())
    assert any(i.value == "evil-c2.top" for i in hits)
    assert match_iocs({"host": "clean", "title": "正常登录"}, s.all()) == []


def test_ioc_store_crud() -> None:
    s = InMemoryIocStore()
    i = s.create("1.2.3.4", "IP", "高", "测试")
    assert i.id == "IOC-1"
    s.bump_hit(i.id)
    assert s.all()[0].hits == 1
    assert s.remove(i.id) is True


client = TestClient(app)


def test_ioc_crud_api_and_alert_hit_marking() -> None:
    # 新建一个 IoC
    ioc = client.post("/api/iocs", json={"value": "bad-domain-xyz.io", "type": "域名", "actor": "admin"}).json()
    iid = ioc["id"]
    # 灌一条命中该 IoC 的告警
    client.post("/api/ingest/alert", json={"hostname": "H", "message": "连接 bad-domain-xyz.io 可疑"})
    # 告警列表里该条带 ioc_hits
    alerts = client.get("/api/alerts").json()["alerts"]
    hit_alert = next((a for a in alerts if "bad-domain-xyz.io" in a.get("ioc_hits", [])), None)
    assert hit_alert is not None
    # IoC 命中计数 +1
    iocs = client.get("/api/iocs").json()["iocs"]
    assert next(i for i in iocs if i["id"] == iid)["hits"] >= 1
    # 审计 + 删除
    audit = client.get("/api/audit").json()
    assert any(e["action"] == "ioc_create" and e["target"] == iid for e in audit["entries"])
    assert client.delete(f"/api/iocs/{iid}").json()["status"] == "deleted"


def test_create_ioc_validation() -> None:
    assert client.post("/api/iocs", json={"value": "  "}).status_code == 400
    assert client.post("/api/iocs", json={"value": "x", "type": "邮箱"}).status_code == 400
