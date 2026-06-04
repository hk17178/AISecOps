"""根据配置组装 LLMGateway。

有 API Key → 用真 provider（OpenAI 兼容），并把 StubProvider 放末位兜底（C-34）；
没 Key → 只用 stub（不联网，纯本地测试）。
"""

from __future__ import annotations

from aisecops.L12_core_support.config import Settings, get_settings

from .budget import BudgetTracker
from .gateway import LLMGateway
from .providers.base import Provider
from .providers.openai_compat import OpenAICompatProvider
from .providers.stub import StubProvider


def build_gateway(settings: Settings | None = None) -> LLMGateway:
    """按 .env 配置组装网关。"""
    settings = settings or get_settings()

    providers: list[Provider] = []
    if settings.llm_api_key:
        providers.append(
            OpenAICompatProvider(
                base_url=settings.llm_base_url,
                api_key=settings.llm_api_key,
                model=settings.llm_model,
                price_per_1k_cny=settings.llm_price_per_1k_cny,
            )
        )
    # 末位兜底：保证真 provider 失败/未配置时仍有响应
    providers.append(StubProvider())

    budget = BudgetTracker(monthly_cap_cny=settings.monthly_budget_cny)
    return LLMGateway(providers, budget=budget, outbound_enabled=settings.allow_outbound)
