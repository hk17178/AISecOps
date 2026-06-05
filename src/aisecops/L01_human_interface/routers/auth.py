from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..runtime import rt

router = APIRouter()


class LoginIn(BaseModel):
    username: str
    password: str


@router.post("/api/login")
async def login(body: LoginIn) -> dict[str, str]:
    """真用户校验（口令 scrypt 哈希；停用用户拒登）。"""
    user = rt.users.verify(body.username, body.password)
    if user is None:
        raise HTTPException(status_code=401, detail="用户名或密码错误，或账号已停用")
    return {"username": user.username, "role": user.role}


@router.get("/api/users")
async def get_users() -> dict[str, Any]:
    return {"users": [u.model_dump() for u in rt.users.all()], "roles": ["管理员", "分析师", "普通查看"]}


class UserIn(BaseModel):
    username: str
    password: str = ""
    role: str = "普通查看"
    actor: str = "未知"


@router.post("/api/users")
async def create_user(body: UserIn) -> dict[str, Any]:
    if not body.username.strip() or not body.password:
        raise HTTPException(status_code=400, detail="用户名与初始口令不能为空")
    u = rt.users.create(body.username.strip(), body.password, body.role)
    rt.ctx.audit.append(actor=body.actor, action="user_create", target=u.username, details={"role": u.role})
    return u.model_dump()


class UserUpdateIn(BaseModel):
    role: str | None = None
    enabled: bool | None = None
    password: str | None = None
    actor: str = "未知"


@router.put("/api/users/{username}")
async def update_user(username: str, body: UserUpdateIn) -> dict[str, Any]:
    fields = body.model_dump(exclude_none=True)
    actor = str(fields.pop("actor", "未知"))
    u = rt.users.update(username, fields)
    if u is None:
        raise HTTPException(status_code=404, detail=f"用户 {username} 不存在")
    # 审计不记录口令本身（只记是否重置）
    rt.ctx.audit.append(
        actor=actor,
        action="user_update",
        target=username,
        details={"role": u.role, "enabled": u.enabled, "password_reset": "password" in fields},
    )
    return u.model_dump()


@router.delete("/api/users/{username}")
async def delete_user(username: str, actor: str = "未知") -> dict[str, Any]:
    if username == "admin":
        raise HTTPException(status_code=400, detail="不能删除内置 admin")
    removed = rt.users.remove(username)
    if removed:
        rt.ctx.audit.append(actor=actor, action="user_delete", target=username, details={})
    return {"status": "deleted" if removed else "not_found", "username": username}
