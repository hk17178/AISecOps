"""L08 · 告警关联引擎（事件聚类，§1.5 第一步）。

把零散告警按"同主机 / 同源IP / 时间邻近 / 共享 IoC"关联成候选「事件簇」，
供上层（L07 关联分析）喂给大模型出跨告警攻击链结论。

对标业界基线：SIEM 的 correlation / 攻击链关联（Kill Chain stitching）。这里先做
规则+图（并查集）的候选关联，是确定性、可解释的；大模型只在候选簇上做叙述与定性，
不负责"发现关联"本身（避免纯 LLM 关联的幻觉，C-4 混合架构）。
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from pydantic import BaseModel

from aisecops.L09_data_platform.alert_store import Alert

_TS_FMT = "%Y-%m-%d %H:%M:%S"
_IP_RE = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")


class Cluster(BaseModel):
    """一个候选事件簇。"""

    id: str
    alert_ids: list[str]
    hosts: list[str]
    shared_ips: list[str]
    reason: str
    size: int


def _parse_ts(ts: str) -> datetime | None:
    try:
        return datetime.strptime(ts, _TS_FMT).replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def _ips(a: Alert) -> set[str]:
    return set(_IP_RE.findall(f"{a.host} {a.title}"))


def _linked(a: Alert, b: Alert, window_secs: int) -> str:
    """两条告警是否可关联；返回关联原因（空串=不关联）。"""
    ta, tb = _parse_ts(a.ts), _parse_ts(b.ts)
    if ta is not None and tb is not None and abs((ta - tb).total_seconds()) > window_secs:
        return ""  # 超出时间邻近窗，不关联
    if a.host and a.host == b.host:
        return f"同主机 {a.host}"
    shared = _ips(a) & _ips(b)
    if shared:
        return f"共享 IP {', '.join(sorted(shared))}"
    return ""


class _UnionFind:
    def __init__(self, n: int) -> None:
        self.p = list(range(n))

    def find(self, x: int) -> int:
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a: int, b: int) -> None:
        self.p[self.find(a)] = self.find(b)


def correlate(alerts: list[Alert], window_secs: int = 1800, min_size: int = 2) -> list[Cluster]:
    """把告警聚成候选事件簇（只取 size>=min_size 的）。被抑制告警不参与。"""
    items = [a for a in alerts if not a.suppressed]
    n = len(items)
    uf = _UnionFind(n)
    reasons: dict[int, str] = {}
    for i in range(n):
        for j in range(i + 1, n):
            why = _linked(items[i], items[j], window_secs)
            if why:
                uf.union(i, j)
                reasons.setdefault(uf.find(i), why)

    groups: dict[int, list[int]] = {}
    for i in range(n):
        groups.setdefault(uf.find(i), []).append(i)

    clusters: list[Cluster] = []
    cid = 0
    for root, idxs in groups.items():
        if len(idxs) < min_size:
            continue
        cid += 1
        members = [items[k] for k in idxs]
        ips: set[str] = set()
        for m in members:
            ips |= _ips(m)
        clusters.append(
            Cluster(
                id=f"CL-{cid}",
                alert_ids=[m.id for m in members],
                hosts=sorted({m.host for m in members if m.host}),
                shared_ips=sorted(ips),
                reason=reasons.get(root, "时间邻近"),
                size=len(members),
            )
        )
    # 大簇优先
    clusters.sort(key=lambda c: c.size, reverse=True)
    return clusters
