"""L05 · LLM Gateway 数据契约。

所有经 Gateway 的请求 / 响应 / 元数据都在此定义（Pydantic，C-21 的地基）。
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Role(str, Enum):
    """消息角色。"""

    system = "system"
    user = "user"
    assistant = "assistant"


class Message(BaseModel):
    """一条对话消息。"""

    role: Role
    content: str


class LLMRequest(BaseModel):
    """送往 provider 的统一请求。"""

    messages: list[Message]
    scenario: str = Field(..., description="调用场景，必填，如 L07/alert_triage")
    temperature: float = 0.0
    seed: int | None = None
    max_tokens: int = 4096
    budget_tag: str = "default"
    allow_outbound: bool = False


class TokenUsage(BaseModel):
    """token 用量。"""

    prompt_tokens: int = 0
    completion_tokens: int = 0


class CallMetadata(BaseModel):
    """每次调用的元数据（C-33：LLM 调用必带 metadata）。"""

    scenario: str
    provider: str
    model: str
    budget_tag: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_cny: float = 0.0
    latency_ms: float = 0.0
    fallback_used: bool = False
    stub: bool = False
    # C-32：是否出域 + 是否已脱敏
    outbound: bool = False
    desensitized: bool = False
    # C-27：是否做了双模型 cross-check，以及两模型是否一致（None=未做/无法做）
    cross_checked: bool = False
    cross_check_agreed: bool | None = None


class LLMResponse(BaseModel):
    """Gateway 统一响应。"""

    content: str
    metadata: CallMetadata
    # C-21：若传了 response_model，这里是校验通过的对象（否则 None）
    parsed: Any = None
