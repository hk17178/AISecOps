"""出域判定（C-32）：判断一个 provider 端点是否「出域」（数据离开内网到外部）。

本地地址（localhost / 私有网段）视为不出域，可直接用；
公网地址视为出域，受全局出域开关限制，且调用前必须脱敏。
"""

from __future__ import annotations

from urllib.parse import urlparse

_LOCAL_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}


def is_outbound_url(url: str) -> bool:
    """True 表示该 URL 指向外部（出域）。"""
    host = (urlparse(url).hostname or "").lower()
    if host in _LOCAL_HOSTS:
        return False
    # 私有网段视为内网
    if host.startswith(("10.", "192.168.")):
        return False
    if host.startswith("172."):
        parts = host.split(".")
        if len(parts) >= 2 and parts[1].isdigit() and 16 <= int(parts[1]) <= 31:
            return False
    return True
