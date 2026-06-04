"""L02 · 工单 + HITL 工作流（平台核心）。

C-8 铁律：任何"写"动作默认要人审。真威胁研判 → 自动建 HITL 工单 → 人工批准/驳回。
源无关：接口稳定，默认内存实现；将来换 PG 不改调用方。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

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
    # 审批留痕：谁、什么时候、为什么
    reason: str = ""
    decided_by: str = ""
    decided_at: str = ""


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
    def decide(self, ticket_id: str, status: str, reason: str = "", actor: str = "") -> Ticket:
        """审批：仅"待审"可改为"已批准/已驳回"，并记录理由与操作人。"""
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

    def decide(self, ticket_id: str, status: str, reason: str = "", actor: str = "") -> Ticket:
        for t in self._tickets:
            if t.id == ticket_id:
                if t.status != "待审":
                    raise TicketError(f"工单 {ticket_id} 已处理（{t.status}）")
                t.status = status
                t.reason = reason
                t.decided_by = actor
                t.decided_at = self._clock().strftime("%Y-%m-%d %H:%M:%S")
                return t
        raise TicketError(f"工单 {ticket_id} 不存在")

    def pending_count(self) -> int:
        return sum(1 for t in self._tickets if t.status == "待审")


class PgTicketStore(TicketStore):
    """PostgreSQL 实现（持久化，P-18）。id 由 seq 派生（TKT-{200+seq}）。"""

    _COLS = "seq, action, target, risk, status, source_alert, ts, reason, decided_by, decided_at"

    def __init__(self, database_url: str, clock: Callable[[], datetime] = _default_clock) -> None:
        from aisecops.L12_core_support.db import get_pool

        self._pool = get_pool(database_url)
        self._clock = clock
        with self._pool.connection() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS tickets ("
                "seq SERIAL PRIMARY KEY, action text, target text, risk text, "
                "status text, source_alert text, ts text, reason text, "
                "decided_by text, decided_at text)"
            )

    @staticmethod
    def _to_ticket(r: Any) -> Ticket:
        return Ticket(
            id=f"TKT-{200 + int(r[0])}",
            action=r[1],
            target=r[2],
            risk=r[3],
            status=r[4],
            source_alert=r[5],
            ts=r[6],
            reason=r[7],
            decided_by=r[8],
            decided_at=r[9],
        )

    @staticmethod
    def _seq_of(ticket_id: str) -> int:
        try:
            return int(ticket_id.split("-")[1]) - 200
        except (ValueError, IndexError):
            return -1

    def create(self, action: str, target: str, risk: str = "高", source_alert: str = "") -> Ticket:
        ts = self._clock().strftime("%Y-%m-%d %H:%M:%S")
        with self._pool.connection() as conn:
            row = conn.execute(
                "INSERT INTO tickets (action, target, risk, status, source_alert, ts, "
                "reason, decided_by, decided_at) VALUES (%s,%s,%s,'待审',%s,%s,'','','') "
                "RETURNING seq",
                (action, target, risk, source_alert, ts),
            ).fetchone()
        seq = int(row[0]) if row else 0
        return Ticket(
            id=f"TKT-{200 + seq}",
            action=action,
            target=target,
            risk=risk,
            status="待审",
            source_alert=source_alert,
            ts=ts,
        )

    def all(self) -> list[Ticket]:
        with self._pool.connection() as conn:
            rows = conn.execute(f"SELECT {self._COLS} FROM tickets ORDER BY seq DESC").fetchall()
        return [self._to_ticket(r) for r in rows]

    def decide(self, ticket_id: str, status: str, reason: str = "", actor: str = "") -> Ticket:
        seq = self._seq_of(ticket_id)
        decided_at = self._clock().strftime("%Y-%m-%d %H:%M:%S")
        with self._pool.connection() as conn:
            cur = conn.execute("SELECT status FROM tickets WHERE seq=%s", (seq,)).fetchone()
            if cur is None:
                raise TicketError(f"工单 {ticket_id} 不存在")
            if cur[0] != "待审":
                raise TicketError(f"工单 {ticket_id} 已处理（{cur[0]}）")
            conn.execute(
                "UPDATE tickets SET status=%s, reason=%s, decided_by=%s, decided_at=%s WHERE seq=%s",
                (status, reason, actor, decided_at, seq),
            )
            row = conn.execute(f"SELECT {self._COLS} FROM tickets WHERE seq=%s", (seq,)).fetchone()
        return self._to_ticket(row)

    def pending_count(self) -> int:
        with self._pool.connection() as conn:
            row = conn.execute("SELECT count(*) FROM tickets WHERE status='待审'").fetchone()
        return int(row[0]) if row else 0


def build_ticket_store(database_url: str = "") -> TicketStore:
    """有 database_url 用 PG（连不上回退内存）；否则内存。"""
    if database_url:
        try:
            return PgTicketStore(database_url)
        except Exception:  # noqa: BLE001 —— 连不上就回退
            pass
    return InMemoryTicketStore()


def seed_demo_tickets(store: TicketStore) -> None:
    """演示样例（真 store + 真审批工作流）。"""
    store.create("隔离主机", "WIN-APP-07", "高", "ALERT-0001")
    store.create("禁用账号", "svc_backup", "高", "ALERT-0006")
    store.create("封禁 IP", "185.x.x.x", "中", "ALERT-0002")
