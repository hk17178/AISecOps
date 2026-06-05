"""L08 · 分析引擎（AIOps 算法 + 安全分析算法）。

AIOps 半边：降噪(dedup) + 关联(correlation)。
安全分析半边(C-2)：kill_chain 还原 / attack_graph 图算法 / ueba 统计 / compromise 失陷研判。
均为确定性算法（C-4 混合：算法出结构，LLM 只叙述）。
"""

from .attack_graph import AttackGraph, GraphEdge, build_attack_graph
from .compromise import CompromiseVerdict, compromise_judgment
from .correlation import Cluster, correlate
from .kill_chain import STAGES, KillChainResult, KillChainStep, reconstruct_kill_chain
from .ueba import EntityRisk, ueba_score
from .intel import (
    IoC,
    IocStore,
    InMemoryIocStore,
    PgIocStore,
    build_ioc_store,
    match_iocs,
    seed_demo_iocs,
)
from .dedup import (
    DedupDecision,
    DedupEngine,
    InMemorySuppressionStore,
    PgSuppressionStore,
    SuppressionRule,
    SuppressionStore,
    build_suppression_store,
    fingerprint,
    rule_matches,
    seed_demo_rules,
)

__all__ = [
    "DedupEngine",
    "DedupDecision",
    "fingerprint",
    "rule_matches",
    "SuppressionRule",
    "SuppressionStore",
    "InMemorySuppressionStore",
    "PgSuppressionStore",
    "build_suppression_store",
    "seed_demo_rules",
    "Cluster",
    "correlate",
    "reconstruct_kill_chain",
    "KillChainResult",
    "KillChainStep",
    "STAGES",
    "build_attack_graph",
    "AttackGraph",
    "GraphEdge",
    "ueba_score",
    "EntityRisk",
    "compromise_judgment",
    "CompromiseVerdict",
    "IoC",
    "IocStore",
    "InMemoryIocStore",
    "PgIocStore",
    "build_ioc_store",
    "match_iocs",
    "seed_demo_iocs",
]
