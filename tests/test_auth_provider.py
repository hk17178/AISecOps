"""Phase 5 · 认证联邦：本地 + AD/LDAP（ADR-0014）。LDAP 用注入 bind，不连真服务器。"""

from __future__ import annotations

from aisecops.L02_agents import (
    LdapAuthenticator,
    LocalAuthenticator,
    build_authenticator,
)
from aisecops.L02_agents.users import build_user_store, seed_demo_users


def _users():
    s = build_user_store("")
    seed_demo_users(s)  # dev: admin/analyst 口令 aisecops
    return s


def test_local_authenticator() -> None:
    auth = LocalAuthenticator(_users())
    p = auth.authenticate("admin", "aisecops")
    assert p and p.role == "管理员"
    assert auth.authenticate("admin", "wrong") is None
    assert auth.mode == "local"


def test_ldap_role_mapping_via_injected_bind() -> None:
    # 注入假 bind：bob 属 SecAdmins → 管理员；其它组 → 默认普通查看
    def fake_bind(url: str, user_dn: str, password: str) -> list[str]:
        if password != "good":
            raise ValueError("bind 失败")
        return ["SecAdmins"] if "bob" in user_dn else ["Other"]

    auth = LdapAuthenticator(
        "ldap://x", "uid={username},dc=corp", {"SecAdmins": "管理员", "SOC": "分析师"}, bind=fake_bind
    )
    bob = auth.authenticate("bob", "good")
    assert bob and bob.role == "管理员" and bob.username == "bob"
    alice = auth.authenticate("alice", "good")
    assert alice and alice.role == "普通查看"  # 未映射组 → 默认
    assert auth.authenticate("bob", "bad") is None  # bind 失败且无兜底
    assert auth.mode == "ldap"


def test_ldap_falls_back_to_local_when_unreachable() -> None:
    def broken_bind(url: str, user_dn: str, password: str) -> list[str]:
        raise ConnectionError("LDAP 不可达")

    auth = LdapAuthenticator("ldap://x", "uid={username}", {}, bind=broken_bind, fallback_local=_users())
    # LDAP 挂了 → 本地兜底账号仍可登（防把人锁外面）
    p = auth.authenticate("admin", "aisecops")
    assert p and p.role == "管理员"


def test_build_authenticator_selects_mode() -> None:
    assert build_authenticator(_users()).mode == "local"
    ldap = build_authenticator(
        _users(), ldap_url="ldap://x", ldap_user_template="uid={username}", ldap_role_map_json='{"A":"管理员"}'
    )
    assert ldap.mode == "ldap"
