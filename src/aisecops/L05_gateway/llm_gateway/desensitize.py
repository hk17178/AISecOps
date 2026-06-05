"""出域脱敏（C-32）：数据进外部 LLM 前打码敏感信息。

覆盖：URL / 邮箱 / Windows SID / 文件哈希(MD5/SHA1/SHA256) / MAC / IPv4 / 域名主机名 / 长数字串。
这些都是安全场景里会带客户专有信息的字段（IoC、内网主机、样本哈希等）。
注意：脱敏是「降低泄露面」，不是「绝对安全」——真高敏数据应优先走本地 LLM。
域名规则较宽（可能把 a.com / file.txt 之类也打码），对"出域到外部 LLM"宁可多打码。
"""

from __future__ import annotations

import re

from .models import LLMRequest, Message

# 顺序敏感：先 URL/邮箱，再域名，避免域名规则吃掉 URL/邮箱的一部分
_URL = re.compile(r"\bhttps?://[^\s<>\"']+", re.IGNORECASE)
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_SID = re.compile(r"\bS-1-(?:\d+-)+\d+\b")  # Windows 安全标识符
_HASH = re.compile(r"\b(?:[0-9a-fA-F]{64}|[0-9a-fA-F]{40}|[0-9a-fA-F]{32})\b")  # SHA256/SHA1/MD5
_MAC = re.compile(r"\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b")
_IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_DOMAIN = re.compile(r"\b(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,24}\b")  # 域名/主机名(IP 已先替换)
_LONG_DIGITS = re.compile(r"\b\d{11,}\b")  # 手机号/长ID等


def desensitize(text: str) -> str:
    """对单段文本脱敏（顺序：URL→邮箱→SID→哈希→MAC→IP→域名→长数字）。"""
    text = _URL.sub("<URL>", text)
    text = _EMAIL.sub("<EMAIL>", text)
    text = _SID.sub("<SID>", text)
    text = _HASH.sub("<HASH>", text)
    text = _MAC.sub("<MAC>", text)
    text = _IPV4.sub("<IP>", text)
    text = _DOMAIN.sub("<DOMAIN>", text)
    text = _LONG_DIGITS.sub("<NUM>", text)
    return text


def desensitize_request(request: LLMRequest) -> LLMRequest:
    """返回一个所有消息内容已脱敏的新请求（不改原对象）。"""
    masked = [Message(role=m.role, content=desensitize(m.content)) for m in request.messages]
    return request.model_copy(update={"messages": masked})
