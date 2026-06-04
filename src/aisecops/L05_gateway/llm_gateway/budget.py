"""月度 Token 预算（⭐ 自用关键）。

超限抛 BudgetExceeded，供 Gateway 拦截 / 告警 / 降级。
时钟可注入，便于测试不依赖真实时间。
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Callable


class BudgetExceeded(Exception):
    """本月度预算已超上限。"""


def _default_clock() -> datetime:
    return datetime.now(timezone.utc)


class BudgetTracker:
    """按自然月记账的预算闸门。"""

    def __init__(
        self,
        monthly_cap_cny: float,
        clock: Callable[[], datetime] = _default_clock,
    ) -> None:
        self.monthly_cap_cny = monthly_cap_cny
        self._clock = clock
        self._spent: dict[str, float] = defaultdict(float)

    def _period(self) -> str:
        return self._clock().strftime("%Y-%m")

    def spent(self) -> float:
        """本月已花（人民币）。"""
        return self._spent[self._period()]

    def remaining(self) -> float:
        """本月剩余额度。"""
        return max(0.0, self.monthly_cap_cny - self.spent())

    def check(self, estimated_cny: float = 0.0) -> None:
        """预算闸门：本期已花 + 预估 超上限则抛 BudgetExceeded。"""
        if self.spent() + estimated_cny > self.monthly_cap_cny:
            raise BudgetExceeded(
                f"月度预算超限：{self._period()} 已用 ¥{self.spent():.4f} / 上限 ¥{self.monthly_cap_cny:.2f}"
            )

    def record(self, cost_cny: float) -> None:
        """记一笔消费。"""
        self._spent[self._period()] += cost_cny
