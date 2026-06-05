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
from .fallback import GatewayError
from .metadata import MetadataRecorder
from .models import CallMetadata, LLMRequest, LLMResponse, Message, Role, TokenUsage
from .providers.base import Provider
from .routing import ScenarioRouter

_JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)

# C-30 可复现：分诊/调查/关联等确定性场景(temperature=0)缺省固定 seed，
# 保证同输入同输出、HITL 可复盘。报告类温度>0 的场景不强制。
DEFAULT_SEED = 42


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
        router: ScenarioRouter | None = None,
    ) -> None:
        if not providers:
            raise ValueError("至少需要一个 provider")
        self.providers = providers
        self.budget = budget
        self.recorder = recorder or MetadataRecorder()
        # 全局出域开关（C-32，默认关）。关闭时出域 provider 不会被使用
        self.outbound_enabled = outbound_enabled
        # 场景→模型路由（§4.4）。None 则所有场景用同一条 provider 顺序
        self.router = router

    def _ordered(self, scenario: str) -> list[Provider]:
        """按场景路由排序 provider（命中的优先，其余作降级）。"""
        if self.router is None:
            return self.providers
        return self.router.order(scenario, self.providers)

    def _usable_for(self, scenario: str) -> list[Provider]:
        """该场景可用 provider（按路由排序 + 出域开关过滤）。"""
        return [p for p in self._ordered(scenario) if (not p.outbound) or self.outbound_enabled]

    async def _invoke(self, provider: Provider, request: LLMRequest) -> tuple[str, TokenUsage, bool]:
        """单次调用一个 provider；出域则先脱敏（C-32）。返回 (文本, 用量, 是否脱敏)。"""
        request_to_send = request
        desensitized = False
        if provider.outbound:
            request_to_send = desensitize_request(request)
            desensitized = True
        content, usage = await provider.complete(request_to_send)
        return content, usage, desensitized

    def _agree(self, response_model: type[BaseModel] | None, content_a: str, content_b: str) -> bool:
        """双模型是否一致（C-27）。

        有 response_model 时按"关键决策字段"比对（cross_check_fields，如分诊的 verdict、
        关联的 is_incident+severity），而非逐字符比全文——否则 evidence/措辞差异会让结构化
        研判几乎必然判不一致，cross-check 退化成"高风险一律 abstain"。
        """
        if response_model is not None:
            try:
                a = response_model.model_validate(_extract_json(content_a))
                b = response_model.model_validate(_extract_json(content_b))
            except (json.JSONDecodeError, ValidationError):
                return _normalize(content_a) == _normalize(content_b)
            fields = getattr(response_model, "cross_check_fields", ())
            if fields:
                return all(getattr(a, f, None) == getattr(b, f, None) for f in fields)
            return a.model_dump() == b.model_dump()
        return _normalize(content_a) == _normalize(content_b)

    async def _complete_validated(
        self, providers: list[Provider], request: LLMRequest, response_model: type[BaseModel] | None
    ) -> tuple[str, TokenUsage, Provider, bool, bool, Any]:
        """带 schema 降级的 provider 链（C-34 + C-21/C-19）。

        非 stub provider 输出必须能解析成 response_model，否则视为该 provider 失败、转下一个；
        遇 stub provider 用零值占位（abstain）；全部走完仍无合规输出时：仅因 schema 失败 →
        SchemaValidationError，含 provider 调用失败 → GatewayError。返回末位多一个 parsed。
        """
        last_provider_error: Exception | None = None
        last_schema_error: Exception | None = None
        attempted = 0
        for provider in providers:
            if provider.outbound and not self.outbound_enabled:
                continue  # 出域开关关闭，跳过（C-32）
            req = request
            desensitized = False
            if provider.outbound:
                req = desensitize_request(request)
                desensitized = True
            try:
                content, usage = await provider.complete(req)
            except (KeyboardInterrupt,):
                raise
            except Exception as exc:  # 网络/限流/畸形响应 → 降级（C-34）
                last_provider_error = exc
                attempted += 1
                continue
            if response_model is None:
                return content, usage, provider, attempted > 0, desensitized, None
            try:
                parsed: Any = response_model.model_validate(_extract_json(content))
                return content, usage, provider, attempted > 0, desensitized, parsed
            except (json.JSONDecodeError, ValidationError) as exc:
                if provider.is_stub:
                    # 离线 stub 产不出真实结构化研判 → 零值占位（confidence=0 → 上层 abstain）
                    return content, usage, provider, attempted > 0, desensitized, _stub_fill(response_model)
                last_schema_error = exc
                attempted += 1
                continue
        # 全链走完仍无合规输出
        if last_schema_error is not None and last_provider_error is None:
            raise SchemaValidationError(
                f"{request.scenario} 所有非 stub provider 输出均不符合 {response_model.__name__ if response_model else ''}"
            )
        raise GatewayError(f"所有 provider 均失败：{last_provider_error or last_schema_error}")

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
        agent_name: str = "",
        trace_id: str = "",
    ) -> LLMResponse:
        """统一调用入口。

        参数:
            prompt: 字符串（单条 user 消息）或完整 Message 列表。
            scenario: 必填，调用场景，如 "L07/alert_triage"。
            temperature/seed: 默认 0；temp=0 且未显式给 seed 时注入固定 DEFAULT_SEED，
                让分诊/调查/关联可复现（C-30）。
            response_model: 传入则校验 LLM 输出 JSON（C-21）；非 stub 不符则降级，仍不符抛
                SchemaValidationError（无 stub 兜底时）。
            cross_check: 高风险动作置 True，双 provider 比对关键决策字段（C-27），两次成本均计入。
            agent_name/trace_id: 归因与端到端追踪（C-33）。
        """
        # C-30：确定性场景缺省固定 seed
        if seed is None and temperature == 0.0:
            seed = DEFAULT_SEED

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
        cross_check_cost = 0.0
        b_tokens = 0

        usable = self._usable_for(scenario)
        if cross_check and len(usable) >= 2:
            # 双模型 cross-check（C-27）：取该场景排序后的前两个，两次都跑、都计成本
            content, usage, desensitized = await self._invoke(usable[0], request)
            content_b, usage_b, _dz_b = await self._invoke(usable[1], request)
            provider = usable[0]
            fallback_used = False
            cross_checked = True
            cross_agreed = self._agree(response_model, content, content_b)
            b_tokens = usage_b.prompt_tokens + usage_b.completion_tokens
            cross_check_cost = b_tokens / 1000 * usable[1].price_per_1k_cny
            parsed: Any = None
            if response_model is not None:
                try:
                    parsed = response_model.model_validate(_extract_json(content))
                except (json.JSONDecodeError, ValidationError):
                    parsed = _stub_fill(response_model) if provider.is_stub else None
                    if parsed is None:
                        raise SchemaValidationError(
                            f"{scenario} cross-check 主模型输出不符合 {response_model.__name__}"
                        ) from None
        else:
            # 普通路由 + 降级（C-34）+ schema 降级（C-21/C-19）
            content, usage, provider, fallback_used, desensitized, parsed = await self._complete_validated(
                self._ordered(scenario), request, response_model
            )
            if cross_check:
                cross_checked = True  # 想做但 provider 不足，agreed 保持 None

        latency_ms = (time.perf_counter() - start) * 1000
        a_tokens = usage.prompt_tokens + usage.completion_tokens
        # 成本 = 主模型 + （cross-check 时）第二模型，按各自单价折算（C-33：不再系统性低估）
        cost_cny = a_tokens / 1000 * provider.price_per_1k_cny + cross_check_cost
        if self.budget is not None:
            self.budget.record(cost_cny)

        metadata = CallMetadata(
            scenario=scenario,
            provider=provider.name,
            model=provider.model,
            budget_tag=budget_tag,
            temperature=temperature,
            seed=seed,
            agent_name=agent_name,
            trace_id=trace_id,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            total_tokens=a_tokens + b_tokens,
            cost_cny=cost_cny,
            latency_ms=latency_ms,
            fallback_used=fallback_used,
            stub=provider.is_stub,
            outbound=provider.outbound,
            desensitized=desensitized,
            cross_checked=cross_checked,
            cross_check_agreed=cross_agreed,
            cross_check_cost_cny=cross_check_cost,
        )
        self.recorder.record(metadata)
        return LLMResponse(content=content, metadata=metadata, parsed=parsed)
