"""降级链（C-34）+ 出域门控（C-32）。

依次尝试 provider，失败转下一个：
- 出域 provider：仅当全局出域开关开启才尝试，且调用前脱敏；
- 全部不可用 / 失败 → GatewayError。

建议把本地 StubProvider 放末位作兜底，保证总有响应。
"""

from __future__ import annotations

from collections.abc import Callable

from .models import LLMRequest, TokenUsage
from .providers.base import Provider, ProviderError


class GatewayError(Exception):
    """Gateway 级错误（如所有可用 provider 均失败）。"""


async def complete_with_fallback(
    providers: list[Provider],
    request: LLMRequest,
    *,
    outbound_enabled: bool,
    desensitizer: Callable[[LLMRequest], LLMRequest],
) -> tuple[str, TokenUsage, Provider, bool, bool]:
    """返回 (生成文本, token 用量, 命中的 provider, 是否用了降级, 是否脱敏)。"""
    if not providers:
        raise GatewayError("没有可用 provider")
    last_error: Exception | None = None
    attempted = 0
    for provider in providers:
        if provider.outbound and not outbound_enabled:
            continue  # 出域开关关闭，跳过出域 provider（C-32）
        request_to_send = request
        desensitized = False
        if provider.outbound:
            request_to_send = desensitizer(request)
            desensitized = True
        try:
            content, usage = await provider.complete(request_to_send)
            return content, usage, provider, attempted > 0, desensitized
        except ProviderError as exc:
            last_error = exc
            attempted += 1
            continue
    if last_error is None:
        raise GatewayError("没有可用 provider（出域开关关闭，且无可用本地 provider）")
    raise GatewayError(f"所有 provider 均失败：{last_error}")
