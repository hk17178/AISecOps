"""L02 · SOAR Playbook 引擎（平台核心，与工单引擎并列）。

剧本 = 触发条件 → 动作序列。命中触发 → **高风险动作走 HITL 工单（C-8）** →
批准后才执行（经 L06 调外部工具，当前为占位执行）→ 可撤销。执行有历史，全程留痕。

对标业界基线：SOAR（如 XSOAR / Tines）的 playbook，但"自动执行高风险动作"在本项目
被强制收敛到 HITL——剧本只负责"触发 + 建审批单 + 记录执行"，真正动手必须人批。
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

ACTION_KINDS = ("封禁 IP", "隔离主机", "禁用账号")


class Playbook(BaseModel):
    """一个处置剧本。"""

    id: str
    name: str
    # 触发条件：研判=真威胁（默认）+ 可选 严重度 / 标题关键字
    trigger_verdict: str = "真威胁"
    trigger_severity: str = ""  # 空=不限
    trigger_keyword: str = ""  # 空=不限
    actions: list[str] = Field(default_factory=list)  # 动作序列（封禁 IP / 隔离主机 / 禁用账号）
    risk: str = "高"
    enabled: bool = True
    runs: int = 0  # 累计触发次数


class PlaybookRun(BaseModel):
    """一次剧本执行记录。"""

    id: str
    playbook_id: str
    playbook_name: str
    target: str
    action: str
    status: str = "待审"  # 待审 / 已执行 / 已撤销 / 已驳回
    ticket_id: str = ""
    alert_id: str = ""
    ts: str


def _default_clock() -> datetime:
    return datetime.now(timezone.utc)


def match_playbooks(fields: dict[str, Any], playbooks: list[Playbook]) -> list[Playbook]:
    """返回命中该告警的已启用剧本。"""
    verdict = str(fields.get("verdict", ""))
    severity = str(fields.get("severity", ""))
    title = str(fields.get("title", ""))
    hit = []
    for p in playbooks:
        if not p.enabled:
            continue
        if p.trigger_verdict and verdict != p.trigger_verdict:
            continue
        if p.trigger_severity and severity != p.trigger_severity:
            continue
        if p.trigger_keyword and p.trigger_keyword.lower() not in title.lower():
            continue
        hit.append(p)
    return hit


# ---- 剧本存储 ----


class PlaybookStore(ABC):
    @abstractmethod
    def all(self) -> list[Playbook]:
        raise NotImplementedError

    @abstractmethod
    def get(self, playbook_id: str) -> Playbook | None:
        raise NotImplementedError

    @abstractmethod
    def create(
        self,
        name: str,
        actions: list[str],
        risk: str,
        trigger_verdict: str,
        trigger_severity: str,
        trigger_keyword: str,
    ) -> Playbook:
        raise NotImplementedError

    @abstractmethod
    def set_enabled(self, playbook_id: str, enabled: bool) -> Playbook | None:
        raise NotImplementedError

    @abstractmethod
    def remove(self, playbook_id: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def bump_runs(self, playbook_id: str) -> None:
        raise NotImplementedError


class InMemoryPlaybookStore(PlaybookStore):
    def __init__(self) -> None:
        self._items: list[Playbook] = []

    def all(self) -> list[Playbook]:
        return list(self._items)

    def get(self, playbook_id: str) -> Playbook | None:
        return next((p for p in self._items if p.id == playbook_id), None)

    def create(
        self,
        name: str,
        actions: list[str],
        risk: str,
        trigger_verdict: str,
        trigger_severity: str,
        trigger_keyword: str,
    ) -> Playbook:
        seq = len(self._items) + 1
        pb = Playbook(
            id=f"PB-{seq}",
            name=name,
            actions=actions,
            risk=risk,
            trigger_verdict=trigger_verdict,
            trigger_severity=trigger_severity,
            trigger_keyword=trigger_keyword,
        )
        self._items.append(pb)
        return pb

    def set_enabled(self, playbook_id: str, enabled: bool) -> Playbook | None:
        pb = self.get(playbook_id)
        if pb is not None:
            pb.enabled = enabled
        return pb

    def remove(self, playbook_id: str) -> bool:
        before = len(self._items)
        self._items = [p for p in self._items if p.id != playbook_id]
        return len(self._items) < before

    def bump_runs(self, playbook_id: str) -> None:
        pb = self.get(playbook_id)
        if pb is not None:
            pb.runs += 1


class PgPlaybookStore(PlaybookStore):
    """PostgreSQL 实现（actions 存 JSON 文本）。"""

    _COLS = "seq, name, trigger_verdict, trigger_severity, trigger_keyword, actions, risk, enabled, runs"

    def __init__(self, database_url: str) -> None:
        from aisecops.L12_core_support.db import get_pool

        self._pool = get_pool(database_url)
        with self._pool.connection() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS playbooks ("
                "seq SERIAL PRIMARY KEY, name text, trigger_verdict text, trigger_severity text, "
                "trigger_keyword text, actions text, risk text, enabled boolean DEFAULT true, runs integer DEFAULT 0)"
            )

    @staticmethod
    def _to_pb(r: Any) -> Playbook:
        try:
            actions = json.loads(r[5]) if r[5] else []
        except json.JSONDecodeError:
            actions = []
        return Playbook(
            id=f"PB-{int(r[0])}",
            name=r[1],
            trigger_verdict=r[2] or "",
            trigger_severity=r[3] or "",
            trigger_keyword=r[4] or "",
            actions=actions,
            risk=r[6] or "高",
            enabled=bool(r[7]),
            runs=int(r[8] or 0),
        )

    @staticmethod
    def _seq_of(pb_id: str) -> int:
        try:
            return int(pb_id.split("-")[1])
        except (ValueError, IndexError):
            return -1

    def all(self) -> list[Playbook]:
        with self._pool.connection() as conn:
            rows = conn.execute(f"SELECT {self._COLS} FROM playbooks ORDER BY seq").fetchall()
        return [self._to_pb(r) for r in rows]

    def get(self, playbook_id: str) -> Playbook | None:
        with self._pool.connection() as conn:
            row = conn.execute(
                f"SELECT {self._COLS} FROM playbooks WHERE seq=%s", (self._seq_of(playbook_id),)
            ).fetchone()
        return self._to_pb(row) if row else None

    def create(
        self,
        name: str,
        actions: list[str],
        risk: str,
        trigger_verdict: str,
        trigger_severity: str,
        trigger_keyword: str,
    ) -> Playbook:
        with self._pool.connection() as conn:
            row = conn.execute(
                "INSERT INTO playbooks (name, trigger_verdict, trigger_severity, trigger_keyword, actions, risk) "
                "VALUES (%s,%s,%s,%s,%s,%s) RETURNING seq",
                (
                    name,
                    trigger_verdict,
                    trigger_severity,
                    trigger_keyword,
                    json.dumps(actions, ensure_ascii=False),
                    risk,
                ),
            ).fetchone()
        seq = int(row[0]) if row else 0
        return Playbook(
            id=f"PB-{seq}",
            name=name,
            actions=actions,
            risk=risk,
            trigger_verdict=trigger_verdict,
            trigger_severity=trigger_severity,
            trigger_keyword=trigger_keyword,
        )

    def set_enabled(self, playbook_id: str, enabled: bool) -> Playbook | None:
        seq = self._seq_of(playbook_id)
        with self._pool.connection() as conn:
            conn.execute("UPDATE playbooks SET enabled=%s WHERE seq=%s", (enabled, seq))
            row = conn.execute(f"SELECT {self._COLS} FROM playbooks WHERE seq=%s", (seq,)).fetchone()
        return self._to_pb(row) if row else None

    def remove(self, playbook_id: str) -> bool:
        with self._pool.connection() as conn:
            cur = conn.execute("DELETE FROM playbooks WHERE seq=%s", (self._seq_of(playbook_id),))
            return bool(cur.rowcount)

    def bump_runs(self, playbook_id: str) -> None:
        with self._pool.connection() as conn:
            conn.execute("UPDATE playbooks SET runs = runs + 1 WHERE seq=%s", (self._seq_of(playbook_id),))


# ---- 执行记录存储 ----


class RunStore(ABC):
    @abstractmethod
    def create(self, pb: Playbook, target: str, action: str, ticket_id: str, alert_id: str) -> PlaybookRun:
        raise NotImplementedError

    @abstractmethod
    def all(self) -> list[PlaybookRun]:
        raise NotImplementedError

    @abstractmethod
    def find_by_ticket(self, ticket_id: str) -> PlaybookRun | None:
        raise NotImplementedError

    @abstractmethod
    def set_status(self, run_id: str, status: str) -> PlaybookRun | None:
        raise NotImplementedError


class InMemoryRunStore(RunStore):
    def __init__(self, clock: Callable[[], datetime] = _default_clock) -> None:
        self._runs: list[PlaybookRun] = []
        self._clock = clock

    def create(self, pb: Playbook, target: str, action: str, ticket_id: str, alert_id: str) -> PlaybookRun:
        seq = len(self._runs) + 1
        run = PlaybookRun(
            id=f"RUN-{seq}",
            playbook_id=pb.id,
            playbook_name=pb.name,
            target=target,
            action=action,
            ticket_id=ticket_id,
            alert_id=alert_id,
            ts=self._clock().strftime("%Y-%m-%d %H:%M:%S"),
        )
        self._runs.append(run)
        return run

    def all(self) -> list[PlaybookRun]:
        return list(reversed(self._runs))

    def find_by_ticket(self, ticket_id: str) -> PlaybookRun | None:
        return next((r for r in self._runs if r.ticket_id == ticket_id), None)

    def set_status(self, run_id: str, status: str) -> PlaybookRun | None:
        for r in self._runs:
            if r.id == run_id:
                r.status = status
                return r
        return None


class PgRunStore(RunStore):
    """PostgreSQL 实现。"""

    _COLS = "seq, playbook_id, playbook_name, target, action, status, ticket_id, alert_id, ts"

    def __init__(self, database_url: str, clock: Callable[[], datetime] = _default_clock) -> None:
        from aisecops.L12_core_support.db import get_pool

        self._pool = get_pool(database_url)
        self._clock = clock
        with self._pool.connection() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS playbook_runs ("
                "seq SERIAL PRIMARY KEY, playbook_id text, playbook_name text, target text, action text, "
                "status text DEFAULT '待审', ticket_id text, alert_id text, ts text)"
            )

    @staticmethod
    def _to_run(r: Any) -> PlaybookRun:
        return PlaybookRun(
            id=f"RUN-{int(r[0])}",
            playbook_id=r[1],
            playbook_name=r[2],
            target=r[3],
            action=r[4],
            status=r[5],
            ticket_id=r[6] or "",
            alert_id=r[7] or "",
            ts=r[8],
        )

    @staticmethod
    def _seq_of(run_id: str) -> int:
        try:
            return int(run_id.split("-")[1])
        except (ValueError, IndexError):
            return -1

    def create(self, pb: Playbook, target: str, action: str, ticket_id: str, alert_id: str) -> PlaybookRun:
        ts = self._clock().strftime("%Y-%m-%d %H:%M:%S")
        with self._pool.connection() as conn:
            row = conn.execute(
                "INSERT INTO playbook_runs (playbook_id, playbook_name, target, action, status, ticket_id, alert_id, ts) "
                "VALUES (%s,%s,%s,%s,'待审',%s,%s,%s) RETURNING seq",
                (pb.id, pb.name, target, action, ticket_id, alert_id, ts),
            ).fetchone()
        seq = int(row[0]) if row else 0
        return PlaybookRun(
            id=f"RUN-{seq}",
            playbook_id=pb.id,
            playbook_name=pb.name,
            target=target,
            action=action,
            ticket_id=ticket_id,
            alert_id=alert_id,
            ts=ts,
        )

    def all(self) -> list[PlaybookRun]:
        with self._pool.connection() as conn:
            rows = conn.execute(f"SELECT {self._COLS} FROM playbook_runs ORDER BY seq DESC").fetchall()
        return [self._to_run(r) for r in rows]

    def find_by_ticket(self, ticket_id: str) -> PlaybookRun | None:
        with self._pool.connection() as conn:
            row = conn.execute(f"SELECT {self._COLS} FROM playbook_runs WHERE ticket_id=%s", (ticket_id,)).fetchone()
        return self._to_run(row) if row else None

    def set_status(self, run_id: str, status: str) -> PlaybookRun | None:
        seq = self._seq_of(run_id)
        with self._pool.connection() as conn:
            conn.execute("UPDATE playbook_runs SET status=%s WHERE seq=%s", (status, seq))
            row = conn.execute(f"SELECT {self._COLS} FROM playbook_runs WHERE seq=%s", (seq,)).fetchone()
        return self._to_run(row) if row else None


def build_playbook_store(database_url: str = "") -> PlaybookStore:
    if database_url:
        try:
            return PgPlaybookStore(database_url)
        except Exception:
            pass
    return InMemoryPlaybookStore()


def build_run_store(database_url: str = "") -> RunStore:
    if database_url:
        try:
            return PgRunStore(database_url)
        except Exception:
            pass
    return InMemoryRunStore()


def seed_demo_playbooks(store: PlaybookStore) -> None:
    if store.all():
        return
    store.create("C2 外连封禁", ["封禁 IP"], "高", "真威胁", "", "C2")
    store.create("横移主机隔离", ["隔离主机"], "高", "真威胁", "", "横向")
    store.create("凭证滥用禁号", ["禁用账号"], "中", "真威胁", "", "凭证")
