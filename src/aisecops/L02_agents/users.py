"""L02 · 用户与 RBAC（平台核心 IAM）。

替换占位登录：真用户表（口令 scrypt 哈希存储，不存明文）+ 三角色。
角色：管理员 / 分析师 / 普通查看。仓储模式，默认内存，配 DATABASE_URL 用 PG。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel

from aisecops.L12_core_support.secrets import hash_password, verify_password

ROLES = ("管理员", "分析师", "普通查看")


class User(BaseModel):
    """对外用户信息（不含口令哈希）。"""

    username: str
    role: str = "普通查看"
    enabled: bool = True


class UserStore(ABC):
    @abstractmethod
    def all(self) -> list[User]:
        raise NotImplementedError

    @abstractmethod
    def verify(self, username: str, password: str) -> User | None:
        """校验口令；成功返回 User，失败/停用返回 None。"""
        raise NotImplementedError

    @abstractmethod
    def create(self, username: str, password: str, role: str) -> User:
        raise NotImplementedError

    @abstractmethod
    def update(self, username: str, fields: dict[str, Any]) -> User | None:
        """改角色/启停/重置口令（password 字段非空则重置）。"""
        raise NotImplementedError

    @abstractmethod
    def remove(self, username: str) -> bool:
        raise NotImplementedError


def _apply(role: str | None, enabled: Any) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if role in ROLES:
        out["role"] = role
    if enabled is not None:
        out["enabled"] = bool(enabled)
    return out


class InMemoryUserStore(UserStore):
    def __init__(self) -> None:
        self._users: dict[str, dict[str, Any]] = {}  # username -> {hash, role, enabled}

    def all(self) -> list[User]:
        return [User(username=u, role=d["role"], enabled=d["enabled"]) for u, d in self._users.items()]

    def verify(self, username: str, password: str) -> User | None:
        d = self._users.get(username)
        if d is None or not d["enabled"] or not verify_password(password, d["hash"]):
            return None
        return User(username=username, role=d["role"], enabled=True)

    def create(self, username: str, password: str, role: str) -> User:
        self._users[username] = {
            "hash": hash_password(password),
            "role": role if role in ROLES else "普通查看",
            "enabled": True,
        }
        return User(username=username, role=self._users[username]["role"])

    def update(self, username: str, fields: dict[str, Any]) -> User | None:
        d = self._users.get(username)
        if d is None:
            return None
        upd = _apply(fields.get("role"), fields.get("enabled"))
        d.update(upd)
        if fields.get("password"):
            d["hash"] = hash_password(str(fields["password"]))
        return User(username=username, role=d["role"], enabled=d["enabled"])

    def remove(self, username: str) -> bool:
        return self._users.pop(username, None) is not None


class PgUserStore(UserStore):
    def __init__(self, database_url: str) -> None:
        from aisecops.L12_core_support.db import get_pool

        self._pool = get_pool(database_url)
        with self._pool.connection() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS users ("
                "username text PRIMARY KEY, password_hash text, role text DEFAULT '普通查看', enabled boolean DEFAULT true)"
            )

    def all(self) -> list[User]:
        with self._pool.connection() as conn:
            rows = conn.execute("SELECT username, role, enabled FROM users ORDER BY username").fetchall()
        return [User(username=r[0], role=r[1] or "普通查看", enabled=bool(r[2])) for r in rows]

    def verify(self, username: str, password: str) -> User | None:
        with self._pool.connection() as conn:
            row = conn.execute(
                "SELECT password_hash, role, enabled FROM users WHERE username=%s", (username,)
            ).fetchone()
        if row is None or not row[2] or not verify_password(password, row[0] or ""):
            return None
        return User(username=username, role=row[1] or "普通查看", enabled=True)

    def create(self, username: str, password: str, role: str) -> User:
        r = role if role in ROLES else "普通查看"
        with self._pool.connection() as conn:
            conn.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (%s,%s,%s) "
                "ON CONFLICT (username) DO UPDATE SET password_hash=EXCLUDED.password_hash, role=EXCLUDED.role",
                (username, hash_password(password), r),
            )
        return User(username=username, role=r)

    def update(self, username: str, fields: dict[str, Any]) -> User | None:
        with self._pool.connection() as conn:
            cur = conn.execute("SELECT role, enabled FROM users WHERE username=%s", (username,)).fetchone()
            if cur is None:
                return None
            upd = _apply(fields.get("role"), fields.get("enabled"))
            role = str(upd.get("role") or cur[0] or "普通查看")
            enabled = bool(upd.get("enabled", bool(cur[1])))
            if fields.get("password"):
                conn.execute(
                    "UPDATE users SET role=%s, enabled=%s, password_hash=%s WHERE username=%s",
                    (role, enabled, hash_password(str(fields["password"])), username),
                )
            else:
                conn.execute("UPDATE users SET role=%s, enabled=%s WHERE username=%s", (role, enabled, username))
        return User(username=username, role=role, enabled=enabled)

    def remove(self, username: str) -> bool:
        with self._pool.connection() as conn:
            cur = conn.execute("DELETE FROM users WHERE username=%s", (username,))
            return bool(cur.rowcount)


def build_user_store(database_url: str = "") -> UserStore:
    if database_url:
        try:
            return PgUserStore(database_url)
        except Exception:
            pass
    return InMemoryUserStore()


def seed_demo_users(store: UserStore) -> None:
    """初始用户（首次空库）。沿用默认口令 aisecops，保持向后兼容。"""
    if store.all():
        return
    store.create("admin", "aisecops", "管理员")
    store.create("analyst", "aisecops", "分析师")
