"""出域脱敏（C-32）：数据进外部 LLM 前打码敏感信息。

最小可用版：遮蔽 IPv4 / 邮箱 / MAC / 长数字串。按需在此扩展规则。
注意：脱敏是「降低泄露面」，不是「绝对安全」——真高敏数据应优先走本地 LLM。
"""

from __future__ import annotations

import re

from .models import LLMRequest, Message

_IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_MAC = re.compile(r"\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b")
_LONG_DIGITS = re.compile(r"\b\d{11,}\b")  # 手机号/长ID等


def desensitize(text: str) -> str:
    """对单段文本脱敏。"""
    text = _EMAIL.sub("<EMAIL>", text)
    text = _MAC.sub("<MAC>", text)
    text = _IPV4.sub("<IP>", text)
    text = _LONG_DIGITS.sub("<NUM>", text)
    return text


def desensitize_request(request: LLMRequest) -> LLMRequest:
    """返回一个所有消息内容已脱敏的新请求（不改原对象）。"""
    masked = [Message(role=m.role, content=desensitize(m.content)) for m in request.messages]
    return request.model_copy(update={"messages": masked})
