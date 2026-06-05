"""L12 · 审计日志（C-23：append-only + 哈希链，不可篡改）。

每条记录链上一条的 hash → 任何历史改动都会让 verify() 失败（防篡改可检测）。
跨层（ADR-0008）：L12 横切支撑，任何层经 ctx 写审计。
源无关：默认内存；将来落 PG/对象存储不改接口。
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any, Protocol

from pydantic import BaseModel, Field

GENESIS_HASH = "0" * 64


class AuditSink(Protocol):
    """审计链的结构化契约（内存 AuditLog 与 PgAuditLog 都满足）。"""

    def append(
        self, actor: str, action: str, target: str = "", details: dict[str, Any] | None = None
    ) -> AuditEntry: ...

    @property
    def entries(self) -> list[AuditEntry]: ...

    def verify(self) -> bool: ...


def _default_clock() -> datetime:
    return datetime.now(timezone.utc)


class AuditEntry(BaseModel):
    """一条审计记录。"""

    seq: int
    timestamp: str
    actor: str  # 谁（agent / 用户）
    action: str  # 做了什么（dispatch / verdict / approve ...）
    target: str = ""  # 对象（主机 / 工单 ...）
    details: dict[str, Any] = Field(default_factory=dict)
    prev_hash: str
    entry_hash: str


def _payload(entry_fields: dict[str, Any]) -> dict[str, Any]:
    return {
        "seq": entry_fields["seq"],
        "timestamp": entry_fields["timestamp"],
        "actor": entry_fields["actor"],
        "action": entry_fields["action"],
        "target": entry_fields["target"],
        "details": entry_fields["details"],
    }


def _compute_hash(prev_hash: str, payload: dict[str, Any]) -> str:
    blob = prev_hash + json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


class AuditLog:
    """append-only 审计链。"""

    def __init__(self, clock: Callable[[], datetime] = _default_clock) -> None:
        self._entries: list[AuditEntry] = []
        self._clock = clock

    def append(
        self,
        actor: str,
        action: str,
        target: str = "",
        details: dict[str, Any] | None = None,
    ) -> AuditEntry:
        """追加一条审计（自动链上一条 hash）。"""
        prev = self._entries[-1].entry_hash if self._entries else GENESIS_HASH
        seq = len(self._entries)
        timestamp = self._clock().isoformat()
        details = details or {}
        payload: dict[str, Any] = {
            "seq": seq,
            "timestamp": timestamp,
            "actor": actor,
            "action": action,
            "target": target,
            "details": details,
        }
        entry_hash = _compute_hash(prev, payload)
        entry = AuditEntry(
            seq=seq,
            timestamp=timestamp,
            actor=actor,
            action=action,
            target=target,
            details=details,
            prev_hash=prev,
            entry_hash=entry_hash,
        )
        self._entries.append(entry)
        return entry

    @property
    def entries(self) -> list[AuditEntry]:
        return list(self._entries)

    def verify(self) -> bool:
        """校验整条链：任何记录被改 / prev 链断裂 → False。"""
        prev = GENESIS_HASH
        for entry in self._entries:
            if entry.prev_hash != prev:
                return False
            if entry.entry_hash != _compute_hash(prev, _payload(entry.model_dump())):
                return False
            prev = entry.entry_hash
        return True


class PgAuditLog:
    """append-only 审计链的 PG 持久化实现（P-18：重启不丢，C-23：不可篡改）。

    与 AuditLog 接口一致（append/entries/verify），runtime 据 DATABASE_URL 二选一。
    并发安全：append 内用事务级 advisory lock 串行化，保证 seq 连续、哈希链不断裂
    （SELECT-then-INSERT 之间不被其他 append 插队）。表仅 INSERT，从不 UPDATE/DELETE。
    """

    # 同一把事务锁键，确保全平台 audit 追加互斥
    _LOCK_KEY = 0x4149_5345  # "AISE"

    def __init__(self, database_url: str, clock: Callable[[], datetime] = _default_clock) -> None:
        from aisecops.L12_core_support.db import get_pool

        self._pool = get_pool(database_url)
        self._clock = clock
        with self._pool.connection() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS audit_log ("
                "seq integer PRIMARY KEY, timestamp text, actor text, action text, "
                "target text, details text, prev_hash text, entry_hash text)"
            )

    def append(
        self,
        actor: str,
        action: str,
        target: str = "",
        details: dict[str, Any] | None = None,
    ) -> AuditEntry:
        details = details or {}
        timestamp = self._clock().isoformat()
        with self._pool.connection() as conn:
            # 事务级锁：序列化所有追加，避免并发下 seq/prev_hash 竞态
            conn.execute("SELECT pg_advisory_xact_lock(%s)", (self._LOCK_KEY,))
            row = conn.execute("SELECT seq, entry_hash FROM audit_log ORDER BY seq DESC LIMIT 1").fetchone()
            seq = (row[0] + 1) if row else 0
            prev = row[1] if row else GENESIS_HASH
            payload = {
                "seq": seq,
                "timestamp": timestamp,
                "actor": actor,
                "action": action,
                "target": target,
                "details": details,
            }
            entry_hash = _compute_hash(prev, payload)
            conn.execute(
                "INSERT INTO audit_log "
                "(seq, timestamp, actor, action, target, details, prev_hash, entry_hash) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    seq,
                    timestamp,
                    actor,
                    action,
                    target,
                    json.dumps(details, sort_keys=True, ensure_ascii=False),
                    prev,
                    entry_hash,
                ),
            )
        return AuditEntry(
            seq=seq,
            timestamp=timestamp,
            actor=actor,
            action=action,
            target=target,
            details=details,
            prev_hash=prev,
            entry_hash=entry_hash,
        )

    @property
    def entries(self) -> list[AuditEntry]:
        with self._pool.connection() as conn:
            rows = conn.execute(
                "SELECT seq, timestamp, actor, action, target, details, prev_hash, entry_hash "
                "FROM audit_log ORDER BY seq"
            ).fetchall()
        out: list[AuditEntry] = []
        for r in rows:
            out.append(
                AuditEntry(
                    seq=r[0],
                    timestamp=r[1],
                    actor=r[2],
                    action=r[3],
                    target=r[4],
                    details=json.loads(r[5]) if r[5] else {},
                    prev_hash=r[6],
                    entry_hash=r[7],
                )
            )
        return out

    def verify(self) -> bool:
        prev = GENESIS_HASH
        for entry in self.entries:
            if entry.prev_hash != prev:
                return False
            if entry.entry_hash != _compute_hash(prev, _payload(entry.model_dump())):
                return False
            prev = entry.entry_hash
        return True


def build_audit_log(database_url: str = "") -> AuditSink:
    """按 DATABASE_URL 选审计实现：有则 PG 持久化，无/连不上回退内存。"""
    if database_url:
        try:
            return PgAuditLog(database_url)
        except Exception:
            pass
    return AuditLog()
