"""降级链（C-34）：按顺序尝试 provider，失败转下一个，全失败抛 GatewayError。

建议把 StubProvider 放在 provider 列表末位作兜底，保证总有响应。
"""

from __future__ import annotations

from .models import LLMRequest, TokenUsage
from .providers.base import Provider, ProviderError


class GatewayError(Exception):
    """Gateway 级错误（如所有 provider 均失败）。"""


async def complete_with_fallback(
    providers: list[Provider],
    request: LLMRequest,
) -> tuple[str, TokenUsage, Provider, bool]:
    """依次尝试 providers。

    返回 (生成文本, token 用量, 命中的 provider, 是否用了降级)。
    全部失败则抛 GatewayError。
    """
    if not providers:
        raise GatewayError("没有可用 provider")
    last_error: Exception | None = None
    for index, provider in enumerate(providers):
        try:
            content, usage = await provider.complete(request)
            return content, usage, provider, index > 0
        except ProviderError as exc:
            last_error = exc
            continue
    raise GatewayError(f"所有 provider 均失败：{last_error}")
