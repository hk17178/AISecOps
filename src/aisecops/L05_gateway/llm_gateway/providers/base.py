"""Provider 抽象 —— 所有 LLM provider 实现此接口，Gateway 只认它。

真 provider（豆包/通义/智谱/OpenAI-compat/Claude）在 S10 实现；
本阶段先有 StubProvider 跑通全链路（C-18）。
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import LLMRequest, TokenUsage


class ProviderError(Exception):
    """provider 调用失败（网络 / 限流 / 服务错误）。触发 Gateway 降级（C-34）。"""


class Provider(ABC):
    """LLM provider 统一接口。"""

    name: str = "base"
    model: str = "unknown"
    # 每 1k token 价格（人民币），用于成本核算与预算控制
    price_per_1k_cny: float = 0.0
    # 是否「出域」（数据离开内网到外部）。出域调用受全局开关限制且需脱敏（C-32）
    outbound: bool = False

    @abstractmethod
    async def complete(self, request: LLMRequest) -> tuple[str, TokenUsage]:
        """返回 (生成文本, token 用量)。失败时抛 ProviderError。"""
        raise NotImplementedError
