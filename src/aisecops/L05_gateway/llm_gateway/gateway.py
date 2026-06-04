"""L05 · LLM Gateway —— 所有 LLM 调用必经此（C-6）。

本阶段统一：预算闸门（自用关键）→ 路由 + 降级（C-34）→ 元数据（C-33）→ 可复现（C-30）。
后续步骤补：出域脱敏（C-32）/ 出域开关 / response_model schema 校验（C-21）/
双模型 cross-check（C-27）/ 真 provider。
"""

from __future__ import annotations

import time

from .budget import BudgetTracker
from .fallback import complete_with_fallback
from .metadata import MetadataRecorder
from .models import CallMetadata, LLMRequest, LLMResponse, Message, Role
from .providers.base import Provider


class LLMGateway:
    """LLM 统一入口。业务一行 `await gateway.call(...)` 即可。"""

    def __init__(
        self,
        providers: list[Provider],
        budget: BudgetTracker | None = None,
        recorder: MetadataRecorder | None = None,
    ) -> None:
        if not providers:
            raise ValueError("至少需要一个 provider")
        self.providers = providers
        self.budget = budget
        self.recorder = recorder or MetadataRecorder()

    async def call(
        self,
        prompt: str | list[Message],
        *,
        scenario: str,
        temperature: float = 0.0,
        seed: int | None = None,
        max_tokens: int = 4096,
        budget_tag: str = "default",
        allow_outbound: bool = False,
    ) -> LLMResponse:
        """统一调用入口。

        参数:
            prompt: 字符串（当作单条 user 消息）或完整 Message 列表。
            scenario: 必填，调用场景，如 "L07/alert_triage"。
            temperature/seed: 默认 0 + 可选种子，服务可复现（C-30）。
            budget_tag: 成本分摊标签。
            allow_outbound: 出域开关（C-32，默认关；脱敏在后续步骤补）。
        """
        messages = [Message(role=Role.user, content=prompt)] if isinstance(prompt, str) else prompt
        request = LLMRequest(
            messages=messages,
            scenario=scenario,
            temperature=temperature,
            seed=seed,
            max_tokens=max_tokens,
            budget_tag=budget_tag,
            allow_outbound=allow_outbound,
        )

        # 预算闸门（超限直接抛 BudgetExceeded，不发起调用）
        if self.budget is not None:
            self.budget.check()

        # 路由 + 降级（C-34）
        start = time.perf_counter()
        content, usage, provider, fallback_used = await complete_with_fallback(self.providers, request)
        latency_ms = (time.perf_counter() - start) * 1000

        total_tokens = usage.prompt_tokens + usage.completion_tokens
        cost_cny = total_tokens / 1000 * provider.price_per_1k_cny

        if self.budget is not None:
            self.budget.record(cost_cny)

        metadata = CallMetadata(
            scenario=scenario,
            provider=provider.name,
            model=provider.model,
            budget_tag=budget_tag,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            total_tokens=total_tokens,
            cost_cny=cost_cny,
            latency_ms=latency_ms,
            fallback_used=fallback_used,
            stub=(provider.name == "stub"),
        )
        self.recorder.record(metadata)
        return LLMResponse(content=content, metadata=metadata)
