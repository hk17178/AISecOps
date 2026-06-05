"""L01 · config router —— 系统设置读写（有效配置 / 改配置存 DB 热更）。"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from aisecops.L06_mcp_servers import build_notifier
from aisecops.L12_core_support.config import get_settings
from aisecops.L12_core_support.config_store import EDITABLE_KEYS, coerce

from ..runtime import apply_overrides, rt

router = APIRouter()


class ConfigIn(BaseModel):
    """系统设置入参（允许任意配置字段）。"""

    model_config = ConfigDict(extra="allow")

    actor: str = "未知"


@router.get("/api/config")
async def get_config() -> dict[str, Any]:
    """有效配置（DB 覆盖 .env）。敏感键只回"是否已配置"，不回明文。"""
    s = rt.settings
    return {
        "llm_base_url": s.llm_base_url,
        "llm_model": s.llm_model,
        "llm_api_key_set": bool(s.llm_api_key),
        "monthly_budget_cny": s.monthly_budget_cny,
        "allow_outbound": s.allow_outbound,
        "es_hosts": s.es_hosts,
        "wechat_webhook_set": bool(s.wechat_webhook),
    }


@router.put("/api/config")
async def put_config(body: ConfigIn) -> dict[str, Any]:
    """改配置 → 存 DB（敏感键加密）+ 即时应用可热更项（预算/出域）。"""
    data = body.model_dump(exclude_unset=True)
    actor = str(data.pop("actor", "未知"))
    applied = []
    for key, raw in data.items():
        if key not in EDITABLE_KEYS:
            continue
        rt.config_store.set(key, coerce(key, raw))
        applied.append(key)
    # 重算有效配置并热更可即时生效的项
    rt.settings = apply_overrides(get_settings(), rt.config_store.all_decrypted())
    if rt.gateway.budget is not None:
        rt.gateway.budget.monthly_cap_cny = rt.settings.monthly_budget_cny
    rt.gateway.outbound_enabled = rt.settings.allow_outbound
    rt.notifier = build_notifier(rt.settings.allow_outbound)
    rt.ctx.audit.append(actor=actor, action="config_update", target="system", details={"keys": applied})
    note = "已保存到 DB（敏感键已加密）。预算/出域即时生效；模型 key/base/model 重启后生效。"
    return {"status": "saved", "applied": applied, "note": note}
