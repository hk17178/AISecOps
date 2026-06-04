"""L11 · 被监测资产域（Target Estate）。

当前：资产 CMDB（手填，分诊富化引用重要度）。
"""

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
]
