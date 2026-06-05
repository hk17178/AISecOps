from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from aisecops.L02_agents import Principal

from ..auth_deps import ADMIN, require_role
from ..runtime import rt

router = APIRouter()


# Agent 名册（诚实反映代码实现状态：当前仅 Orchestrator + Triage 已编码）
_AGENT_ROSTER = [
    {"name": "Orchestrator", "status": "实现", "desc": "统一调度，禁省略（C-5）"},
    {"name": "Triage", "status": "实现", "desc": "告警分诊：结构化研判 + abstain + cross-check"},
    {"name": "Investigation", "status": "实现", "desc": "事件取证：ES 日志建时间线 + LLM 攻击链"},
    {"name": "Enrichment", "status": "规划", "desc": "上下文富化"},
    {"name": "Responder", "status": "规划", "desc": "处置执行，经 HITL"},
    {"name": "Reporter", "status": "规划", "desc": "报告生成"},
    {"name": "Intel", "status": "规划", "desc": "威胁情报"},
    {"name": "Tuning", "status": "规划", "desc": "反馈调优（不训 DSLM）"},
]


def _agent_model(scenario: str) -> str:
    """该 Agent 当前路由到的 provider（场景→模型）。"""
    if not scenario or rt.gateway.router is None:
        return (rt.gateway.router.default or "") if rt.gateway.router else ""
    return rt.gateway.router.provider_name_for(scenario) or (rt.gateway.router.default or "")


@router.get("/api/agents")
async def get_agents() -> dict[str, Any]:
    """Agent 名册 + 可编辑的运行时配置（已编码的 agent 才有 config）。"""
    roster = []
    for a in _AGENT_ROSTER:
        item: dict[str, Any] = dict(a)
        cfg = rt.agent_configs.get(a["name"].lower())
        if cfg is not None:
            item["config"] = {
                **cfg.model_dump(),
                "model": _agent_model(cfg.scenario),
            }
        roster.append(item)
    providers = [p.name for p in rt.gateway.providers]
    return {"agents": roster, "providers": providers, "cross_check_modes": ["auto", "on", "off"]}


class AgentConfigIn(BaseModel):
    """编辑 Agent 配置：启停/阈值/cross-check/模型/prompt key。"""

    enabled: bool | None = None
    confidence_threshold: float | None = None
    cross_check_mode: str | None = None
    prompt_key: str | None = None
    model: str | None = None  # 改它=改该 agent 场景的模型路由
    actor: str = "未知"


@router.put("/api/agents/{name}")
async def update_agent_config(
    name: str, body: AgentConfigIn, principal: Principal = Depends(require_role(*ADMIN))
) -> dict[str, Any]:
    """改 Agent 配置（即时生效）。model 写进路由表（§4.4），其余写 agent_configs。"""
    fields = body.model_dump(exclude_none=True)
    fields.pop("actor", None)
    actor = principal.username
    model = fields.pop("model", None)
    cfg = rt.agent_configs.update(name, fields)
    if cfg is None:
        raise HTTPException(status_code=404, detail=f"Agent {name} 无可编辑配置")
    # 换模型 → 写该 agent 场景的路由（复用 §4.4，单一事实源）
    if model is not None and cfg.scenario:
        names = {p.name for p in rt.gateway.providers}
        if model not in names:
            raise HTTPException(status_code=400, detail=f"provider「{model}」不存在")
        rt.route_store.set(cfg.scenario, model)
        if rt.gateway.router is not None:
            rt.gateway.router.set_route(cfg.scenario, model)
    rt.ctx.audit.append(actor=actor, action="agent_config_update", target=name, details={**fields, "model": model})
    return {**cfg.model_dump(), "model": _agent_model(cfg.scenario)}
