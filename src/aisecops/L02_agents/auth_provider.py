"""L02 · 认证联邦（IAM）—— 本地账号 + AD/LDAP（ADR-0014）。

把登录认证抽象成 Authenticator.authenticate()，本地表与 AD/LDAP 二选一（配了 LDAP_URL 用 LDAP，
否则本地）。LDAP 走 stub-first + 依赖注入：bind/取组可注入（测试不连真服务器），真实现 lazy import
ldap3（未配 LDAP 根本不碰）。守 ADR-0003：单组织 AD，不做多租户。
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from collections.abc import Callable

from .sessions import Principal
from .users import UserStore

# 注入点：(url, user_dn, password) -> 该用户的 AD 组列表；bind 失败抛异常
LdapBind = Callable[[str, str, str], list[str]]


class Authenticator(ABC):
    @abstractmethod
    def authenticate(self, username: str, password: str) -> Principal | None:
        """认证成功返回 Principal，失败返回 None。"""
        raise NotImplementedError

    @property
    @abstractmethod
    def mode(self) -> str:
        """认证模式标识（local / ldap），给前端只读展示。"""
        raise NotImplementedError


class LocalAuthenticator(Authenticator):
    """本地用户表（scrypt 口令）。"""

    def __init__(self, users: UserStore) -> None:
        self._users = users

    def authenticate(self, username: str, password: str) -> Principal | None:
        user = self._users.verify(username, password)
        return Principal(username=user.username, role=user.role) if user else None

    @property
    def mode(self) -> str:
        return "local"


def _real_ldap_bind(url: str, user_dn: str, password: str) -> list[str]:
    """真实 LDAP bind + 取组（lazy import ldap3；只有真用 LDAP 才需要装）。"""
    try:
        import ldap3  # type: ignore[import-untyped, import-not-found]
    except ImportError as exc:  # 配了 LDAP 却没装库 → 明确报错，不静默
        raise RuntimeError("启用了 LDAP 但未安装 ldap3，请 `pip install ldap3`") from exc
    server = ldap3.Server(url, get_info=ldap3.NONE)
    conn = ldap3.Connection(server, user=user_dn, password=password, auto_bind=True)
    conn.search(user_dn, "(objectClass=*)", attributes=["memberOf"])
    groups: list[str] = []
    if conn.entries:
        raw = conn.entries[0].entry_attributes_as_dict.get("memberOf", [])
        groups = [str(g).split(",")[0].split("=")[-1] for g in raw]
    conn.unbind()
    return groups


class LdapAuthenticator(Authenticator):
    """AD/LDAP 认证：bind 校验口令 + AD 组→角色映射。

    bind 注入便于测试（不连真服务器）；fallback_local 在 LDAP 不可达时兜底本地账号（防把人锁外面）。
    """

    def __init__(
        self,
        url: str,
        user_template: str,
        role_map: dict[str, str],
        *,
        bind: LdapBind | None = None,
        fallback_local: UserStore | None = None,
        default_role: str = "普通查看",
    ) -> None:
        self._url = url
        self._user_template = user_template  # 如 uid={username},ou=people,dc=corp
        self._role_map = role_map  # AD 组 -> 角色
        self._bind = bind or _real_ldap_bind
        self._fallback = fallback_local
        self._default_role = default_role

    def _role_for(self, groups: list[str]) -> str:
        for g in groups:
            if g in self._role_map:
                return self._role_map[g]
        return self._default_role

    def authenticate(self, username: str, password: str) -> Principal | None:
        user_dn = self._user_template.format(username=username)
        try:
            groups = self._bind(self._url, user_dn, password)
        except Exception:
            # LDAP 不可达/认证失败 → 兜底本地账号（仅当配置了 fallback）
            if self._fallback is not None:
                u = self._fallback.verify(username, password)
                return Principal(username=u.username, role=u.role) if u else None
            return None
        return Principal(username=username, role=self._role_for(groups))

    @property
    def mode(self) -> str:
        return "ldap"


def build_authenticator(
    users: UserStore,
    *,
    ldap_url: str = "",
    ldap_user_template: str = "",
    ldap_role_map_json: str = "",
    bind: LdapBind | None = None,
) -> Authenticator:
    """配了 LDAP_URL 用 LDAP（本地兜底），否则纯本地。"""
    if ldap_url and ldap_user_template:
        try:
            role_map = json.loads(ldap_role_map_json) if ldap_role_map_json else {}
        except json.JSONDecodeError:
            role_map = {}
        return LdapAuthenticator(ldap_url, ldap_user_template, role_map, bind=bind, fallback_local=users)
    return LocalAuthenticator(users)
