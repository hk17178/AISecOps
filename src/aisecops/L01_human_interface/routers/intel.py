from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..runtime import rt

router = APIRouter()


@router.get("/api/iocs")
async def get_iocs() -> dict[str, Any]:
    return {"iocs": [i.model_dump() for i in rt.iocs.all()], "type_options": ["域名", "IP", "哈希", "URL"]}


class IocIn(BaseModel):
    value: str
    type: str = "IP"
    severity: str = "高"
    note: str = ""
    actor: str = "未知"


@router.post("/api/iocs")
async def create_ioc(body: IocIn) -> dict[str, Any]:
    if not body.value.strip():
        raise HTTPException(status_code=400, detail="IoC 值不能为空")
    if body.type not in ("域名", "IP", "哈希", "URL"):
        raise HTTPException(status_code=400, detail="type 须为 域名/IP/哈希/URL")
    i = rt.iocs.create(body.value.strip(), body.type, body.severity, body.note.strip())
    rt.ctx.audit.append(actor=body.actor, action="ioc_create", target=i.id, details={"value": i.value, "type": i.type})
    return i.model_dump()


@router.delete("/api/iocs/{ioc_id}")
async def delete_ioc(ioc_id: str, actor: str = "未知") -> dict[str, Any]:
    removed = rt.iocs.remove(ioc_id)
    if removed:
        rt.ctx.audit.append(actor=actor, action="ioc_delete", target=ioc_id, details={})
    return {"status": "deleted" if removed else "not_found", "id": ioc_id}
