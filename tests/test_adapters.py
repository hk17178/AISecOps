"""L06 工具适配器：CRUD + 启停 + 连通测试。"""

from fastapi.testclient import TestClient

from aisecops.L01_human_interface.api import app
from aisecops.L06_mcp_servers import Adapter, InMemoryAdapterStore, seed_demo_adapters
from aisecops.L06_mcp_servers import test_connectivity as check_connectivity


def test_adapter_store_crud() -> None:
    s = InMemoryAdapterStore()
    seed_demo_adapters(s, "http://localhost:9200")
    assert len(s.all()) == 3
    a = s.create("自定义", "custom", "x", "")
    assert s.set_enabled(a.id, False).enabled is False
    assert s.set_status(a.id, "已连", "2026-06-04 10:00:00").last_status == "已连"
    assert s.remove(a.id) is True


def test_connectivity_no_endpoint_and_outbound_gate() -> None:
    assert check_connectivity(Adapter(id="A1", name="x", endpoint=""), False, "t") == "未配置"
    # 外网端点 + 出域关 → 跳过（不真探）
    out = Adapter(id="A2", name="x", endpoint="https://example.com")
    assert check_connectivity(out, False, "t") == "跳过（出域关）"


client = TestClient(app)


def test_adapter_api_crud_test_audited() -> None:
    created = client.post(
        "/api/tools", json={"name": "测试防火墙", "category": "security_tools", "kind": "firewall", "actor": "admin"}
    ).json()
    aid = created["id"]
    # 列表
    adapters = client.get("/api/tools").json()["adapters"]
    assert any(a["id"] == aid for a in adapters)
    # 启停
    assert client.put(f"/api/tools/{aid}", json={"enabled": False, "actor": "admin"}).json()["enabled"] is False
    # 测连（无端点 → 未配置）
    rec = client.post(f"/api/tools/{aid}/test").json()
    assert rec["last_status"] == "未配置"
    # 审计
    audit = client.get("/api/audit").json()
    assert any(e["action"] == "adapter_create" and e["target"] == aid for e in audit["entries"])
    assert any(e["action"] == "adapter_test" and e["target"] == aid for e in audit["entries"])
    assert client.delete(f"/api/tools/{aid}").json()["status"] == "deleted"


def test_create_adapter_requires_name() -> None:
    assert client.post("/api/tools", json={"name": "  "}).status_code == 400
