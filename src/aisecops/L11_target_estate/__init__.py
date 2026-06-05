"""L11 · 被监测资产域（Target Estate）。

资产 CMDB（手填，分诊富化引用重要度）+ AI 资产合规 / Shadow AI 治理（C-3）。
"""

from .ai_compliance import (
    AiAsset,
    AiAssetStore,
    ComplianceFinding,
    InMemoryAiAssetStore,
    PgAiAssetStore,
    build_ai_asset_store,
    check_compliance,
    discover_shadow_ai,
    seed_demo_ai_assets,
)
from .asset_store import (
    Asset,
    AssetStore,
    InMemoryAssetStore,
    PgAssetStore,
    build_asset_store,
    seed_demo_assets,
)

__all__ = [
    "Asset",
    "AssetStore",
    "InMemoryAssetStore",
    "PgAssetStore",
    "build_asset_store",
    "seed_demo_assets",
    "AiAsset",
    "AiAssetStore",
    "InMemoryAiAssetStore",
    "PgAiAssetStore",
    "build_ai_asset_store",
    "ComplianceFinding",
    "check_compliance",
    "discover_shadow_ai",
    "seed_demo_ai_assets",
]
