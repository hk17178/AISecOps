"""StubProvider —— 确定性假响应（C-18）。

输出只取决于输入 → 天然可复现（C-30，无需真随机种子）。
可配 price 与 fail，用于在不联网的情况下测 budget / fallback。
"""

from __future__ import annotations

from ..models import LLMRequest, TokenUsage
from .base import Provider, ProviderError


def _estimate_tokens(request: LLMRequest) -> int:
    """粗估 token：约 4 字符 1 token。"""
    chars = sum(len(m.content) for m in request.messages)
    return max(1, chars // 4)


class StubProvider(Provider):
    """假 provider：不联网、不烧 token、结果可复现。"""

    name = "stub"
    is_stub = True

    def __init__(
        self,
        model: str = "stub-1",
        price_per_1k_cny: float = 0.0,
        fail: bool = False,
        canned: str | None = None,
        name: str | None = None,
    ) -> None:
        # 只有显式传 name 才覆盖类属性（保留子类 class-attr name 的行为）
        if name is not None:
            self.name = name
        self.model = model
        self.price_per_1k_cny = price_per_1k_cny
        self._fail = fail
        # 指定固定返回内容（用于测 schema 校验 / cross-check）；None 则回显输入
        self._canned = canned

    async def complete(self, request: LLMRequest) -> tuple[str, TokenUsage]:
        if self._fail:
            raise ProviderError(f"stub[{self.model}] 强制失败（用于测降级）")
        if self._canned is not None:
            content = self._canned
        else:
            last = request.messages[-1].content if request.messages else ""
            content = f"[stub:{request.scenario}] {last[:200]}"
        usage = TokenUsage(
            prompt_tokens=_estimate_tokens(request),
            completion_tokens=max(1, len(content) // 4),
        )
        return content, usage
