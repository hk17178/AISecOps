"""L08 · UEBA 行为分析（C-2 安全分析：统计算法，非 LLM / C-4）。

对实体（用户/主机）做行为基线 + 统计异常评分：抽取行为特征（活动量、非工作时间占比、
失败登录、接触面），用 z-score 衡量个体相对群体的偏离，融合成 0-1 风险分。纯统计，
可解释、可复现。
"""

from __future__ import annotations

import math
import re
from typing import Any

from pydantic import BaseModel, Field

_HOUR = re.compile(r"\b(\d{1,2}):\d{2}")


class EntityRisk(BaseModel):
    entity: str
    kind: str = "user"  # user / host
    event_count: int = 0
    off_hours: int = 0  # 非工作时间(9-18 外)事件数
    failed_logins: int = 0
    distinct_peers: int = 0  # 接触的不同对端数
    risk: float = 0.0  # 0-1
    reasons: list[str] = Field(default_factory=list)


def _hour_of(log: dict[str, Any]) -> int | None:
    m = _HOUR.search(str(log.get("time", "")))
    if not m:
        return None
    h = int(m.group(1))
    return h if 0 <= h <= 23 else None


def _zscores(values: list[float]) -> list[float]:
    n = len(values)
    if n == 0:
        return []
    mean = sum(values) / n
    var = sum((v - mean) ** 2 for v in values) / n
    std = math.sqrt(var)
    if std == 0:
        return [0.0] * n
    return [(v - mean) / std for v in values]


def ueba_score(logs: list[dict[str, Any]]) -> list[EntityRisk]:
    """按用户聚合行为特征，z-score 融合成风险分（降序）。"""
    feats: dict[str, EntityRisk] = {}
    peers: dict[str, set[str]] = {}
    for log in logs:
        user = str(log.get("user", "") or log.get("account", ""))
        if not user:
            continue
        er = feats.setdefault(user, EntityRisk(entity=user, kind="user"))
        peers.setdefault(user, set())
        er.event_count += 1
        hour = _hour_of(log)
        if hour is not None and not (9 <= hour < 18):
            er.off_hours += 1
        text = f"{log.get('event', '')} {log.get('title', '')}".lower()
        is_login = "login" in text or "登录" in text
        is_fail = any(w in text for w in ("失败", "failed", "denied", "拒绝"))
        if is_login and is_fail:
            er.failed_logins += 1
        host = str(log.get("host", "") or log.get("dst_ip", ""))
        if host:
            peers[user].add(host)
    for user, er in feats.items():
        er.distinct_peers = len(peers[user])

    entities = list(feats.values())
    if not entities:
        return []
    # 各特征 z-score → 取正向偏离加权融合 → sigmoid 压到 0-1
    z_off = _zscores([e.off_hours for e in entities])
    z_fail = _zscores([float(e.failed_logins) for e in entities])
    z_peer = _zscores([float(e.distinct_peers) for e in entities])
    z_cnt = _zscores([float(e.event_count) for e in entities])
    for i, er in enumerate(entities):
        raw = 0.35 * z_fail[i] + 0.3 * z_off[i] + 0.2 * z_peer[i] + 0.15 * z_cnt[i]
        er.risk = round(1 / (1 + math.exp(-raw)), 3)
        if z_fail[i] >= 1.0 and er.failed_logins:
            er.reasons.append(f"失败登录显著偏高({er.failed_logins})")
        if z_off[i] >= 1.0 and er.off_hours:
            er.reasons.append(f"非工作时间活动偏高({er.off_hours})")
        if z_peer[i] >= 1.0 and er.distinct_peers > 1:
            er.reasons.append(f"接触面异常宽({er.distinct_peers} 个对端)")
    entities.sort(key=lambda e: -e.risk)
    return entities
