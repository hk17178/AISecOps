"""L01 · 人机交互 —— FastAPI 入口。

当前提供一个最小「L05 Gateway 测试台」：浏览器打开 `/` 即可输入 prompt 调用网关，
看到响应 + 元数据（成本 / token / 延迟 / provider / 是否降级）。
正式的 React 告警分诊台在 Sprint 4 做（按 docs/design 暖纸设计语言）。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict

from aisecops.L02_agents import (
    AgentContext,
    InMemoryTicketStore,
    TicketError,
    seed_demo_tickets,
)
from aisecops.L05_gateway.llm_gateway import LLMGateway
from aisecops.L05_gateway.llm_gateway.factory import build_gateway
from aisecops.L06_mcp_servers import build_tool_registry
from aisecops.L07_secops_capabilities import (
    AlertTriageService,
    InvestigationService,
    build_alert_triage_service,
    build_investigation_service,
)
from aisecops.L09_data_platform.alert_store import (
    InMemoryAlertStore,
    alert_stats,
    seed_demo_alerts,
)
from aisecops.L10_data_collection.ingest import normalize_alert
from aisecops.L12_core_support.config import get_settings

app = FastAPI(title="AISECOPS · L05 测试台", version="0.1.0")

_STATIC = Path(__file__).parent / "static"
# 共享一个网关 + 工具注册表 + 上下文：分诊与成本统计读同一份数据
_gateway = build_gateway()
_registry = build_tool_registry()
_ctx = AgentContext(llm=_gateway, tools=_registry)

# HITL 工单库（真 store + 演示种子）；真威胁分诊会自动建单
_tickets = InMemoryTicketStore()
seed_demo_tickets(_tickets)
_triage_service = build_alert_triage_service(_ctx, _tickets)
_invest_service = build_investigation_service(_ctx)

# 告警库（真 store + 演示种子；接 SIEM webhook 后真数据流入）
_alerts = InMemoryAlertStore()
seed_demo_alerts(_alerts)


def get_gateway() -> LLMGateway:
    """可被测试覆盖的网关依赖。"""
    return _gateway


def get_triage_service() -> AlertTriageService:
    """可被测试覆盖的分诊服务依赖。"""
    return _triage_service


def get_invest_service() -> InvestigationService:
    """可被测试覆盖的调查服务依赖。"""
    return _invest_service


class CallIn(BaseModel):
    """测试台调用入参。"""

    prompt: str
    scenario: str = "L01/test"


class AlertIn(BaseModel):
    """告警入参（允许额外字段，整个对象作为告警 payload）。"""

    model_config = ConfigDict(extra="allow")

    host: str = ""
    high_risk: bool = False


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/llm/call")
async def llm_call(body: CallIn, gateway: LLMGateway = Depends(get_gateway)) -> dict[str, Any]:
    resp = await gateway.call(body.prompt, scenario=body.scenario)
    return {"content": resp.content, "metadata": resp.metadata.model_dump()}


@app.post("/api/triage")
async def triage(body: AlertIn, svc: AlertTriageService = Depends(get_triage_service)) -> dict[str, Any]:
    """端到端告警分诊：Orchestrator → Triage（ES 富化 + LLM 研判）→ 结果。"""
    alert = body.model_dump()
    high_risk = bool(alert.pop("high_risk", False))
    result = await svc.triage(alert, high_risk=high_risk)
    return result.model_dump()


class LoginIn(BaseModel):
    username: str
    password: str


# 占位认证（真 RBAC 在 L02 平台核心做）。默认口令 aisecops。
_ROLES = {"admin": "管理员", "analyst": "分析师"}


@app.post("/api/login")
async def login(body: LoginIn) -> dict[str, str]:
    if not body.username or body.password != "aisecops":
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    role = _ROLES.get(body.username, "普通查看")
    return {"username": body.username, "role": role}


# 配置覆盖（仅内存暂存；持久化到 DB + 密钥加密是 P-18 待做）
_config_overrides: dict[str, Any] = {}


class ConfigIn(BaseModel):
    """系统设置入参（允许任意配置字段）。"""

    model_config = ConfigDict(extra="allow")


@app.get("/api/config")
async def get_config() -> dict[str, Any]:
    s = get_settings()
    base: dict[str, Any] = {
        "llm_base_url": s.llm_base_url,
        "llm_model": s.llm_model,
        "llm_api_key_set": bool(s.llm_api_key),
        "monthly_budget_cny": s.monthly_budget_cny,
        "allow_outbound": s.allow_outbound,
        "es_hosts": s.es_hosts,
        "wechat_webhook_set": bool(s.wechat_webhook),
    }
    base.update(_config_overrides)
    return base


@app.put("/api/config")
async def put_config(body: ConfigIn) -> dict[str, str]:
    _config_overrides.update(body.model_dump())
    return {"status": "saved", "note": "已暂存（内存）；DB 持久化与密钥加密为 P-18 待做"}


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


@app.get("/api/agents")
async def get_agents() -> dict[str, Any]:
    return {"agents": _AGENT_ROSTER}


@app.get("/api/tools")
async def get_tools() -> dict[str, Any]:
    tools: list[dict[str, Any]] = []
    ls = _registry.log_source
    if ls is not None:
        is_real = ls.name == "elasticsearch"
        tools.append(
            {
                "name": "Elasticsearch",
                "category": "data_sources",
                "form": "薄适配器",
                "status": "已接入" if is_real else "Stub（未配 ES 凭证，离线）",
            }
        )
    return {"tools": tools, "note": "其余适配器（SIEM/EDR/通知）待接入"}


@app.get("/api/cost")
async def get_cost() -> dict[str, Any]:
    history = _gateway.recorder.history
    budget = _gateway.budget
    by_provider: dict[str, int] = {}
    by_scenario: dict[str, int] = {}
    for m in history:
        by_provider[m.provider] = by_provider.get(m.provider, 0) + 1
        by_scenario[m.scenario] = by_scenario.get(m.scenario, 0) + 1
    return {
        "monthly_cap_cny": budget.monthly_cap_cny if budget else 0.0,
        "spent_cny": round(budget.spent(), 4) if budget else 0.0,
        "remaining_cny": round(budget.remaining(), 4) if budget else 0.0,
        "total_calls": len(history),
        "total_tokens": sum(m.total_tokens for m in history),
        "by_provider": by_provider,
        "by_scenario": by_scenario,
        "providers": [{"name": p.name, "model": p.model, "outbound": p.outbound} for p in _gateway.providers],
    }


class IngestIn(BaseModel):
    """告警入库入参（允许任意原始字段）。"""

    model_config = ConfigDict(extra="allow")


@app.post("/api/ingest/alert")
async def ingest_alert(body: IngestIn) -> dict[str, Any]:
    """L10 入库：归一化外部告警 → 存入 L09 告警库。"""
    alert = _alerts.add(normalize_alert(body.model_dump()))
    return alert.model_dump()


@app.get("/api/alerts")
async def get_alerts() -> dict[str, Any]:
    return {"alerts": [a.model_dump() for a in _alerts.recent(50)]}


@app.get("/api/dashboard")
async def get_dashboard() -> dict[str, Any]:
    stats = alert_stats(_alerts)
    budget = _gateway.budget
    stats["spent_cny"] = round(budget.spent(), 4) if budget else 0.0
    stats["monthly_cap_cny"] = budget.monthly_cap_cny if budget else 0.0
    stats["triage_calls"] = len(_gateway.recorder.history)
    stats["hitl_pending"] = _tickets.pending_count()
    return stats


class InvestigateIn(BaseModel):
    host: str = ""
    question: str = ""


@app.post("/api/investigate")
async def investigate(body: InvestigateIn, svc: InvestigationService = Depends(get_invest_service)) -> dict[str, Any]:
    """事件调查：查 ES 日志建时间线 + LLM 推断攻击链。"""
    result = await svc.investigate(body.host, body.question)
    return result.model_dump()


@app.get("/api/tickets")
async def get_tickets() -> dict[str, Any]:
    return {"tickets": [t.model_dump() for t in _tickets.all()]}


@app.post("/api/tickets/{ticket_id}/approve")
async def approve_ticket(ticket_id: str) -> dict[str, Any]:
    try:
        return _tickets.decide(ticket_id, "已批准").model_dump()
    except TicketError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/tickets/{ticket_id}/reject")
async def reject_ticket(ticket_id: str) -> dict[str, Any]:
    try:
        return _tickets.decide(ticket_id, "已驳回").model_dump()
    except TicketError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(_STATIC / "index.html")
