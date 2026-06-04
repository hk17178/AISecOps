"""L06 · 通知发送适配器（vendors 类薄适配器）。

把"发一条消息到企微/钉钉/通用 Webhook"统一成一个接口。真正出域（HTTP POST 到外部）
只在全局出域开关开启时发生（C-32：数据离开内网默认关）；关闭时用 StubNotifier，
不联网、返回"未真实出域"，让测试/离线可跑、生产默认安全。
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import httpx

# 各渠道的消息体格式（都是 POST JSON）
CHANNEL_KINDS = ("wechat", "dingtalk", "webhook")


class Notifier(ABC):
    """消息发送接口。返回 (是否成功, 错误信息, 备注)。"""

    @abstractmethod
    def send(self, kind: str, url: str, title: str, content: str) -> tuple[bool, str, str]:
        raise NotImplementedError


def _payload(kind: str, title: str, content: str) -> dict[str, object]:
    text = f"{title}\n{content}".strip()
    if kind in ("wechat", "dingtalk"):
        return {"msgtype": "text", "text": {"content": text}}
    return {"title": title, "content": content}


class StubNotifier(Notifier):
    """离线/出域关闭时用：不联网，恒"成功（未真实出域）"。"""

    def send(self, kind: str, url: str, title: str, content: str) -> tuple[bool, str, str]:
        if not url:
            return False, "渠道未配置 webhook 地址", ""
        return True, "", "stub（出域关闭，未真实发送）"


class HttpNotifier(Notifier):
    """真实发送：POST 到渠道 webhook（出域开关开启时使用）。"""

    def __init__(self, timeout: float = 8.0) -> None:
        self.timeout = timeout

    def send(self, kind: str, url: str, title: str, content: str) -> tuple[bool, str, str]:
        if not url:
            return False, "渠道未配置 webhook 地址", ""
        try:
            resp = httpx.post(url, json=_payload(kind, title, content), timeout=self.timeout)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            return False, f"发送失败：{exc}", ""
        return True, "", "已发送"


def build_notifier(outbound_enabled: bool) -> Notifier:
    """出域开关开 → 真实发送；否则 stub（安全默认）。"""
    return HttpNotifier() if outbound_enabled else StubNotifier()
