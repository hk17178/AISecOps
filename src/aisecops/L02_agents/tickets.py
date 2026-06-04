"""L02 · 工单 + HITL 工作流（平台核心）。

C-8 铁律：任何"写"动作默认要人审。真威胁研判 → 自动建 HITL 工单 → 人工批准/驳回。
源无关：接口稳定，默认内存实现；将来换 PG 不改调用方。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import datetime, timezone

from pydantic import BaseModel


class Ticket(BaseModel):
    """一张 HITL 审批工单。"""

    id: str
    action: str  # 隔离主机 / 封禁 IP / 禁用账号
    target: str
    risk: str = "高"  # 高 / 中
    status: str = "待审"  # 待审 / 已批准 / 已驳回
    source_alert: str = ""
    ts: str


class TicketError(Exception):
    """工单操作错误（不存在 / 已处理）。"""


class TicketStore(ABC):
    @abstractmethod
    def create(self, action: str, target: str, risk: str = "高", source_alert: str = "") -> Ticket:
        raise NotImplementedError

    @abstractmethod
    def all(self) -> list[Ticket]:
        raise NotImplementedError

    @abstractmethod
    def decide(self, ticket_id: str, status: str) -> Ticket:
        """审批：仅"待审"可改为"已批准/已驳回"。"""
        raise NotImplementedError

    @abstractmethod
    def pending_count(self) -> int:
        raise NotImplementedError


def _default_clock() -> datetime:
    return datetime.now(timezone.utc)


class InMemoryTicketStore(TicketStore):
    def __init__(self, clock: Callable[[], datetime] = _default_clock) -> None:
        self._tickets: list[Ticket] = []
        self._clock = clock

    def create(self, action: str, target: str, risk: str = "高", source_alert: str = "") -> Ticket:
        seq = len(self._tickets) + 1
        ticket = Ticket(
            id=f"TKT-{200 + seq}",
            action=action,
            target=target,
            risk=risk,
            source_alert=source_alert,
            ts=self._clock().strftime("%Y-%m-%d %H:%M:%S"),
        )
        self._tickets.append(ticket)
        return ticket

    def all(self) -> list[Ticket]:
        return list(reversed(self._tickets))

    def decide(self, ticket_id: str, status: str) -> Ticket:
        for t in self._tickets:
            if t.id == ticket_id:
                if t.status != "待审":
                    raise TicketError(f"工单 {ticket_id} 已处理（{t.status}）")
                t.status = status
                return t
        raise TicketError(f"工单 {ticket_id} 不存在")

    def pending_count(self) -> int:
        return sum(1 for t in self._tickets if t.status == "待审")


def seed_demo_tickets(store: TicketStore) -> None:
    """演示样例（真 store + 真审批工作流）。"""
    store.create("隔离主机", "WIN-APP-07", "高", "ALERT-0001")
    store.create("禁用账号", "svc_backup", "高", "ALERT-0006")
    store.create("封禁 IP", "185.x.x.x", "中", "ALERT-0002")
