from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from aisecops.L02_agents import Principal

from ..auth_deps import ADMIN, require_role
from ..runtime import rt

router = APIRouter()


class LoginIn(BaseModel):
    username: str
    password: str


@router.post("/api/login")
async def login(body: LoginIn) -> dict[str, str]:
    """真用户校验（口令 scrypt 哈希；停用用户拒登）。成功签发会话令牌。"""
    user = rt.users.verify(body.username, body.password)
    if user is None:
        raise HTTPException(status_code=401, detail="用户名或密码错误，或账号已停用")
    token = rt.sessions.issue(user.username, user.role)
    return {"username": user.username, "role": user.role, "token": token}


@router.post("/api/logout")
async def logout(authorization: str | None = Header(default=None)) -> dict[str, str]:
    """登出：吊销当前令牌（幂等）。"""
    if authorization and authorization.lower().startswith("bearer "):
        rt.sessions.revoke(authorization[7:].strip())
    return {"status": "ok"}


@router.get("/api/users")
async def get_users(_: Principal = Depends(require_role(*ADMIN))) -> dict[str, Any]:
    return {"users": [u.model_dump() for u in rt.users.all()], "roles": ["管理员", "分析师", "普通查看"]}


class UserIn(BaseModel):
    username: str
    password: str = ""
    role: str = "普通查看"


@router.post("/api/users")
async def create_user(body: UserIn, principal: Principal = Depends(require_role(*ADMIN))) -> dict[str, Any]:
    if not body.username.strip() or not body.password:
        raise HTTPException(status_code=400, detail="用户名与初始口令不能为空")
    u = rt.users.create(body.username.strip(), body.password, body.role)
    rt.ctx.audit.append(actor=principal.username, action="user_create", target=u.username, details={"role": u.role})
    return u.model_dump()


class UserUpdateIn(BaseModel):
    role: str | None = None
    enabled: bool | None = None
    password: str | None = None


@router.put("/api/users/{username}")
async def update_user(
    username: str, body: UserUpdateIn, principal: Principal = Depends(require_role(*ADMIN))
) -> dict[str, Any]:
    fields = body.model_dump(exclude_none=True)
    u = rt.users.update(username, fields)
    if u is None:
        raise HTTPException(status_code=404, detail=f"用户 {username} 不存在")
    # 审计不记录口令本身（只记是否重置）
    rt.ctx.audit.append(
        actor=principal.username,
        action="user_update",
        target=username,
        details={"role": u.role, "enabled": u.enabled, "password_reset": "password" in fields},
    )
    return u.model_dump()


@router.delete("/api/users/{username}")
async def delete_user(username: str, principal: Principal = Depends(require_role(*ADMIN))) -> dict[str, Any]:
    if username == "admin":
        raise HTTPException(status_code=400, detail="不能删除内置 admin")
    removed = rt.users.remove(username)
    if removed:
        rt.ctx.audit.append(actor=principal.username, action="user_delete", target=username, details={})
    return {"status": "deleted" if removed else "not_found", "username": username}
