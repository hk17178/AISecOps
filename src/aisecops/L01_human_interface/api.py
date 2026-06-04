"""L01 · 人机交互 —— FastAPI 入口。

当前提供一个最小「L05 Gateway 测试台」：浏览器打开 `/` 即可输入 prompt 调用网关，
看到响应 + 元数据（成本 / token / 延迟 / provider / 是否降级）。
正式的 React 告警分诊台在 Sprint 4 做（按 docs/design 暖纸设计语言）。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel

from aisecops.L05_gateway.llm_gateway import LLMGateway
from aisecops.L05_gateway.llm_gateway.factory import build_gateway

app = FastAPI(title="AISECOPS · L05 测试台", version="0.1.0")

_STATIC = Path(__file__).parent / "static"
_gateway = build_gateway()


def get_gateway() -> LLMGateway:
    """可被测试覆盖的网关依赖。"""
    return _gateway


class CallIn(BaseModel):
    """测试台调用入参。"""

    prompt: str
    scenario: str = "L01/test"


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/llm/call")
async def llm_call(body: CallIn, gateway: LLMGateway = Depends(get_gateway)) -> dict[str, Any]:
    resp = await gateway.call(body.prompt, scenario=body.scenario)
    return {"content": resp.content, "metadata": resp.metadata.model_dump()}


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(_STATIC / "index.html")
