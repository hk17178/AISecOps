"""L09 · 安全事件存储（关联分析确认后的产物）。

高置信关联簇经人工确认 → 升级为「安全事件」，可进调查/处置。仓储模式，与告警/工单一致。
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class SecurityEvent(BaseModel):
    """一个安全事件（由关联簇确认而来）。"""

    id: str
    title: str
    severity: str = "高"
    summary: str = ""
    alert_ids: list[str] = Field(default_factory=list)
    status: str = "调查中"  # 调查中 / 已处置 / 已关闭
    ts: str


def _default_clock() -> datetime:
    return datetime.now(timezone.utc)


class EventStore(ABC):
    @abstractmethod
    def create(self, title: str, severity: str, summary: str, alert_ids: list[str]) -> SecurityEvent:
        raise NotImplementedError

    @abstractmethod
    def all(self) -> list[SecurityEvent]:
        raise NotImplementedError

    @abstractmethod
    def count(self) -> int:
        raise NotImplementedError


class InMemoryEventStore(EventStore):
    def __init__(self, clock: Callable[[], datetime] = _default_clock) -> None:
        self._events: list[SecurityEvent] = []
        self._clock = clock

    def create(self, title: str, severity: str, summary: str, alert_ids: list[str]) -> SecurityEvent:
        seq = len(self._events) + 1
        ev = SecurityEvent(
            id=f"EVT-{100 + seq}",
            title=title,
            severity=severity,
            summary=summary,
            alert_ids=alert_ids,
            ts=self._clock().strftime("%Y-%m-%d %H:%M:%S"),
        )
        self._events.append(ev)
        return ev

    def all(self) -> list[SecurityEvent]:
        return list(reversed(self._events))

    def count(self) -> int:
        return len(self._events)


class PgEventStore(EventStore):
    """PostgreSQL 实现（持久化，P-18）。alert_ids 存 JSON 文本。"""

    _COLS = "seq, title, severity, summary, alert_ids, status, ts"

    def __init__(self, database_url: str, clock: Callable[[], datetime] = _default_clock) -> None:
        from aisecops.L12_core_support.db import get_pool

        self._pool = get_pool(database_url)
        self._clock = clock
        with self._pool.connection() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS events ("
                "seq SERIAL PRIMARY KEY, title text, severity text, summary text, "
                "alert_ids text, status text DEFAULT '调查中', ts text)"
            )

    @staticmethod
    def _to_event(r: Any) -> SecurityEvent:
        try:
            alert_ids = json.loads(r[4]) if r[4] else []
        except json.JSONDecodeError:
            alert_ids = []
        return SecurityEvent(
            id=f"EVT-{100 + int(r[0])}",
            title=r[1],
            severity=r[2],
            summary=r[3],
            alert_ids=alert_ids,
            status=r[5],
            ts=r[6],
        )

    def create(self, title: str, severity: str, summary: str, alert_ids: list[str]) -> SecurityEvent:
        ts = self._clock().strftime("%Y-%m-%d %H:%M:%S")
        with self._pool.connection() as conn:
            row = conn.execute(
                "INSERT INTO events (title, severity, summary, alert_ids, status, ts) "
                "VALUES (%s,%s,%s,%s,'调查中',%s) RETURNING seq",
                (title, severity, summary, json.dumps(alert_ids, ensure_ascii=False), ts),
            ).fetchone()
        seq = int(row[0]) if row else 0
        return SecurityEvent(
            id=f"EVT-{100 + seq}", title=title, severity=severity, summary=summary, alert_ids=alert_ids, ts=ts
        )

    def all(self) -> list[SecurityEvent]:
        with self._pool.connection() as conn:
            rows = conn.execute(f"SELECT {self._COLS} FROM events ORDER BY seq DESC").fetchall()
        return [self._to_event(r) for r in rows]

    def count(self) -> int:
        with self._pool.connection() as conn:
            row = conn.execute("SELECT count(*) FROM events").fetchone()
        return int(row[0]) if row else 0


def build_event_store(database_url: str = "") -> EventStore:
    """有 database_url 用 PG（连不上回退内存）；否则内存。"""
    if database_url:
        try:
            return PgEventStore(database_url)
        except Exception:
            pass
    return InMemoryEventStore()
