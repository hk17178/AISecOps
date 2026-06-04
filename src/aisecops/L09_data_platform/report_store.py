"""L09 · 报表存储（生成的报告，平台衍生数据）。

报告 = 按模板从真数据汇总成的 Markdown 文档，可列表、可重看、可导出。仓储模式。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any


class Report:  # 轻量数据类（避免 BaseModel 对长 markdown 的开销，纯字段）
    def __init__(self, id: str, kind: str, title: str, markdown: str, summary: str, ts: str) -> None:
        self.id = id
        self.kind = kind
        self.title = title
        self.markdown = markdown
        self.summary = summary
        self.ts = ts

    def meta(self) -> dict[str, Any]:
        """列表用：不含正文。"""
        return {"id": self.id, "kind": self.kind, "title": self.title, "summary": self.summary, "ts": self.ts}

    def full(self) -> dict[str, Any]:
        return {**self.meta(), "markdown": self.markdown}


def _default_clock() -> datetime:
    return datetime.now(timezone.utc)


class ReportStore(ABC):
    @abstractmethod
    def create(self, kind: str, title: str, markdown: str, summary: str) -> Report:
        raise NotImplementedError

    @abstractmethod
    def all(self) -> list[Report]:
        raise NotImplementedError

    @abstractmethod
    def get(self, report_id: str) -> Report | None:
        raise NotImplementedError


class InMemoryReportStore(ReportStore):
    def __init__(self, clock: Callable[[], datetime] = _default_clock) -> None:
        self._items: list[Report] = []
        self._clock = clock

    def create(self, kind: str, title: str, markdown: str, summary: str) -> Report:
        seq = len(self._items) + 1
        rep = Report(
            id=f"RPT-{seq}",
            kind=kind,
            title=title,
            markdown=markdown,
            summary=summary,
            ts=self._clock().strftime("%Y-%m-%d %H:%M:%S"),
        )
        self._items.append(rep)
        return rep

    def all(self) -> list[Report]:
        return list(reversed(self._items))

    def get(self, report_id: str) -> Report | None:
        return next((r for r in self._items if r.id == report_id), None)


class PgReportStore(ReportStore):
    """PostgreSQL 实现（持久化，P-18）。"""

    _COLS = "seq, kind, title, markdown, summary, ts"

    def __init__(self, database_url: str, clock: Callable[[], datetime] = _default_clock) -> None:
        from aisecops.L12_core_support.db import get_pool

        self._pool = get_pool(database_url)
        self._clock = clock
        with self._pool.connection() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS reports ("
                "seq SERIAL PRIMARY KEY, kind text, title text, markdown text, summary text, ts text)"
            )

    @staticmethod
    def _to_report(r: Any) -> Report:
        return Report(id=f"RPT-{int(r[0])}", kind=r[1], title=r[2], markdown=r[3] or "", summary=r[4] or "", ts=r[5])

    @staticmethod
    def _seq_of(rid: str) -> int:
        try:
            return int(rid.split("-")[1])
        except (ValueError, IndexError):
            return -1

    def create(self, kind: str, title: str, markdown: str, summary: str) -> Report:
        ts = self._clock().strftime("%Y-%m-%d %H:%M:%S")
        with self._pool.connection() as conn:
            row = conn.execute(
                "INSERT INTO reports (kind, title, markdown, summary, ts) VALUES (%s,%s,%s,%s,%s) RETURNING seq",
                (kind, title, markdown, summary, ts),
            ).fetchone()
        seq = int(row[0]) if row else 0
        return Report(id=f"RPT-{seq}", kind=kind, title=title, markdown=markdown, summary=summary, ts=ts)

    def all(self) -> list[Report]:
        with self._pool.connection() as conn:
            rows = conn.execute(f"SELECT {self._COLS} FROM reports ORDER BY seq DESC").fetchall()
        return [self._to_report(r) for r in rows]

    def get(self, report_id: str) -> Report | None:
        with self._pool.connection() as conn:
            row = conn.execute(f"SELECT {self._COLS} FROM reports WHERE seq=%s", (self._seq_of(report_id),)).fetchone()
        return self._to_report(row) if row else None


def build_report_store(database_url: str = "") -> ReportStore:
    if database_url:
        try:
            return PgReportStore(database_url)
        except Exception:
            pass
    return InMemoryReportStore()
