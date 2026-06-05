"""L07 · 告警接入业务能力（ingest）—— 数据面入口的业务出口。

把原来散在 L01 表现层 router 里的"归一化 → 威胁情报匹配 → 降噪决策 → 入库"流水线
收敛成一个业务出口（修审查 #23：表现层不应编排数据面 L10→L08→L09 流水线）。

跨层（ADR-0008）：L07 是编排层，合法依赖 L08（match_iocs）。L10 归一化与 L09 入库走
**依赖注入**（组合根传入 normalize 可调用对象 + 仓储），L07 不静态 import L09/L10，
既复用闭环又不破坏依赖方向（DIP）。

混合架构（C-4）：归一化/指纹去重/抑制都是确定性算法，无 LLM，叙述定性才交给 L02 Agent。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

from aisecops.L08_analytics_engines import match_iocs


class _IocStore(Protocol):
    def all(self) -> list[Any]: ...
    def bump_hit(self, ioc_id: str) -> Any: ...


class _DedupEngine(Protocol):
    def evaluate(self, fields: dict[str, Any], recent: list[Any]) -> Any: ...


class _SuppStore(Protocol):
    def bump_hit(self, rule_id: str) -> Any: ...


class _AlertStore(Protocol):
    def recent(self, n: int) -> list[Any]: ...
    def add(self, fields: dict[str, Any]) -> Any: ...
    def bump(self, alert_id: str) -> Any: ...


class IngestService:
    """告警接入出口：一条原始告警进 → 归一化/降噪/入库后的结果出（带可解释 deduped 说明）。"""

    def __init__(
        self,
        normalize: Callable[[dict[str, Any]], dict[str, Any]],
        iocs: _IocStore,
        dedup: _DedupEngine,
        alerts: _AlertStore,
        supp_rules: _SuppStore,
    ) -> None:
        self._normalize = normalize
        self._iocs = iocs
        self._dedup = dedup
        self._alerts = alerts
        self._supp_rules = supp_rules

    def ingest(self, raw: dict[str, Any]) -> dict[str, Any]:
        """L10 归一化 → L08 威胁情报匹配/降噪 → L09 入库。返回带 deduped 说明的结果。"""
        fields = self._normalize(raw)
        # 威胁情报匹配：命中 IoC 即计数（前端据此标红）
        for ioc in match_iocs(fields, self._iocs.all()):
            self._iocs.bump_hit(ioc.id)
        decision = self._dedup.evaluate(fields, self._alerts.recent(500))
        if decision.action == "merge":
            merged = self._alerts.bump(decision.target_id)
            if merged is not None:
                return {
                    **merged.model_dump(),
                    "deduped": "merged",
                    "into": decision.target_id,
                    "reason": decision.reason,
                }
            decision.action = "new"  # 并入目标已不存在 → 退化为新建
        if decision.action == "suppress":
            self._supp_rules.bump_hit(decision.rule_id)
            fields.update(fingerprint=decision.fingerprint, suppressed=True, suppress_reason=decision.reason)
            alert = self._alerts.add(fields)
            return {**alert.model_dump(), "deduped": "suppressed", "reason": decision.reason}
        fields["fingerprint"] = decision.fingerprint
        alert = self._alerts.add(fields)
        return {**alert.model_dump(), "deduped": "new"}


def build_ingest_service(
    normalize: Callable[[dict[str, Any]], dict[str, Any]],
    iocs: _IocStore,
    dedup: _DedupEngine,
    alerts: _AlertStore,
    supp_rules: _SuppStore,
) -> IngestService:
    """组合根用：注入 L10 归一化 + L08/L09 仓储，得到接入出口。"""
    return IngestService(normalize, iocs, dedup, alerts, supp_rules)
