"""L08 · 告警降噪引擎（分诊前置）。

四级降噪里的前三级在这里（第四级"关联聚合"属关联引擎 correlation，另见 §1.5）：
1. 精确去重：指纹 = hash(来源 + 主机 + 标题) 相同即合并计数；
2. 时间窗归并：同指纹且在滑动时间窗（默认 5min）内 → 并入已存在告警；
3. 抑制规则：用户维护的噪声规则（主机通配 / 来源 / 关键字 / IP）命中即"标记抑制"（不丢弃，可回溯）。

对标业界基线：SIEM（如 Splunk ES / QRadar）都有 dedup + 抑制（suppression）+ 聚合，
这里把它显式做成可解释、可追溯、规则可增删改的能力，而非黑盒。
"""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from fnmatch import fnmatch
from typing import Any

from pydantic import BaseModel

from aisecops.L09_data_platform.alert_store import Alert

_TS_FMT = "%Y-%m-%d %H:%M:%S"


def fingerprint(fields: dict[str, Any]) -> str:
    """去重指纹：来源 + 主机 + 标题 归一化后取 sha1 前 16 位。"""
    parts = [
        str(fields.get("source", "")).strip().lower(),
        str(fields.get("host", "")).strip().lower(),
        str(fields.get("title", "")).strip().lower(),
    ]
    raw = "|".join(parts)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


# ---- 抑制规则 ----

# 规则类型：主机通配(DEV-*) / 来源精确 / 标题关键字 / IP 子串
RULE_KINDS = ("host", "source", "keyword", "ip")


class SuppressionRule(BaseModel):
    """一条抑制规则。"""

    id: str
    name: str
    kind: str = "keyword"  # host / source / keyword / ip
    pattern: str = ""
    enabled: bool = True
    hits: int = 0  # 累计命中次数（可解释"降了多少噪"）


def rule_matches(rule: SuppressionRule, fields: dict[str, Any]) -> bool:
    """规则是否命中该告警。"""
    if not rule.enabled or not rule.pattern:
        return False
    host = str(fields.get("host", ""))
    source = str(fields.get("source", ""))
    title = str(fields.get("title", ""))
    pat = rule.pattern
    if rule.kind == "host":
        return fnmatch(host, pat)
    if rule.kind == "source":
        return source == pat
    if rule.kind == "keyword":
        return pat.lower() in title.lower()
    if rule.kind == "ip":
        return pat in host or pat in title
    return False


