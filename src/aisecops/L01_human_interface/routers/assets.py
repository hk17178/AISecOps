from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from ..runtime import rt

router = APIRouter()


@router.get("/api/assets")
async def get_assets() -> dict[str, Any]:
    return {
        "assets": [a.model_dump() for a in rt.assets.all()],
        "importance_options": ["关键", "高", "中", "低"],
        "status_options": ["正常", "观察", "已隔离", "下线"],
    }


class AssetIn(BaseModel):
    host: str
    ip: str = ""
    role: str = ""
    importance: str = "中"
    status: str = "正常"
    owner: str = ""
    note: str = ""
    actor: str = "未知"


@router.post("/api/assets")
async def create_asset(body: AssetIn) -> dict[str, Any]:
    if not body.host.strip():
        raise HTTPException(status_code=400, detail="主机名不能为空")
    a = rt.assets.create(
        body.host.strip(),
        body.ip.strip(),
        body.role.strip(),
        body.importance,
        body.status,
        body.owner.strip(),
        body.note.strip(),
    )
    rt.ctx.audit.append(
        actor=body.actor, action="asset_create", target=a.id, details={"host": a.host, "importance": a.importance}
    )
    return a.model_dump()


class AssetUpdateIn(BaseModel):
    model_config = ConfigDict(extra="allow")

    actor: str = "未知"


@router.put("/api/assets/{asset_id}")
async def update_asset(asset_id: str, body: AssetUpdateIn) -> dict[str, Any]:
    fields = body.model_dump()
    actor = str(fields.pop("actor", "未知"))
    a = rt.assets.update(asset_id, fields)
    if a is None:
        raise HTTPException(status_code=404, detail=f"资产 {asset_id} 不存在")
    rt.ctx.audit.append(actor=actor, action="asset_update", target=asset_id, details={"fields": list(fields.keys())})
    return a.model_dump()


@router.delete("/api/assets/{asset_id}")
async def delete_asset(asset_id: str, actor: str = "未知") -> dict[str, Any]:
    removed = rt.assets.remove(asset_id)
    if removed:
        rt.ctx.audit.append(actor=actor, action="asset_delete", target=asset_id, details={})
    return {"status": "deleted" if removed else "not_found", "id": asset_id}
