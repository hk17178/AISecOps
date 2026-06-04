"""根据配置组装 LLMGateway。

provider 构成（§4.4 多模型档位）：
- 配了 LLM_PROFILES（多档位）→ 每档一个真 provider（共享 key/base_url，model 不同）；
- 没配档位但有 key → 单个真 provider；
- 没 key → 该档位退化成同名 StubProvider（路由仍可演示，metadata 标 stub）；
- 末位永远兜一个通用 StubProvider，保证真 provider 失败/未配也有响应（C-34）。

路由表（场景→provider 名）由调用方从 RouteStore 加载后注入；这里只给一个
DEFAULT_ROUTES 的默认 router，default 指向首个真 provider。
"""

from __future__ import annotations

import json

from aisecops.L12_core_support.config import Settings, get_settings

from .budget import BudgetTracker
from .gateway import LLMGateway
from .providers.base import Provider
from .providers.openai_compat import OpenAICompatProvider
from .providers.stub import StubProvider
from .routing import DEFAULT_ROUTES, ScenarioRouter


def _parse_profiles(raw: str) -> list[dict[str, object]]:
    """解析 LLM_PROFILES JSON；非法则当作没配（不让平台起不来）。"""
    if not raw.strip():
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    return [p for p in data if isinstance(p, dict) and p.get("name")] if isinstance(data, list) else []


def build_providers(settings: Settings) -> list[Provider]:
    """按配置构造 provider 列表（不含末位兜底 stub）。"""
    profiles = _parse_profiles(settings.llm_profiles)
    providers: list[Provider] = []
    if profiles:
        for p in profiles:
            name = str(p["name"])
            model = str(p.get("model") or settings.llm_model)
            base_url = str(p.get("base_url") or settings.llm_base_url)
            api_key = str(p.get("api_key") or settings.llm_api_key)
            price = float(p.get("price_per_1k_cny", settings.llm_price_per_1k_cny))  # type: ignore[arg-type]
            if api_key:
                providers.append(OpenAICompatProvider(base_url, api_key, model, price, name=name))
            else:
                # 没 key：用同名 stub 占位，路由依然可演示（metadata 标 stub，诚实）
                providers.append(StubProvider(model=model, price_per_1k_cny=price, name=name))
    elif settings.llm_api_key:
        providers.append(
            OpenAICompatProvider(
                settings.llm_base_url,
                settings.llm_api_key,
                settings.llm_model,
                settings.llm_price_per_1k_cny,
                name=settings.llm_model or "默认",
            )
        )
    return providers


def build_gateway(settings: Settings | None = None, router: ScenarioRouter | None = None) -> LLMGateway:
    """按 .env 配置组装网关。router 不传则用默认分档表。"""
    settings = settings or get_settings()

    providers = build_providers(settings)
    # 末位兜底：保证真 provider 失败/未配置时仍有响应
    providers.append(StubProvider())

    if router is None:
        default_name = next((p.name for p in providers if not p.is_stub), providers[-1].name)
        router = ScenarioRouter(dict(DEFAULT_ROUTES), default=default_name)

    budget = BudgetTracker(monthly_cap_cny=settings.monthly_budget_cny)
    return LLMGateway(providers, budget=budget, outbound_enabled=settings.allow_outbound, router=router)
