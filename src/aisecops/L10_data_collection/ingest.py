"""L10 · 告警入库归一化。

外部告警（SIEM/EDR/防火墙 webhook）字段五花八门，先归一化成画布字段，再入 L09 store。
机器入站属采集层 L10（不是 L01，见技术设计 §5.1 修订）。
"""

from __future__ import annotations

from typing import Any

# 严重度别名 → 画布四级
_SEVERITY = {
    "critical": "严重",
    "crit": "严重",
    "严重": "严重",
    "p1": "严重",
    "fatal": "严重",
    "high": "高",
    "高": "高",
    "p2": "高",
    "medium": "中",
    "med": "中",
    "中": "中",
    "p3": "中",
    "warning": "中",
    "warn": "中",
    "low": "低",
    "低": "低",
    "info": "低",
    "p4": "低",
}


def _norm_severity(value: Any) -> str:
    return _SEVERITY.get(str(value).strip().lower(), str(value))


def _first(raw: dict[str, Any], keys: list[str], default: str = "") -> str:
    for k in keys:
        if raw.get(k):
            return str(raw[k])
    return default


def normalize_alert(raw: dict[str, Any]) -> dict[str, Any]:
    """把任意来源的原始告警归一化为画布字段。"""
    return {
        "host": _first(raw, ["host", "hostname", "dest_host", "computer", "device"]),
        "source": _first(raw, ["source", "vendor", "product", "sensor"]),
        "severity": _norm_severity(raw.get("severity") or raw.get("level") or "中"),
        "title": _first(raw, ["title", "message", "name", "rule", "signature"], "(无标题)"),
    }
