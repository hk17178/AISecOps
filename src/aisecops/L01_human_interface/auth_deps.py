"""L01 · HTTP 鉴权依赖（会话令牌 → 已认证主体）。

HTTP 关注点留在 L01（ADR-0011）：从 Authorization: Bearer <token> 解析出 Principal，
按角色放行写/审批端点。写端点统一 `Depends(require_role(...))`，匿名→401、越权→403。

测试缝：所有角色守卫内部都依赖唯一的 `get_principal`；测试经 `app.dependency_overrides`
覆盖它即可全局放行（见 tests/conftest.py），无需逐请求带令牌。
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import Depends, Header, HTTPException

from aisecops.L02_agents import Principal

from .runtime import rt

# 角色集合常量：写操作至少需分析师；系统管理类仅管理员
ADMIN = ("管理员",)
WRITE = ("管理员", "分析师")


async def get_principal(authorization: str | None = Header(default=None)) -> Principal:
    """从 Bearer 令牌解析已认证主体；缺失/失效 → 401。"""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="缺少会话令牌，请先登录")
    token = authorization[7:].strip()
    principal = rt.sessions.resolve(token)
    if principal is None:
        raise HTTPException(status_code=401, detail="会话令牌无效或已过期，请重新登录")
    return principal


def require_role(*allowed: str) -> Callable[[Principal], Coroutine[Any, Any, Principal]]:
    """生成"需指定角色"的依赖；allowed 为空表示任意已认证主体即可。"""

    async def _dep(principal: Principal = Depends(get_principal)) -> Principal:
        if allowed and principal.role not in allowed:
            raise HTTPException(status_code=403, detail="当前角色无权执行该操作")
        return principal

    return _dep
