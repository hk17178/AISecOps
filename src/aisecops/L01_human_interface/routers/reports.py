from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from aisecops.L02_agents import Principal
from aisecops.L09_data_platform.alert_store import alert_stats

from ..auth_deps import WRITE, require_role
from ..runtime import rt

router = APIRouter()


def _collect_report_data(kind: str, event_id: str = "") -> dict[str, Any]:
    """从各真实 store 汇总报告数据（确定性，不编造）。"""
    all_alerts = rt.alerts.all()
    rows = len(all_alerts)
    merged_away = sum(max(0, a.count - 1) for a in all_alerts)
    active = [a for a in all_alerts if not a.suppressed]
    raw_total = merged_away + rows
    reduction = round((1 - len(active) / raw_total) * 100) if raw_total else 0
    stats = alert_stats(rt.alerts)
    budget = rt.gateway.budget
    now = datetime.now(timezone.utc)
    top = [a.model_dump() for a in rt.alerts.recent(200) if a.verdict == "真威胁" and not a.suppressed][:5]
    data: dict[str, Any] = {
        "date": now.strftime("%Y-%m-%d"),
        "generated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "alerts_total": stats["total"],
        "threats": stats["threats"],
        "pending": stats["pending"],
        "dedupe_reduction": reduction,
        "events": rt.events.count(),
        "tickets_pending": rt.tickets.pending_count(),
        "dispatch_sent": sum(1 for r in rt.records.recent(500) if r.status == "成功"),
        "cost_spent": round(budget.spent(), 4) if budget else 0.0,
        "by_severity": stats["by_severity"],
        "by_source": stats["by_source"],
        "top_threats": top,
    }
    if kind == "incident" and event_id:
        ev = next((e for e in rt.events.all() if e.id == event_id), None)
        if ev is not None:
            data["incident"] = ev.model_dump()
            data["date"] = ev.title
    return data


class ReportGenIn(BaseModel):
    """生成报告：kind=daily/weekly/incident；incident 需 event_id。"""

    kind: str = "daily"
    event_id: str = ""
    actor: str = "未知"


@router.post("/api/reports/generate")
async def generate_report(body: ReportGenIn, principal: Principal = Depends(require_role(*WRITE))) -> dict[str, Any]:
    """按模板从真实数据生成报告（执行摘要走 L07/report 强模型，离线诚实降级）。"""
    if body.kind not in ("daily", "weekly", "incident"):
        raise HTTPException(status_code=400, detail="kind 须为 daily/weekly/incident")
    data = _collect_report_data(body.kind, body.event_id)
    title, markdown, summary = await rt.reporting.generate(body.kind, data)
    rep = rt.reports.create(body.kind, title, markdown, summary)
    rt.ctx.audit.append(
        actor=principal.username, action="report_generate", target=rep.id, details={"kind": body.kind, "title": title}
    )
    return rep.full()


@router.get("/api/reports")
async def list_reports() -> dict[str, Any]:
    return {"reports": [r.meta() for r in rt.reports.all()]}


@router.get("/api/reports/{report_id}")
async def get_report(report_id: str) -> dict[str, Any]:
    rep = rt.reports.get(report_id)
    if rep is None:
        raise HTTPException(status_code=404, detail=f"报告 {report_id} 不存在")
    return rep.full()


@router.get("/api/reports/{report_id}/export")
async def export_report(report_id: str) -> Response:
    """导出 Markdown 文件（下载）。"""
    rep = rt.reports.get(report_id)
    if rep is None:
        raise HTTPException(status_code=404, detail=f"报告 {report_id} 不存在")
    filename = f"{rep.id}.md"
    return Response(
        content=rep.markdown,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
