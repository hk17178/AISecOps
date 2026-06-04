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

from aisecops.L05_gateway.llm_gateway import LLMGateway
from aisecops.L05_gateway.llm_gateway.factory import build_gateway
from aisecops.L07_secops_capabilities import (
    AlertTriageService,
    build_alert_triage_service,
)
from aisecops.L12_core_support.config import get_settings

app = FastAPI(title="AISECOPS · L05 测试台", version="0.1.0")

_STATIC = Path(__file__).parent / "static"
_gateway = build_gateway()
_triage_service = build_alert_triage_service()


def get_gateway() -> LLMGateway:
    """可被测试覆盖的网关依赖。"""
    return _gateway


def get_triage_service() -> AlertTriageService:
    """可被测试覆盖的分诊服务依赖。"""
    return _triage_service


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


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(_STATIC / "index.html")
