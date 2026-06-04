"""L05 · LLM Gateway —— 所有 LLM 调用的统一入口（C-6）。

用法::

    from aisecops.L05_gateway.llm_gateway import LLMGateway, StubProvider

    gateway = LLMGateway([StubProvider()])
    resp = await gateway.call("有横向移动告警", scenario="L07/alert_triage")
    print(resp.content, resp.metadata.cost_cny)
"""

from .budget import BudgetExceeded, BudgetTracker
from .factory import build_gateway
from .fallback import GatewayError, complete_with_fallback
from .gateway import LLMGateway
from .metadata import MetadataRecorder
from .models import (
    CallMetadata,
    LLMRequest,
    LLMResponse,
    Message,
    Role,
    TokenUsage,
)
from .providers.base import Provider, ProviderError
from .providers.openai_compat import OpenAICompatProvider
from .providers.stub import StubProvider

__all__ = [
    "LLMGateway",
    "build_gateway",
    "BudgetTracker",
    "BudgetExceeded",
    "GatewayError",
    "complete_with_fallback",
    "MetadataRecorder",
    "Provider",
    "ProviderError",
    "StubProvider",
    "OpenAICompatProvider",
    "Message",
    "Role",
    "LLMRequest",
    "LLMResponse",
    "CallMetadata",
    "TokenUsage",
]
