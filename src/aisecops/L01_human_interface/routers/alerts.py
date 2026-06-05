from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict

from aisecops.L02_agents import Principal
from aisecops.L08_analytics_engines import match_iocs
from aisecops.L09_data_platform.alert_store import alert_stats, dedupe_stats

from ..auth_deps import WRITE, require_role
from ..runtime import rt

router = APIRouter()


class IngestIn(BaseModel):
    """告警入库入参（允许任意原始字段）。"""

    model_config = ConfigDict(extra="allow")


@router.post("/api/ingest/alert")
async def ingest_alert(body: IngestIn, _: Principal = Depends(require_role(*WRITE))) -> dict[str, Any]:
    """告警接入：归一化 → 威胁情报匹配 → 降噪 → 入库。

    流水线已下沉到 L07 IngestService（审查 #23：表现层不编排数据面），这里只调出口。
    """
    return rt.ingest.ingest(body.model_dump())


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
    """降噪效果（真实可解释）：降噪口径走 L09 dedupe_stats 单一事实源 + 规则命中明细。"""
    stats = dedupe_stats(rt.alerts)  # 口径与报表中心一致（审查 #24）
    rules = rt.supp_rules.all()
    suppressed_recent = [
        {"id": a.id, "host": a.host, "title": a.title, "reason": a.suppress_reason}
        for a in rt.alerts.recent(200)
        if a.suppressed
    ][:20]
    return {
        **stats,
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
async def create_rule(body: RuleIn, principal: Principal = Depends(require_role(*WRITE))) -> dict[str, Any]:
    """新建抑制规则（即时生效，写审计）。"""
    if not body.name.strip() or not body.pattern.strip():
        raise HTTPException(status_code=400, detail="名称与匹配内容不能为空")
    if body.kind not in ("host", "source", "keyword", "ip"):
        raise HTTPException(status_code=400, detail="kind 须为 host/source/keyword/ip 之一")
    rule = rt.supp_rules.create(body.name.strip(), body.kind, body.pattern.strip())
    rt.ctx.audit.append(
        actor=principal.username,
        action="suppression_create",
        target=rule.id,
        details={"name": rule.name, "kind": rule.kind, "pattern": rule.pattern},
    )
    return rule.model_dump()


class RuleToggleIn(BaseModel):
    enabled: bool
    actor: str = "未知"


@router.put("/api/suppression-rules/{rule_id}")
async def toggle_rule(
    rule_id: str, body: RuleToggleIn, principal: Principal = Depends(require_role(*WRITE))
) -> dict[str, Any]:
    """启用/停用抑制规则（即时生效，写审计）。"""
    rule = rt.supp_rules.set_enabled(rule_id, body.enabled)
    if rule is None:
        raise HTTPException(status_code=404, detail=f"规则 {rule_id} 不存在")
    rt.ctx.audit.append(
        actor=principal.username,
        action="suppression_toggle",
        target=rule_id,
        details={"enabled": body.enabled},
    )
    return rule.model_dump()


@router.delete("/api/suppression-rules/{rule_id}")
async def delete_rule(rule_id: str, principal: Principal = Depends(require_role(*WRITE))) -> dict[str, Any]:
    """删除抑制规则（写审计）。"""
    removed = rt.supp_rules.remove(rule_id)
    if removed:
        rt.ctx.audit.append(actor=principal.username, action="suppression_delete", target=rule_id, details={})
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
