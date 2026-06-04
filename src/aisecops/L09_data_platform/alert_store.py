"""L09 · 告警存储（平台自有衍生数据）。

源无关：接口稳定，默认内存实现；将来换 PG（pgvector，见 ADR-0004 O2）不改调用方。
告警是"我方衍生数据"（非原始日志，原始日志在 ES，见 ADR-0009）。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel


class Alert(BaseModel):
    """一条告警。"""

    id: str
    ts: str
    host: str = ""
    source: str = ""
    severity: str = "中"  # 严重 / 高 / 中 / 低
    title: str = ""
    verdict: str = "新"  # 新 / 真威胁 / 待研判 / 误报
    confidence: float = 0.0


class AlertStore(ABC):
    """告警存储接口。"""

    @abstractmethod
    def add(self, fields: dict[str, Any]) -> Alert:
        """新增一条告警（自动分配 id / ts）。"""
        raise NotImplementedError

    @abstractmethod
    def recent(self, limit: int = 50) -> list[Alert]:
        """最近的若干条（倒序）。"""
        raise NotImplementedError

    @abstractmethod
    def all(self) -> list[Alert]:
        raise NotImplementedError

    @abstractmethod
    def count(self) -> int:
        raise NotImplementedError


def _default_clock() -> datetime:
    return datetime.now(timezone.utc)


class InMemoryAlertStore(AlertStore):
    """默认内存实现（进程内）。生产换 PG。"""

    def __init__(self, clock: Callable[[], datetime] = _default_clock) -> None:
        self._alerts: list[Alert] = []
        self._clock = clock

    def add(self, fields: dict[str, Any]) -> Alert:
        seq = len(self._alerts) + 1
        alert = Alert(
            id=str(fields.get("id") or f"ALERT-{seq:04d}"),
            ts=str(fields.get("ts") or self._clock().strftime("%Y-%m-%d %H:%M:%S")),
            host=str(fields.get("host", "")),
            source=str(fields.get("source", "")),
            severity=str(fields.get("severity", "中")),
            title=str(fields.get("title", "")),
            verdict=str(fields.get("verdict", "新")),
            confidence=float(fields.get("confidence", 0.0)),
        )
        self._alerts.append(alert)
        return alert

    def recent(self, limit: int = 50) -> list[Alert]:
        return list(reversed(self._alerts))[:limit]

    def all(self) -> list[Alert]:
        return list(self._alerts)

    def count(self) -> int:
        return len(self._alerts)


def alert_stats(store: AlertStore) -> dict[str, Any]:
    """聚合统计，给仪表盘用。"""
    alerts = store.all()
    by_severity: dict[str, int] = {}
    by_source: dict[str, int] = {}
    threats = 0
    pending = 0
    for a in alerts:
        by_severity[a.severity] = by_severity.get(a.severity, 0) + 1
        if a.source:
            by_source[a.source] = by_source.get(a.source, 0) + 1
        if a.verdict == "真威胁":
            threats += 1
        if a.verdict in ("新", "待研判"):
            pending += 1
    return {
        "total": len(alerts),
        "threats": threats,
        "pending": pending,
        "by_severity": by_severity,
        "by_source": by_source,
        "recent": [a.model_dump() for a in store.recent(8)],
    }


def seed_demo_alerts(store: AlertStore) -> None:
    """放一批演示样例进真 store（仅初始数据是样例，存储/聚合都是真）。"""
    samples: list[dict[str, Any]] = [
        {
            "host": "WIN-APP-07",
            "source": "EDR",
            "severity": "严重",
            "title": "检测到横向移动 (PsExec)",
            "verdict": "真威胁",
            "confidence": 0.94,
        },
        {
            "host": "DEV-12",
            "source": "防火墙",
            "severity": "中",
            "title": "出站连接到已知 C2 域名",
            "verdict": "真威胁",
            "confidence": 0.88,
        },
        {
            "host": "corp-mail",
            "source": "SIEM",
            "severity": "高",
            "title": "境外 IP 多次失败后登录成功",
            "verdict": "待研判",
            "confidence": 0.61,
        },
        {
            "host": "DEV-03",
            "source": "Syslog",
            "severity": "低",
            "title": "sudo 提权频次异常",
            "verdict": "误报",
            "confidence": 0.27,
        },
        {
            "host": "NDR-sensor",
            "source": "NDR",
            "severity": "高",
            "title": "DNS 隧道疑似数据外泄",
            "verdict": "待研判",
            "confidence": 0.55,
        },
        {
            "host": "WIN-APP-07",
            "source": "EDR",
            "severity": "严重",
            "title": "凭证 svc_backup 非常规登录",
            "verdict": "真威胁",
            "confidence": 0.9,
        },
    ]
    for s in samples:
        store.add(s)
