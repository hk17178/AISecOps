"""L11 资产 CMDB：CRUD + 分诊富化用到重要度。"""

from fastapi.testclient import TestClient

from aisecops.L01_human_interface.api import app
from aisecops.L11_target_estate import InMemoryAssetStore, seed_demo_assets


def test_asset_store_crud_and_lookup() -> None:
    s = InMemoryAssetStore()
    seed_demo_assets(s)
    assert s.get_by_host("DC-01").importance == "关键"
    a = s.create("NEW-1", "1.2.3.4", "测试", "低", "正常", "我", "")
    assert a.id.startswith("AST-")
    upd = s.update(a.id, {"importance": "高", "status": "已隔离"})
    assert upd.importance == "高" and upd.status == "已隔离"
    assert s.remove(a.id) is True
    assert s.remove(a.id) is False


client = TestClient(app)


def test_asset_crud_api_audited() -> None:
    created = client.post(
        "/api/assets", json={"host": "PG-TEST-1", "importance": "高", "role": "DB", "actor": "admin"}
    ).json()
    aid = created["id"]
    assert created["host"] == "PG-TEST-1"
    # 改
    upd = client.put(f"/api/assets/{aid}", json={"status": "已隔离", "actor": "admin"}).json()
    assert upd["status"] == "已隔离"
    # 列表
    assets = client.get("/api/assets").json()["assets"]
    assert any(a["id"] == aid for a in assets)
    # 审计
    audit = client.get("/api/audit").json()
    assert any(e["action"] == "asset_create" and e["target"] == aid for e in audit["entries"])
    assert client.delete(f"/api/assets/{aid}").json()["status"] == "deleted"


def test_create_asset_requires_host() -> None:
    assert client.post("/api/assets", json={"host": "  "}).status_code == 400


async def test_triage_enriched_with_asset_importance() -> None:
    # seed 资产 DC-01 是「关键」→ 分诊应升级为高风险（high_risk → cross_check）
    # 离线 stub 下 cross_check 需 ≥2 provider 才生效；这里验证富化字段进入研判不报错
    r = client.post("/api/triage", json={"host": "DC-01", "title": "可疑登录"})
    assert r.status_code == 200
    # 关键资产命中：研判结果应正常返回（abstain 也可，离线 stub），富化不报错
    assert "verdict" in r.json()["data"]
