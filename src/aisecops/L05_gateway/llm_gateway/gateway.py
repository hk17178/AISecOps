"""L05 · LLM Gateway —— 所有 LLM 调用必经此（C-6）。

统一：预算闸门（自用关键）→ 出域开关 + 脱敏（C-32）→ 路由 + 降级（C-34）
→ schema 校验（C-21）→ 双模型 cross-check（C-27）→ 元数据（C-33）→ 可复现（C-30）。
"""

from __future__ import annotations

import json
import re
import time
from typing import Any, get_origin

from pydantic import BaseModel, ValidationError

from .budget import BudgetTracker
from .desensitize import desensitize_request
from .fallback import complete_with_fallback
from .metadata import MetadataRecorder
from .models import CallMetadata, LLMRequest, LLMResponse, Message, Role, TokenUsage
from .providers.base import Provider

_JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)


class SchemaValidationError(Exception):
    """LLM 输出不符合 response_model（C-21）。"""


def _extract_json(content: str) -> Any:
    """从 LLM 文本中提取 JSON（容忍 ```json 包裹或前后多余文字）。"""
    text = content.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = _JSON_BLOCK.search(content)
        if match:
            return json.loads(match.group(0))
        raise


def _normalize(text: str) -> str:
    return " ".join(text.split()).strip().lower()


def _placeholder(annotation: Any) -> Any:
    """按类型给一个零值占位（stub 离线填充用）。"""
    origin = get_origin(annotation)
    if annotation is str:
        return ""
    if annotation is int:
        return 0
    if annotation is float:
        return 0.0
    if annotation is bool:
        return False
    if origin in (list, set, tuple):
        return []
    if origin is dict:
        return {}
    return None


def _stub_fill(model: type[BaseModel]) -> BaseModel:
    """构造一个 schema 合法的占位实例（必填字段填零值）。"""
    values = {name: _placeholder(field.annotation) for name, field in model.model_fields.items() if field.is_required()}
    return model.model_validate(values)


class LLMGateway:
    """LLM 统一入口。业务一行 `await gateway.call(...)` 即可。"""

    def __init__(
        self,
        providers: list[Provider],
        budget: BudgetTracker | None = None,
        recorder: MetadataRecorder | None = None,
        outbound_enabled: bool = False,
    ) -> None:
        if not providers:
            raise ValueError("至少需要一个 provider")
        self.providers = providers
        self.budget = budget
        self.recorder = recorder or MetadataRecorder()
        # 全局出域开关（C-32，默认关）。关闭时出域 provider 不会被使用
        self.outbound_enabled = outbound_enabled

    def _usable(self) -> list[Provider]:
        """当前可用 provider（出域 provider 仅在开关开启时算）。"""
        return [p for p in self.providers if (not p.outbound) or self.outbound_enabled]

    async def _invoke(self, provider: Provider, request: LLMRequest) -> tuple[str, TokenUsage, bool]:
        """单次调用一个 provider；出域则先脱敏（C-32）。返回 (文本, 用量, 是否脱敏)。"""
        request_to_send = request
        desensitized = False
        if provider.outbound:
            request_to_send = desensitize_request(request)
            desensitized = True
        content, usage = await provider.complete(request_to_send)
        return content, usage, desensitized

    async def call(
        self,
        prompt: str | list[Message],
        *,
        scenario: str,
        temperature: float = 0.0,
        seed: int | None = None,
        max_tokens: int = 4096,
        budget_tag: str = "default",
        response_model: type[BaseModel] | None = None,
        cross_check: bool = False,
    ) -> LLMResponse:
        """统一调用入口。

        参数:
            prompt: 字符串（单条 user 消息）或完整 Message 列表。
            scenario: 必填，调用场景，如 "L07/alert_triage"。
            temperature/seed: 默认 0 + 可选种子，服务可复现（C-30）。
            response_model: 传入则校验 LLM 输出 JSON（C-21），不符抛 SchemaValidationError。
            cross_check: 高风险动作置 True，双 provider 比对（C-27），结果记进 metadata。
        """
        messages = [Message(role=Role.user, content=prompt)] if isinstance(prompt, str) else prompt
        request = LLMRequest(
            messages=messages,
            scenario=scenario,
            temperature=temperature,
            seed=seed,
            max_tokens=max_tokens,
            budget_tag=budget_tag,
        )

        # 预算闸门（超限直接抛 BudgetExceeded，不发起调用）
        if self.budget is not None:
            self.budget.check()

        start = time.perf_counter()
        cross_checked = False
        cross_agreed: bool | None = None

        if cross_check and len(self._usable()) >= 2:
            # 双模型 cross-check（C-27）
            usable = self._usable()
            content, usage, desensitized = await self._invoke(usable[0], request)
            content_b, _usage_b, _dz_b = await self._invoke(usable[1], request)
            provider = usable[0]
            fallback_used = False
            cross_checked = True
            cross_agreed = _normalize(content) == _normalize(content_b)
        else:
            # 普通路由 + 降级（C-34）。cross_check 但可用 provider 不足 2 个时也走这里
            content, usage, provider, fallback_used, desensitized = await complete_with_fallback(
                self.providers,
                request,
                outbound_enabled=self.outbound_enabled,
                desensitizer=desensitize_request,
            )
            if cross_check:
                cross_checked = True  # 想做但 provider 不足，agreed 保持 None

        latency_ms = (time.perf_counter() - start) * 1000
        total_tokens = usage.prompt_tokens + usage.completion_tokens
        cost_cny = total_tokens / 1000 * provider.price_per_1k_cny
        if self.budget is not None:
            self.budget.record(cost_cny)

        # schema 校验（C-21）
        parsed: Any = None
        if response_model is not None:
            try:
                parsed = response_model.model_validate(_extract_json(content))
            except (json.JSONDecodeError, ValidationError) as exc:
                if provider.name == "stub":
                    # 离线 stub 产不出真实结构化研判 → 给 schema 合法占位
                    # （必填字段填零值，confidence=0 自然让上层 abstain → 待研判）
                    parsed = _stub_fill(response_model)
                else:
                    raise SchemaValidationError(f"{scenario} 输出不符合 {response_model.__name__}：{exc}") from exc

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
            outbound=provider.outbound,
            desensitized=desensitized,
            cross_checked=cross_checked,
            cross_check_agreed=cross_agreed,
        )
        self.recorder.record(metadata)
        return LLMResponse(content=content, metadata=metadata, parsed=parsed)
