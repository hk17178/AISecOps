"""L01 · Skills(SOP) 管理 router（L04，ADR-0013）。

标准操作流程 CRUD（鉴权+审计+持久化）。Skill 是"怎么做某类事"的步骤清单，调查时按场景
自动匹配附给分析师照做；与 SOAR Playbook(自动处置)、Prompt(模型人设)、知识库(经验文档) 分工。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from aisecops.L02_agents import Principal
from aisecops.L04_ai_assets_models import SKILL_CATEGORIES

from ..auth_deps import WRITE, require_role
from ..runtime import rt

router = APIRouter()


@router.get("/api/skills")
async def list_skills() -> dict[str, Any]:
    return {"skills": [s.model_dump() for s in rt.skills.all()], "categories": list(SKILL_CATEGORIES)}


class SkillIn(BaseModel):
    name: str
    category: str = "调查SOP"
    scenario: str = ""
    steps: list[str] = []
    refs: list[str] = []


@router.post("/api/skills")
async def create_skill(body: SkillIn, principal: Principal = Depends(require_role(*WRITE))) -> dict[str, Any]:
    if not body.name.strip() or not body.steps:
        raise HTTPException(status_code=400, detail="名称与至少一个步骤不能为空")
    s = rt.skills.create(body.model_dump())
    rt.ctx.audit.append(actor=principal.username, action="skill_create", target=s.id, details={"name": s.name})
    return s.model_dump()


class SkillUpdateIn(BaseModel):
    name: str | None = None
    category: str | None = None
    scenario: str | None = None
    steps: list[str] | None = None
    refs: list[str] | None = None
    enabled: bool | None = None


@router.put("/api/skills/{skill_id}")
async def update_skill(
    skill_id: str, body: SkillUpdateIn, principal: Principal = Depends(require_role(*WRITE))
) -> dict[str, Any]:
    s = rt.skills.update(skill_id, body.model_dump(exclude_none=True))
    if s is None:
        raise HTTPException(status_code=404, detail=f"SOP {skill_id} 不存在")
    rt.ctx.audit.append(
        actor=principal.username, action="skill_update", target=skill_id, details={"version": s.version}
    )
    return s.model_dump()


@router.delete("/api/skills/{skill_id}")
async def delete_skill(skill_id: str, principal: Principal = Depends(require_role(*WRITE))) -> dict[str, Any]:
    removed = rt.skills.remove(skill_id)
    if removed:
        rt.ctx.audit.append(actor=principal.username, action="skill_delete", target=skill_id, details={})
    return {"status": "deleted" if removed else "not_found", "id": skill_id}
