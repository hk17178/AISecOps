"""L01 · FastAPI 应用装配点（薄装配：建 app + 注册各域 router）。

业务逻辑不在这里：组合根见 runtime.py，各域 REST 路由见 routers/*.py（ADR-0011）。
本文件只负责把 routers 挂到一个 FastAPI 实例上，并对外导出 `app`。
为兼容测试的 dependency_overrides，从 runtime 再导出 get_* 依赖函数。
"""

from __future__ import annotations

from fastapi import FastAPI

from .routers import (
    agents,
    alerts,
    assets,
    auth,
    config,
    dispatch,
    intel,
    investigation,
    knowledge,
    prompts,
    reports,
    routing,
    soar,
    system,
    tickets,
    tools,
    triage_chat,
)
from .runtime import (
    get_corr_service,
    get_gateway,
    get_invest_service,
    get_triage_service,
)

app = FastAPI(title="AISECOPS · 安全运营台", version="0.1.0")

# 按域注册 router（顺序不影响：各 router 路径前缀互不重叠）
for _module in (
    system,
    triage_chat,
    auth,
    config,
    agents,
    tools,
    routing,
    alerts,
    investigation,
    tickets,
    soar,
    dispatch,
    reports,
    assets,
    intel,
    prompts,
    knowledge,
):
    app.include_router(_module.router)

# 测试用：dependency_overrides 需要这些依赖对象可从 api 导入（与 routers 共用同一对象）
__all__ = ["app", "get_gateway", "get_triage_service", "get_invest_service", "get_corr_service"]
