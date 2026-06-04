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
from typing import Any

from pydantic import BaseModel, Field

GENESIS_HASH = "0" * 64


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
