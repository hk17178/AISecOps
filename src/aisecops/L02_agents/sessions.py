"""L02 · 会话令牌（平台核心 IAM 的认证态）。

登录成功后签发不透明随机令牌（bearer token），写操作端点据令牌解析出已认证主体
（Principal），从而：
1. 拦截匿名写/审批（C-8：HITL 与高风险动作必须有真实身份）；
2. 审计 actor 由服务端从令牌解析（C-23：问责主体不可由客户端伪造）。

令牌存内存 + TTL：进程重启即失效，重新登录即可；审计链本身落 PG 持久化，二者职责不同。
"""

from __future__ import annotations

import secrets
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from pydantic import BaseModel


class Principal(BaseModel):
    """已认证主体（写操作的 actor 来源）。"""

    username: str
    role: str


def _now() -> datetime:
    return datetime.now(timezone.utc)


class SessionStore:
    """内存会话表：签发 / 解析 / 吊销令牌，带 TTL 过期。"""

    def __init__(self, ttl_hours: int = 12, clock: Callable[[], datetime] = _now) -> None:
        self._ttl = timedelta(hours=ttl_hours)
        self._clock = clock
        self._sessions: dict[str, tuple[Principal, datetime]] = {}  # token -> (principal, expire_at)

    def issue(self, username: str, role: str) -> str:
        """签发令牌；返回不可猜测的随机串。"""
        token = secrets.token_urlsafe(32)
        self._sessions[token] = (Principal(username=username, role=role), self._clock() + self._ttl)
        return token

    def resolve(self, token: str) -> Principal | None:
        """解析令牌为主体；无效/过期返回 None（过期则顺手清除）。"""
        item = self._sessions.get(token)
        if item is None:
            return None
        principal, expire_at = item
        if self._clock() >= expire_at:
            self._sessions.pop(token, None)
            return None
        return principal

    def revoke(self, token: str) -> bool:
        """登出：吊销令牌。"""
        return self._sessions.pop(token, None) is not None
