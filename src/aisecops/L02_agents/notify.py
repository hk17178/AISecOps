"""L02 · 通知中枢（平台核心）。

三件套：**渠道**（企微/钉钉/通用 Webhook，含 webhook 地址）+ **外发规则**（命中即发，
按 研判/严重度/关键字）+ **发送记录**（成功/失败/备注，可追溯）。真正发送经 L06 适配器，
受全局出域开关约束（C-32）。webhook 地址是密钥，API 不回明文（脱敏，P-18 后续入库加密）。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel


def mask_url(url: str) -> str:
    """webhook 地址脱敏：只留尾部少量字符。"""
    if not url:
        return ""
    return f"…{url[-6:]}" if len(url) > 6 else "已配置"


class Channel(BaseModel):
    id: str
    name: str
    kind: str = "wechat"  # wechat / dingtalk / webhook
    url: str = ""  # webhook 地址（密钥，不外泄）
    enabled: bool = True


class DispatchRule(BaseModel):
    id: str
    name: str
    trigger_verdict: str = "真威胁"
    trigger_severity: str = ""  # 空=不限
    trigger_keyword: str = ""  # 空=不限
    channel_id: str = ""
    enabled: bool = True
    hits: int = 0


class SendRecord(BaseModel):
    id: str
    channel_name: str
    kind: str
    title: str
    status: str  # 成功 / 失败
    note: str = ""
    error: str = ""
    ts: str


def match_dispatch_rules(fields: dict[str, Any], rules: list[DispatchRule]) -> list[DispatchRule]:
    """命中该告警的已启用外发规则。"""
    verdict = str(fields.get("verdict", ""))
    severity = str(fields.get("severity", ""))
    title = str(fields.get("title", ""))
    hit = []
    for r in rules:
        if not r.enabled:
            continue
        if r.trigger_verdict and verdict != r.trigger_verdict:
            continue
        if r.trigger_severity and severity != r.trigger_severity:
            continue
        if r.trigger_keyword and r.trigger_keyword.lower() not in title.lower():
            continue
        hit.append(r)
    return hit


def _default_clock() -> datetime:
    return datetime.now(timezone.utc)


# ---- 渠道存储 ----


class ChannelStore(ABC):
    @abstractmethod
    def all(self) -> list[Channel]:
        raise NotImplementedError

    @abstractmethod
    def get(self, channel_id: str) -> Channel | None:
        raise NotImplementedError

    @abstractmethod
    def create(self, name: str, kind: str, url: str) -> Channel:
        raise NotImplementedError

    @abstractmethod
    def set_enabled(self, channel_id: str, enabled: bool) -> Channel | None:
        raise NotImplementedError

    @abstractmethod
    def remove(self, channel_id: str) -> bool:
        raise NotImplementedError


class InMemoryChannelStore(ChannelStore):
    def __init__(self) -> None:
        self._items: list[Channel] = []

    def all(self) -> list[Channel]:
        return list(self._items)

    def get(self, channel_id: str) -> Channel | None:
        return next((c for c in self._items if c.id == channel_id), None)

    def create(self, name: str, kind: str, url: str) -> Channel:
        seq = len(self._items) + 1
        ch = Channel(id=f"CH-{seq}", name=name, kind=kind, url=url)
        self._items.append(ch)
        return ch

    def set_enabled(self, channel_id: str, enabled: bool) -> Channel | None:
        ch = self.get(channel_id)
        if ch is not None:
            ch.enabled = enabled
        return ch

    def remove(self, channel_id: str) -> bool:
        before = len(self._items)
        self._items = [c for c in self._items if c.id != channel_id]
        return len(self._items) < before


class PgChannelStore(ChannelStore):
    _COLS = "seq, name, kind, url, enabled"

    def __init__(self, database_url: str) -> None:
        from aisecops.L12_core_support.db import get_pool

        self._pool = get_pool(database_url)
        with self._pool.connection() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS channels ("
                "seq SERIAL PRIMARY KEY, name text, kind text, url text, enabled boolean DEFAULT true)"
            )

    @staticmethod
    def _to_ch(r: Any) -> Channel:
        return Channel(id=f"CH-{int(r[0])}", name=r[1], kind=r[2], url=r[3] or "", enabled=bool(r[4]))

    @staticmethod
    def _seq_of(cid: str) -> int:
        try:
            return int(cid.split("-")[1])
        except (ValueError, IndexError):
            return -1

    def all(self) -> list[Channel]:
        with self._pool.connection() as conn:
            rows = conn.execute(f"SELECT {self._COLS} FROM channels ORDER BY seq").fetchall()
        return [self._to_ch(r) for r in rows]

    def get(self, channel_id: str) -> Channel | None:
        with self._pool.connection() as conn:
            row = conn.execute(
                f"SELECT {self._COLS} FROM channels WHERE seq=%s", (self._seq_of(channel_id),)
            ).fetchone()
        return self._to_ch(row) if row else None

    def create(self, name: str, kind: str, url: str) -> Channel:
        with self._pool.connection() as conn:
            row = conn.execute(
                "INSERT INTO channels (name, kind, url) VALUES (%s,%s,%s) RETURNING seq", (name, kind, url)
            ).fetchone()
        seq = int(row[0]) if row else 0
        return Channel(id=f"CH-{seq}", name=name, kind=kind, url=url)

    def set_enabled(self, channel_id: str, enabled: bool) -> Channel | None:
        seq = self._seq_of(channel_id)
        with self._pool.connection() as conn:
            conn.execute("UPDATE channels SET enabled=%s WHERE seq=%s", (enabled, seq))
            row = conn.execute(f"SELECT {self._COLS} FROM channels WHERE seq=%s", (seq,)).fetchone()
        return self._to_ch(row) if row else None

    def remove(self, channel_id: str) -> bool:
        with self._pool.connection() as conn:
            cur = conn.execute("DELETE FROM channels WHERE seq=%s", (self._seq_of(channel_id),))
            return bool(cur.rowcount)


# ---- 外发规则存储 ----


class DispatchRuleStore(ABC):
    @abstractmethod
    def all(self) -> list[DispatchRule]:
        raise NotImplementedError

    @abstractmethod
    def create(
        self, name: str, channel_id: str, trigger_verdict: str, trigger_severity: str, trigger_keyword: str
    ) -> DispatchRule:
        raise NotImplementedError

    @abstractmethod
    def set_enabled(self, rule_id: str, enabled: bool) -> DispatchRule | None:
        raise NotImplementedError

    @abstractmethod
    def remove(self, rule_id: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def bump_hit(self, rule_id: str) -> None:
        raise NotImplementedError


class InMemoryDispatchRuleStore(DispatchRuleStore):
    def __init__(self) -> None:
        self._items: list[DispatchRule] = []

    def all(self) -> list[DispatchRule]:
        return list(self._items)

    def create(
        self, name: str, channel_id: str, trigger_verdict: str, trigger_severity: str, trigger_keyword: str
    ) -> DispatchRule:
        seq = len(self._items) + 1
        r = DispatchRule(
            id=f"DR-{seq}",
            name=name,
            channel_id=channel_id,
            trigger_verdict=trigger_verdict,
            trigger_severity=trigger_severity,
            trigger_keyword=trigger_keyword,
        )
        self._items.append(r)
        return r

    def set_enabled(self, rule_id: str, enabled: bool) -> DispatchRule | None:
        r = next((x for x in self._items if x.id == rule_id), None)
        if r is not None:
            r.enabled = enabled
        return r

    def remove(self, rule_id: str) -> bool:
        before = len(self._items)
        self._items = [x for x in self._items if x.id != rule_id]
        return len(self._items) < before

    def bump_hit(self, rule_id: str) -> None:
        r = next((x for x in self._items if x.id == rule_id), None)
        if r is not None:
            r.hits += 1


class PgDispatchRuleStore(DispatchRuleStore):
    _COLS = "seq, name, trigger_verdict, trigger_severity, trigger_keyword, channel_id, enabled, hits"

    def __init__(self, database_url: str) -> None:
        from aisecops.L12_core_support.db import get_pool

        self._pool = get_pool(database_url)
        with self._pool.connection() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS dispatch_rules ("
                "seq SERIAL PRIMARY KEY, name text, trigger_verdict text, trigger_severity text, "
                "trigger_keyword text, channel_id text, enabled boolean DEFAULT true, hits integer DEFAULT 0)"
            )

    @staticmethod
    def _to_rule(r: Any) -> DispatchRule:
        return DispatchRule(
            id=f"DR-{int(r[0])}",
            name=r[1],
            trigger_verdict=r[2] or "",
            trigger_severity=r[3] or "",
            trigger_keyword=r[4] or "",
            channel_id=r[5] or "",
            enabled=bool(r[6]),
            hits=int(r[7] or 0),
        )

    @staticmethod
    def _seq_of(rid: str) -> int:
        try:
            return int(rid.split("-")[1])
        except (ValueError, IndexError):
            return -1

    def all(self) -> list[DispatchRule]:
        with self._pool.connection() as conn:
            rows = conn.execute(f"SELECT {self._COLS} FROM dispatch_rules ORDER BY seq").fetchall()
        return [self._to_rule(r) for r in rows]

    def create(
        self, name: str, channel_id: str, trigger_verdict: str, trigger_severity: str, trigger_keyword: str
    ) -> DispatchRule:
        with self._pool.connection() as conn:
            row = conn.execute(
                "INSERT INTO dispatch_rules (name, trigger_verdict, trigger_severity, trigger_keyword, channel_id) "
                "VALUES (%s,%s,%s,%s,%s) RETURNING seq",
                (name, trigger_verdict, trigger_severity, trigger_keyword, channel_id),
            ).fetchone()
        seq = int(row[0]) if row else 0
        return DispatchRule(
            id=f"DR-{seq}",
            name=name,
            channel_id=channel_id,
            trigger_verdict=trigger_verdict,
            trigger_severity=trigger_severity,
            trigger_keyword=trigger_keyword,
        )

    def set_enabled(self, rule_id: str, enabled: bool) -> DispatchRule | None:
        seq = self._seq_of(rule_id)
        with self._pool.connection() as conn:
            conn.execute("UPDATE dispatch_rules SET enabled=%s WHERE seq=%s", (enabled, seq))
            row = conn.execute(f"SELECT {self._COLS} FROM dispatch_rules WHERE seq=%s", (seq,)).fetchone()
        return self._to_rule(row) if row else None

    def remove(self, rule_id: str) -> bool:
        with self._pool.connection() as conn:
            cur = conn.execute("DELETE FROM dispatch_rules WHERE seq=%s", (self._seq_of(rule_id),))
            return bool(cur.rowcount)

    def bump_hit(self, rule_id: str) -> None:
        with self._pool.connection() as conn:
            conn.execute("UPDATE dispatch_rules SET hits = hits + 1 WHERE seq=%s", (self._seq_of(rule_id),))


# ---- 发送记录存储 ----


class RecordStore(ABC):
    @abstractmethod
    def add(self, channel_name: str, kind: str, title: str, status: str, note: str, error: str) -> SendRecord:
        raise NotImplementedError

    @abstractmethod
    def recent(self, limit: int = 50) -> list[SendRecord]:
        raise NotImplementedError


class InMemoryRecordStore(RecordStore):
    def __init__(self, clock: Callable[[], datetime] = _default_clock) -> None:
        self._items: list[SendRecord] = []
        self._clock = clock

    def add(self, channel_name: str, kind: str, title: str, status: str, note: str, error: str) -> SendRecord:
        seq = len(self._items) + 1
        rec = SendRecord(
            id=f"SND-{seq}",
            channel_name=channel_name,
            kind=kind,
            title=title,
            status=status,
            note=note,
            error=error,
            ts=self._clock().strftime("%Y-%m-%d %H:%M:%S"),
        )
        self._items.append(rec)
        return rec

    def recent(self, limit: int = 50) -> list[SendRecord]:
        return list(reversed(self._items))[:limit]


class PgRecordStore(RecordStore):
    _COLS = "seq, channel_name, kind, title, status, note, error, ts"

    def __init__(self, database_url: str, clock: Callable[[], datetime] = _default_clock) -> None:
        from aisecops.L12_core_support.db import get_pool

        self._pool = get_pool(database_url)
        self._clock = clock
        with self._pool.connection() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS send_records ("
                "seq SERIAL PRIMARY KEY, channel_name text, kind text, title text, "
                "status text, note text, error text, ts text)"
            )

    @staticmethod
    def _to_rec(r: Any) -> SendRecord:
        return SendRecord(
            id=f"SND-{int(r[0])}",
            channel_name=r[1],
            kind=r[2],
            title=r[3],
            status=r[4],
            note=r[5] or "",
            error=r[6] or "",
            ts=r[7],
        )

    def add(self, channel_name: str, kind: str, title: str, status: str, note: str, error: str) -> SendRecord:
        ts = self._clock().strftime("%Y-%m-%d %H:%M:%S")
        with self._pool.connection() as conn:
            row = conn.execute(
                "INSERT INTO send_records (channel_name, kind, title, status, note, error, ts) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING seq",
                (channel_name, kind, title, status, note, error, ts),
            ).fetchone()
        seq = int(row[0]) if row else 0
        return SendRecord(
            id=f"SND-{seq}",
            channel_name=channel_name,
            kind=kind,
            title=title,
            status=status,
            note=note,
            error=error,
            ts=ts,
        )

    def recent(self, limit: int = 50) -> list[SendRecord]:
        with self._pool.connection() as conn:
            rows = conn.execute(
                f"SELECT {self._COLS} FROM send_records ORDER BY seq DESC LIMIT %s", (limit,)
            ).fetchall()
        return [self._to_rec(r) for r in rows]


def build_channel_store(database_url: str = "") -> ChannelStore:
    if database_url:
        try:
            return PgChannelStore(database_url)
        except Exception:
            pass
    return InMemoryChannelStore()


def build_dispatch_rule_store(database_url: str = "") -> DispatchRuleStore:
    if database_url:
        try:
            return PgDispatchRuleStore(database_url)
        except Exception:
            pass
    return InMemoryDispatchRuleStore()


def build_record_store(database_url: str = "") -> RecordStore:
    if database_url:
        try:
            return PgRecordStore(database_url)
        except Exception:
            pass
    return InMemoryRecordStore()


def seed_demo_channels_rules(channels: ChannelStore, rules: DispatchRuleStore, wechat_url: str = "") -> None:
    """演示渠道 + 规则（首次空库）。"""
    if not channels.all():
        channels.create("企业微信 · 值班群", "wechat", wechat_url)
        channels.create("通用 Webhook", "webhook", "")
    if not rules.all():
        ch = channels.all()[0].id
        rules.create("真威胁严重→企微", ch, "真威胁", "严重", "")
        rules.create("C2 外连→企微", ch, "真威胁", "", "C2")
