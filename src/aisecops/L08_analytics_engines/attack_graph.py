"""L08 · 攻击图（C-2 安全分析：≥1 图算法）。

从事件构建有向图（节点=实体 主机/账号/IP，边=观察到的交互），跑真实图算法：
- **度中心性**找枢纽节点（pivot，攻击者落脚/跳板）；
- **BFS 路径搜索**从入口节点到关键资产，还原可达攻击路径。
确定性、非 LLM（C-4）。供调查时定位"谁是跳板、打到了哪"。
"""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any

from pydantic import BaseModel, Field


class GraphEdge(BaseModel):
    src: str
    dst: str
    kind: str = ""  # 访问 / 网络 / 外联
    count: int = 1


class AttackGraph(BaseModel):
    nodes: list[str] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
    pivots: list[dict[str, Any]] = Field(default_factory=list)  # [{node, degree}]，度中心性 Top
    paths: list[list[str]] = Field(default_factory=list)  # 入口→关键资产的可达路径


def _entities(log: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(log.get("user", "") or log.get("account", "")),
        str(log.get("host", "") or log.get("dst_host", "")),
        str(log.get("src_ip", "") or log.get("src", "")),
        str(log.get("dst_ip", "") or log.get("dst", "")),
    )


def build_attack_graph(logs: list[dict[str, Any]], critical: set[str] | None = None) -> AttackGraph:
    """构图 + 度中心性 + BFS 路径搜索。critical 为关键资产节点集合（路径目标）。"""
    critical = critical or set()
    agg: dict[tuple[str, str, str], int] = defaultdict(int)
    for log in logs:
        user, host, src_ip, dst_ip = _entities(log)
        if user and host:
            agg[(user, host, "访问")] += 1
        if src_ip and dst_ip:
            agg[(src_ip, dst_ip, "网络")] += 1
        if host and dst_ip and dst_ip != host:
            agg[(host, dst_ip, "外联")] += 1

    edges = [GraphEdge(src=s, dst=d, kind=k, count=c) for (s, d, k), c in agg.items()]
    adj: dict[str, list[str]] = defaultdict(list)
    degree: dict[str, int] = defaultdict(int)
    indeg: dict[str, int] = defaultdict(int)
    nodes: set[str] = set()
    for e in edges:
        adj[e.src].append(e.dst)
        degree[e.src] += 1
        degree[e.dst] += 1
        indeg[e.dst] += 1
        nodes.update((e.src, e.dst))

    pivots = [{"node": n, "degree": degree[n]} for n in sorted(nodes, key=lambda x: -degree[x])[:5]]

    # 入口节点：入度为 0（最初发起方）。BFS 找到关键资产的简单路径
    entries = [n for n in nodes if indeg[n] == 0] or list(nodes)[:3]
    targets = critical & nodes
    paths: list[list[str]] = []
    if targets:
        for entry in entries:
            paths.extend(_bfs_paths(adj, entry, targets, max_depth=6, max_paths=3))
    return AttackGraph(nodes=sorted(nodes), edges=edges, pivots=pivots, paths=paths[:5])


def _bfs_paths(
    adj: dict[str, list[str]], start: str, targets: set[str], max_depth: int, max_paths: int
) -> list[list[str]]:
    """BFS 搜索 start 到任一 target 的简单路径（去环、限深、限条数）。"""
    out: list[list[str]] = []
    queue: deque[list[str]] = deque([[start]])
    while queue and len(out) < max_paths:
        path = queue.popleft()
        if len(path) > max_depth:
            continue
        last = path[-1]
        if last in targets and len(path) > 1:
            out.append(path)
            continue
        for nxt in adj.get(last, []):
            if nxt not in path:  # 去环
                queue.append([*path, nxt])
    return out
