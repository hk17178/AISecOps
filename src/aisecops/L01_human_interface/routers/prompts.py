from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from aisecops.L02_agents import Principal

from ..auth_deps import ADMIN, require_role
from ..runtime import rt

router = APIRouter()


@router.get("/api/prompts")
async def get_prompts() -> dict[str, Any]:
    """Prompt 列表（每个 key 的活跃版本概览）。"""
    out = []
    for key in rt.prompts.keys():
        act = rt.prompts.active(key)
        out.append(
            {
                "key": key,
                "active_version": act.version if act else 0,
                "versions": len(rt.prompts.versions(key)),
                "updated": act.ts if act else "",
            }
        )
    return {"prompts": out}


@router.get("/api/prompts/{key:path}")
async def get_prompt_detail(key: str) -> dict[str, Any]:
    """某 Prompt 的活跃版本 + 全部历史版本（用于 diff/回滚）。"""
    versions = rt.prompts.versions(key)
    if not versions:
        raise HTTPException(status_code=404, detail=f"Prompt {key} 不存在")
    act = rt.prompts.active(key)
    return {
        "key": key,
        "active_version": act.version if act else 0,
        "versions": [v.model_dump() for v in versions],
    }


class PromptRollbackIn(BaseModel):
    version: int
    actor: str = "未知"


# 注意：rollback 路由必须定义在贪婪的 {key:path} save 之前，否则被其捕获
@router.post("/api/prompts/{key:path}/rollback")
async def rollback_prompt(
    key: str, body: PromptRollbackIn, principal: Principal = Depends(require_role(*ADMIN))
) -> dict[str, Any]:
    """回滚：把活跃版本指回指定旧版本。"""
    pv = rt.prompts.rollback(key, body.version, principal.username)
    if pv is None:
        raise HTTPException(status_code=404, detail=f"{key} 无版本 {body.version}")
    rt.ctx.audit.append(
        actor=principal.username, action="prompt_rollback", target=key, details={"version": body.version}
    )
    return pv.model_dump()


class PromptSaveIn(BaseModel):
    content: str
    note: str = ""
    actor: str = "未知"


@router.post("/api/prompts/{key:path}")
async def save_prompt(
    key: str, body: PromptSaveIn, principal: Principal = Depends(require_role(*ADMIN))
) -> dict[str, Any]:
    """编辑保存为新版本（自动置为活跃，旧版本保留可回滚）。"""
    if not body.content.strip():
        raise HTTPException(status_code=400, detail="内容不能为空")
    pv = rt.prompts.save(key, body.content, body.note.strip(), principal.username)
    rt.ctx.audit.append(actor=principal.username, action="prompt_save", target=key, details={"version": pv.version})
    return pv.model_dump()
