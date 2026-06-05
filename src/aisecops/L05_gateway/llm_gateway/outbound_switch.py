"""出域判定（C-32）：判断一个 provider 端点是否「出域」（数据离开内网到外部）。

统一委托 L12 net_guard（修正了 `10.example.com` 这类主机名被 startswith 误判为内网的问题）：
本地/私网视为不出域，可直接用；公网视为出域，受全局出域开关限制且调用前必须脱敏。
"""

from __future__ import annotations

from aisecops.L12_core_support.net_guard import is_outbound_url

__all__ = ["is_outbound_url"]
