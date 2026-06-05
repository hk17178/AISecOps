"""L02 · 工单 + HITL 工作流（平台核心）。

C-8 铁律：任何"写"动作默认要人审。真威胁研判 → 自动建 HITL 工单 → 人工批准/驳回。
源无关：接口稳定，默认内存实现；将来换 PG 不改调用方。
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Any

from pydantic import BaseModel, Field

PROGRESS = ("待处理", "处理中", "已完成", "已挂起")
# SLA 时限（小时），按风险定（ADR-0012）
_SLA_HOURS = {"高": 4, "中": 24, "低": 48}


class Ticket(BaseModel):
    """一张 HITL 工单（审批态 + 协作态，ADR-0012）。"""

    id: str
    action: str  # 隔离主机 / 封禁 IP / 禁用账号
    target: str
    risk: str = "高"  # 高 / 中
    status: str = "待审"  # 审批态：待审 / 已批准 / 已驳回
    source_alert: str = ""
    ts: str
    # 审批留痕：谁、什么时候、为什么
    reason: str = ""
    decided_by: str = ""
    decided_at: str = ""
    # 协作态（驾驶舱，ADR-0012）：谁在处理 / 进度 / SLA 截止 / 处理时间线
    assignee: str = ""
    progress: str = "待处理"  # 待处理 / 处理中 / 已完成 / 已挂起
    sla_due: str = ""
    notes: list[dict[str, str]] = Field(default_factory=list)  # [{ts, author, text}]


def _fmt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _sla_due(now: datetime, risk: str) -> str:
    return _fmt(now + timedelta(hours=_SLA_HOURS.get(risk, 24)))


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

    @abstractmethod
    def assign(self, ticket_id: str, assignee: str, actor: str = "") -> Ticket:
        """指派处理人（协作态，ADR-0012）。"""
        raise NotImplementedError

    @abstractmethod
    def update_progress(self, ticket_id: str, progress: str, note: str, author: str) -> Ticket:
        """更新处理进度并追加一条时间线。"""
        raise NotImplementedError


def _default_clock() -> datetime:
    return datetime.now(timezone.utc)


class InMemoryTicketStore(TicketStore):
    def __init__(self, clock: Callable[[], datetime] = _default_clock) -> None:
        self._tickets: list[Ticket] = []
        self._clock = clock

    def create(self, action: str, target: str, risk: str = "高", source_alert: str = "") -> Ticket:
        seq = len(self._tickets) + 1
        now = self._clock()
        ticket = Ticket(
            id=f"TKT-{200 + seq}",
            action=action,
            target=target,
            risk=risk,
            source_alert=source_alert,
            ts=_fmt(now),
            sla_due=_sla_due(now, risk),
        )
        self._tickets.append(ticket)
        return ticket

    def all(self) -> list[Ticket]:
        return list(reversed(self._tickets))

    def _get(self, ticket_id: str) -> Ticket:
        for t in self._tickets:
            if t.id == ticket_id:
                return t
        raise TicketError(f"工单 {ticket_id} 不存在")

    def assign(self, ticket_id: str, assignee: str, actor: str = "") -> Ticket:
        t = self._get(ticket_id)
        t.assignee = assignee
        if t.progress == "待处理":
            t.progress = "处理中"
        t.notes.append({"ts": _fmt(self._clock()), "author": actor or "系统", "text": f"指派给 {assignee}"})
        return t

    def update_progress(self, ticket_id: str, progress: str, note: str, author: str) -> Ticket:
        t = self._get(ticket_id)
        if progress in PROGRESS:
            t.progress = progress
        text = note.strip() or f"进度更新为「{t.progress}」"
        t.notes.append({"ts": _fmt(self._clock()), "author": author, "text": text})
        return t

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

    _COLS = (
        "seq, action, target, risk, status, source_alert, ts, reason, decided_by, decided_at, "
        "assignee, progress, sla_due, notes"
    )

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
            # 协作字段（ADR-0012）：对既有表平滑加列
            for col, ddl in (
                ("assignee", "text DEFAULT ''"),
                ("progress", "text DEFAULT '待处理'"),
                ("sla_due", "text DEFAULT ''"),
                ("notes", "text DEFAULT '[]'"),
            ):
                conn.execute(f"ALTER TABLE tickets ADD COLUMN IF NOT EXISTS {col} {ddl}")

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
            assignee=(r[10] or "") if len(r) > 10 else "",
            progress=(r[11] or "待处理") if len(r) > 11 else "待处理",
            sla_due=(r[12] or "") if len(r) > 12 else "",
            notes=json.loads(r[13]) if len(r) > 13 and r[13] else [],
        )

    @staticmethod
    def _seq_of(ticket_id: str) -> int:
        try:
            return int(ticket_id.split("-")[1]) - 200
        except (ValueError, IndexError):
            return -1

    def create(self, action: str, target: str, risk: str = "高", source_alert: str = "") -> Ticket:
        now = self._clock()
        ts = _fmt(now)
        sla = _sla_due(now, risk)
        with self._pool.connection() as conn:
            row = conn.execute(
                "INSERT INTO tickets (action, target, risk, status, source_alert, ts, "
                "reason, decided_by, decided_at, assignee, progress, sla_due, notes) "
                "VALUES (%s,%s,%s,'待审',%s,%s,'','','','','待处理',%s,'[]') RETURNING seq",
                (action, target, risk, source_alert, ts, sla),
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
            sla_due=sla,
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

    def _fetch(self, seq: int) -> Ticket:
        with self._pool.connection() as conn:
            row = conn.execute(f"SELECT {self._COLS} FROM tickets WHERE seq=%s", (seq,)).fetchone()
        if row is None:
            raise TicketError("工单不存在")
        return self._to_ticket(row)

    def assign(self, ticket_id: str, assignee: str, actor: str = "") -> Ticket:
        seq = self._seq_of(ticket_id)
        t = self._fetch(seq)
        notes = [*t.notes, {"ts": _fmt(self._clock()), "author": actor or "系统", "text": f"指派给 {assignee}"}]
        progress = "处理中" if t.progress == "待处理" else t.progress
        with self._pool.connection() as conn:
            conn.execute(
                "UPDATE tickets SET assignee=%s, progress=%s, notes=%s WHERE seq=%s",
                (assignee, progress, json.dumps(notes, ensure_ascii=False), seq),
            )
        return self._fetch(seq)

    def update_progress(self, ticket_id: str, progress: str, note: str, author: str) -> Ticket:
        seq = self._seq_of(ticket_id)
        t = self._fetch(seq)
        new_progress = progress if progress in PROGRESS else t.progress
        text = note.strip() or f"进度更新为「{new_progress}」"
        notes = [*t.notes, {"ts": _fmt(self._clock()), "author": author, "text": text}]
        with self._pool.connection() as conn:
            conn.execute(
                "UPDATE tickets SET progress=%s, notes=%s WHERE seq=%s",
                (new_progress, json.dumps(notes, ensure_ascii=False), seq),
            )
        return self._fetch(seq)


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
