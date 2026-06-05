from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from aisecops.L08_analytics_engines import match_iocs
from aisecops.L09_data_platform.alert_store import alert_stats
from aisecops.L10_data_collection.ingest import normalize_alert

from ..runtime import rt

router = APIRouter()


class IngestIn(BaseModel):
    """告警入库入参（允许任意原始字段）。"""

    model_config = ConfigDict(extra="allow")


@router.post("/api/ingest/alert")
async def ingest_alert(body: IngestIn) -> dict[str, Any]:
    """L10 入库 → L08 降噪 → L09 告警库。

    入库前跑降噪：抑制规则命中 → 标记抑制入库；同指纹时间窗内 → 并入计数；
    否则新建。返回结果带 deduped 说明（可解释）。
    """
    fields = normalize_alert(body.model_dump())
    # 威胁情报匹配：命中 IoC 即给情报计数（标红在列表里动态体现）
    for ioc in match_iocs(fields, rt.iocs.all()):
        rt.iocs.bump_hit(ioc.id)
    decision = rt.dedup.evaluate(fields, rt.alerts.recent(500))
    if decision.action == "merge":
        merged = rt.alerts.bump(decision.target_id)
        if merged is not None:
            return {**merged.model_dump(), "deduped": "merged", "into": decision.target_id, "reason": decision.reason}
        # 并入目标已不存在 → 退化为新建
        decision.action = "new"
    if decision.action == "suppress":
        rt.supp_rules.bump_hit(decision.rule_id)
        fields.update(fingerprint=decision.fingerprint, suppressed=True, suppress_reason=decision.reason)
        alert = rt.alerts.add(fields)
        return {**alert.model_dump(), "deduped": "suppressed", "reason": decision.reason}
    fields["fingerprint"] = decision.fingerprint
    alert = rt.alerts.add(fields)
    return {**alert.model_dump(), "deduped": "new"}


@router.get("/api/alerts")
async def get_alerts(include_suppressed: bool = False) -> dict[str, Any]:
    """告警列表。默认只看未抑制（降噪后）；include_suppressed=true 看全量（可回溯）。

    每条附 ioc_hits（命中的威胁情报值），供前端标红。
    """
    alerts = rt.alerts.recent(200)
    if not include_suppressed:
        alerts = [a for a in alerts if not a.suppressed]
    iocs = rt.iocs.all()
    out = []
    for a in alerts[:50]:
        d = a.model_dump()
        d["ioc_hits"] = [i.value for i in match_iocs(d, iocs)]
        out.append(d)
    return {"alerts": out}


@router.get("/api/dedupe/stats")
async def get_dedupe_stats() -> dict[str, Any]:
    """降噪效果（真实可解释）：原始事件数 vs 降噪后留存 + 各级贡献 + 规则命中。"""
    alerts = rt.alerts.all()
    rows = len(alerts)
    merged_away = sum(max(0, a.count - 1) for a in alerts)  # 精确去重+时间窗归并折叠掉的
    suppressed_rows = sum(1 for a in alerts if a.suppressed)
    active = sum(1 for a in alerts if not a.suppressed)
    raw_total = merged_away + rows  # 进入入口的原始事件总数
    after = active  # 分析师实际要看的（降噪后）
    reduction = round((1 - after / raw_total) * 100) if raw_total else 0
    rules = rt.supp_rules.all()
    suppressed_recent = [
        {"id": a.id, "host": a.host, "title": a.title, "reason": a.suppress_reason}
        for a in rt.alerts.recent(200)
        if a.suppressed
    ][:20]
    return {
        "raw_total": raw_total,
        "after": after,
        "reduction_pct": reduction,
        "breakdown": {
            "exact_window_merged": merged_away,
            "suppressed": suppressed_rows,
        },
        "rules": [r.model_dump() for r in rules],
        "rules_total": len(rules),
        "rules_enabled": sum(1 for r in rules if r.enabled),
        "suppressed_recent": suppressed_recent,
    }


class RuleIn(BaseModel):
    """新建抑制规则。"""

    name: str
    kind: str = "keyword"  # host / source / keyword / ip
    pattern: str
    actor: str = "未知"


@router.post("/api/suppression-rules")
async def create_rule(body: RuleIn) -> dict[str, Any]:
    """新建抑制规则（即时生效，写审计）。"""
    if not body.name.strip() or not body.pattern.strip():
        raise HTTPException(status_code=400, detail="名称与匹配内容不能为空")
    if body.kind not in ("host", "source", "keyword", "ip"):
        raise HTTPException(status_code=400, detail="kind 须为 host/source/keyword/ip 之一")
    rule = rt.supp_rules.create(body.name.strip(), body.kind, body.pattern.strip())
    rt.ctx.audit.append(
        actor=body.actor,
        action="suppression_create",
        target=rule.id,
        details={"name": rule.name, "kind": rule.kind, "pattern": rule.pattern},
    )
    return rule.model_dump()


class RuleToggleIn(BaseModel):
    enabled: bool
    actor: str = "未知"


@router.put("/api/suppression-rules/{rule_id}")
async def toggle_rule(rule_id: str, body: RuleToggleIn) -> dict[str, Any]:
    """启用/停用抑制规则（即时生效，写审计）。"""
    rule = rt.supp_rules.set_enabled(rule_id, body.enabled)
    if rule is None:
        raise HTTPException(status_code=404, detail=f"规则 {rule_id} 不存在")
    rt.ctx.audit.append(
        actor=body.actor,
        action="suppression_toggle",
        target=rule_id,
        details={"enabled": body.enabled},
    )
    return rule.model_dump()


@router.delete("/api/suppression-rules/{rule_id}")
async def delete_rule(rule_id: str, actor: str = "未知") -> dict[str, Any]:
    """删除抑制规则（写审计）。"""
    removed = rt.supp_rules.remove(rule_id)
    if removed:
        rt.ctx.audit.append(actor=actor, action="suppression_delete", target=rule_id, details={})
    return {"status": "deleted" if removed else "not_found", "id": rule_id}


@router.get("/api/dashboard")
async def get_dashboard() -> dict[str, Any]:
    stats = alert_stats(rt.alerts)
    budget = rt.gateway.budget
    stats["spent_cny"] = round(budget.spent(), 4) if budget else 0.0
    stats["monthly_cap_cny"] = budget.monthly_cap_cny if budget else 0.0
    stats["triage_calls"] = len(rt.gateway.recorder.history)
    stats["hitl_pending"] = rt.tickets.pending_count()
    return stats
