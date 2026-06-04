"""L02/L12 RBAC + 配置持久化 + 密钥加密（§4.5）。"""

from fastapi.testclient import TestClient

from aisecops.L01_human_interface.api import app
from aisecops.L02_agents import InMemoryUserStore, seed_demo_users
from aisecops.L12_core_support.config_store import InMemoryConfigStore
from aisecops.L12_core_support.secrets import (
    decrypt_secret,
    encrypt_secret,
    hash_password,
    verify_password,
)


def test_password_hash_and_verify() -> None:
    h = hash_password("s3cret")
    assert "$" in h and "s3cret" not in h
    assert verify_password("s3cret", h) is True
    assert verify_password("wrong", h) is False


def test_secret_encrypt_roundtrip() -> None:
    token = encrypt_secret("sk-abc-123")
    assert token and "sk-abc-123" not in token  # 密文不含明文
    assert decrypt_secret(token) == "sk-abc-123"
    assert decrypt_secret("garbage") == ""  # 坏数据不崩
    assert encrypt_secret("") == ""


def test_config_store_encrypts_secret_keys() -> None:
    s = InMemoryConfigStore()
    s.set("monthly_budget_cny", "999")  # 非敏感
    s.set("llm_api_key", "sk-secret")  # 敏感 → 加密存
    raw = s._items["llm_api_key"][0]  # type: ignore[attr-defined]
    assert "sk-secret" not in raw  # 落库密文
    assert s.all_decrypted()["llm_api_key"] == "sk-secret"  # 读时解密
    assert s.all_decrypted()["monthly_budget_cny"] == "999"


def test_user_store_crud_and_auth() -> None:
    u = InMemoryUserStore()
    seed_demo_users(u)
    assert u.verify("admin", "aisecops").role == "管理员"
    assert u.verify("admin", "wrong") is None
    u.create("bob", "pw1", "分析师")
    assert u.verify("bob", "pw1").role == "分析师"
    # 停用 → 拒登
    u.update("bob", {"enabled": False})
    assert u.verify("bob", "pw1") is None
    # 改口令
    u.update("bob", {"enabled": True, "password": "pw2"})
    assert u.verify("bob", "pw2") is not None and u.verify("bob", "pw1") is None
    assert u.remove("bob") is True


client = TestClient(app)


def test_login_real_user() -> None:
    assert client.post("/api/login", json={"username": "admin", "password": "aisecops"}).json()["role"] == "管理员"
    assert client.post("/api/login", json={"username": "admin", "password": "x"}).status_code == 401


def test_user_api_crud_audited() -> None:
    client.post("/api/users", json={"username": "carol", "password": "init", "role": "分析师", "actor": "admin"})
    assert client.post("/api/login", json={"username": "carol", "password": "init"}).json()["role"] == "分析师"
    # 停用 → 登录被拒
    client.put("/api/users/carol", json={"enabled": False, "actor": "admin"})
    assert client.post("/api/login", json={"username": "carol", "password": "init"}).status_code == 401
    audit = client.get("/api/audit").json()
    assert any(e["action"] == "user_create" and e["target"] == "carol" for e in audit["entries"])
    assert client.delete("/api/users/carol").json()["status"] == "deleted"
    # 不能删内置 admin
    assert client.delete("/api/users/admin").status_code == 400


def test_config_put_persists_and_masks_secret() -> None:
    client.put("/api/config", json={"monthly_budget_cny": 888, "allow_outbound": True, "actor": "admin"})
    cfg = client.get("/api/config").json()
    assert cfg["monthly_budget_cny"] == 888.0 and cfg["allow_outbound"] is True
    # 设密钥：GET 只回是否已配置，不回明文
    client.put("/api/config", json={"llm_api_key": "sk-should-not-leak", "actor": "admin"})
    cfg2 = client.get("/api/config").json()
    assert cfg2["llm_api_key_set"] is True
    assert "sk-should-not-leak" not in str(cfg2)
    # 复位出域，避免影响其它测试
    client.put("/api/config", json={"allow_outbound": False, "actor": "admin"})