class SuppressionStore(ABC):
    """抑制规则存储（仓储模式，与告警/工单一致）。"""

    @abstractmethod
    def all(self) -> list[SuppressionRule]:
        raise NotImplementedError

    @abstractmethod
    def create(self, name: str, kind: str, pattern: str) -> SuppressionRule:
        raise NotImplementedError

    @abstractmethod
    def set_enabled(self, rule_id: str, enabled: bool) -> SuppressionRule | None:
        raise NotImplementedError

    @abstractmethod
    def remove(self, rule_id: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def bump_hit(self, rule_id: str) -> None:
        raise NotImplementedError


class InMemorySuppressionStore(SuppressionStore):
    def __init__(self) -> None:
        self._rules: list[SuppressionRule] = []

    def all(self) -> list[SuppressionRule]:
        return list(self._rules)

    def create(self, name: str, kind: str, pattern: str) -> SuppressionRule:
        seq = len(self._rules) + 1
        rule = SuppressionRule(id=f"SUP-{seq}", name=name, kind=kind, pattern=pattern)
        self._rules.append(rule)
        return rule

    def set_enabled(self, rule_id: str, enabled: bool) -> SuppressionRule | None:
        for r in self._rules:
            if r.id == rule_id:
                r.enabled = enabled
                return r
        return None

    def remove(self, rule_id: str) -> bool:
        before = len(self._rules)
        self._rules = [r for r in self._rules if r.id != rule_id]
        return len(self._rules) < before

    def bump_hit(self, rule_id: str) -> None:
        for r in self._rules:
            if r.id == rule_id:
                r.hits += 1
                return


class PgSuppressionStore(SuppressionStore):
    """PostgreSQL 实现（持久化，P-18）。"""

    _COLS = "seq, name, kind, pattern, enabled, hits"

    def __init__(self, database_url: str) -> None:
        from aisecops.L12_core_support.db import get_pool

        self._pool = get_pool(database_url)
        with self._pool.connection() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS suppression_rules ("
                "seq SERIAL PRIMARY KEY, name text, kind text, pattern text, "
                "enabled boolean DEFAULT true, hits integer DEFAULT 0)"
            )

    @staticmethod
    def _to_rule(r: Any) -> SuppressionRule:
        return SuppressionRule(
            id=f"SUP-{int(r[0])}", name=r[1], kind=r[2], pattern=r[3], enabled=bool(r[4]), hits=int(r[5] or 0)
        )

    @staticmethod
    def _seq_of(rule_id: str) -> int:
        try:
            return int(rule_id.split("-")[1])
        except (ValueError, IndexError):
            return -1

    def all(self) -> list[SuppressionRule]:
        with self._pool.connection() as conn:
            rows = conn.execute(f"SELECT {self._COLS} FROM suppression_rules ORDER BY seq").fetchall()
        return [self._to_rule(r) for r in rows]

    def create(self, name: str, kind: str, pattern: str) -> SuppressionRule:
        with self._pool.connection() as conn:
            row = conn.execute(
                "INSERT INTO suppression_rules (name, kind, pattern) VALUES (%s,%s,%s) RETURNING seq",
                (name, kind, pattern),
            ).fetchone()
        seq = int(row[0]) if row else 0
        return SuppressionRule(id=f"SUP-{seq}", name=name, kind=kind, pattern=pattern)

    def set_enabled(self, rule_id: str, enabled: bool) -> SuppressionRule | None:
        seq = self._seq_of(rule_id)
        with self._pool.connection() as conn:
            conn.execute("UPDATE suppression_rules SET enabled=%s WHERE seq=%s", (enabled, seq))
            row = conn.execute(f"SELECT {self._COLS} FROM suppression_rules WHERE seq=%s", (seq,)).fetchone()
        return self._to_rule(row) if row else None

    def remove(self, rule_id: str) -> bool:
        with self._pool.connection() as conn:
            cur = conn.execute("DELETE FROM suppression_rules WHERE seq=%s", (self._seq_of(rule_id),))
            return bool(cur.rowcount)

    def bump_hit(self, rule_id: str) -> None:
        with self._pool.connection() as conn:
            conn.execute("UPDATE suppression_rules SET hits = hits + 1 WHERE seq=%s", (self._seq_of(rule_id),))


def build_suppression_store(database_url: str = "") -> SuppressionStore:
    """有 database_url 用 PG（连不上回退内存）；否则内存。"""
    if database_url:
        try:
            return PgSuppressionStore(database_url)
        except Exception:
            pass
    return InMemorySuppressionStore()


def seed_demo_rules(store: SuppressionStore) -> None:
    """演示噪声规则（真规则 + 真匹配，命中即抑制）。"""
    if store.all():
        return
    store.create("健康检查心跳", "keyword", "healthcheck")
    store.create("测试环境主机", "host", "DEV-*")
    store.create("已知扫描器来源", "source", "scanner")


# ---- 降噪决策 ----


class DedupDecision(BaseModel):
    """对一条新告警的降噪决策。"""

    action: str  # new / merge / suppress
    fingerprint: str = ""
    target_id: str = ""  # merge 时并入的已存在告警
    rule_id: str = ""  # suppress 时命中的规则
    reason: str = ""


def _parse_ts(ts: str) -> datetime | None:
    try:
        return datetime.strptime(ts, _TS_FMT).replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


class DedupEngine:
    """降噪引擎：抑制 → 精确去重/时间窗归并 → 否则新建。"""

    def __init__(self, rules: SuppressionStore, window_secs: int = 300) -> None:
        self._rules = rules
        self.window_secs = window_secs

    def evaluate(self, fields: dict[str, Any], recent: list[Alert], now: datetime | None = None) -> DedupDecision:
        fp = fingerprint(fields)
        # 1) 抑制规则优先（命中即标记抑制，不参与后续）
        for rule in self._rules.all():
            if rule_matches(rule, fields):
                return DedupDecision(
                    action="suppress", fingerprint=fp, rule_id=rule.id, reason=f"命中抑制规则「{rule.name}」"
                )
        # 2) 精确去重 + 时间窗归并：找最近一条同指纹、且在时间窗内（未抑制）的告警
        now = now or datetime.now(timezone.utc)
        for a in recent:  # recent 已是倒序（最新在前）
            if a.suppressed or a.fingerprint != fp:
                continue
            ats = _parse_ts(a.ts)
            if ats is None or (now - ats).total_seconds() <= self.window_secs:
                return DedupDecision(
                    action="merge", fingerprint=fp, target_id=a.id, reason=f"同指纹 {self.window_secs}s 内归并"
                )
        # 3) 全新告警
        return DedupDecision(action="new", fingerprint=fp)
