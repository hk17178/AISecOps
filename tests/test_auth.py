"""会话令牌鉴权的真实拦截测试（C-8 / C-23）。

这里**移除** conftest 的 admin 放行 override，验证真实守卫：
匿名→401、越权→403、带正确令牌→200，且审计 actor 取自令牌而非请求体。
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from aisecops.L01_human_interface.api import app
from aisecops.L01_human_interface.auth_deps import get_principal

client = TestClient(app)


def _no_bypass() -> None:
    """去掉自动放行，走真实 get_principal。"""
    app.dependency_overrides.pop(get_principal, None)


def test_write_endpoint_rejects_anonymous() -> None:
    _no_bypass()
    # 无 Authorization 头 → 401（在进入处理函数前就被拦）
    r = client.post("/api/tickets/TKT-x/approve", json={"reason": "x"})
    assert r.status_code == 401


def test_login_issues_token_and_authorizes() -> None:
    _no_bypass()
    login = client.post("/api/login", json={"username": "admin", "password": "aisecops"})
    assert login.status_code == 200
    token = login.json()["token"]
    assert token
    # 带令牌访问管理员端点 → 200
    r = client.get("/api/users", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200


def test_analyst_forbidden_on_admin_endpoint() -> None:
    _no_bypass()
    login = client.post("/api/login", json={"username": "analyst", "password": "aisecops"})
    token = login.json()["token"]
    # 分析师建用户（管理员专属）→ 403
    r = client.post(
        "/api/users",
        json={"username": "x", "password": "p", "role": "普通查看"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403


def test_audit_actor_comes_from_token_not_body() -> None:
    _no_bypass()
    token = client.post("/api/login", json={"username": "admin", "password": "aisecops"}).json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    # 即使请求体自报 actor=伪造者，审计也应记录令牌身份 admin
    tickets = client.get("/api/tickets", headers=headers).json()["tickets"]
    pending = [t for t in tickets if t["status"] == "待审"]
    if pending:
        tid = pending[0]["id"]
        client.post(f"/api/tickets/{tid}/approve", json={"reason": "ok", "actor": "伪造者"}, headers=headers)
        audit = client.get("/api/audit", headers=headers).json()
        hit = [e for e in audit["entries"] if e["target"] == tid and e["action"] == "ticket_approve"]
        assert hit and hit[0]["actor"] == "admin"
