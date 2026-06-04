"""L08 · 分析引擎（AIOps 算法 + 安全分析算法）。

当前：告警降噪引擎（dedup，分诊前置）。关联引擎（correlation）随 §1.5 落地。
"""

from .correlation import Cluster, correlate
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
]
