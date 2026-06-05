"""L01 · 协作驾驶舱（Ops Cockpit，ADR-0012）。

只读总览：在办工单"指派给谁、进度、SLA 是否超时、按人负载"。让管理层一屏看清进展，
少打扰技术。聚合读 L02 工单仓储（薄读，ADR-0011 允许）；SLA 用同格式时间串比较（字典序=时序）。
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter

from ..runtime import rt

router = APIRouter()


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _age_hours(ts: str, now_dt: datetime) -> float:
    try:
        t = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        return round((now_dt - t).total_seconds() / 3600, 1)
    except (ValueError, TypeError):
        return 0.0


@router.get("/api/cockpit")
async def get_cockpit() -> dict[str, Any]:
    """在办工单看板 + 按人负载 + 超时预警 + 汇总。"""
    now_str = _now()
    now_dt = datetime.now(timezone.utc)
    tickets = rt.tickets.all()

    items: list[dict[str, Any]] = []
    by_assignee: dict[str, dict[str, int]] = {}
    overdue = 0
    for t in tickets:
        done = t.progress == "已完成"
        # 在办 = 未驳回 且 未完成（待审/已批准且进度未完成）
        if t.status == "已驳回" or done:
            continue
        is_overdue = bool(t.sla_due) and now_str > t.sla_due
        if is_overdue:
            overdue += 1
        who = t.assignee or "（未指派）"
        load = by_assignee.setdefault(who, {"open": 0, "overdue": 0})
        load["open"] += 1
        if is_overdue:
            load["overdue"] += 1
        items.append(
            {
                "id": t.id,
                "action": t.action,
                "target": t.target,
                "risk": t.risk,
                "status": t.status,
                "assignee": t.assignee,
                "progress": t.progress,
                "sla_due": t.sla_due,
                "overdue": is_overdue,
                "age_hours": _age_hours(t.ts, now_dt),
                "last_note": t.notes[-1]["text"] if t.notes else "",
            }
        )

    # 风险高 + 超时优先排前
    items.sort(key=lambda x: (not x["overdue"], x["risk"] != "高", -x["age_hours"]))
    counts = {
        "open": len(items),
        "pending_approval": rt.tickets.pending_count(),
        "in_progress": sum(1 for t in tickets if t.progress == "处理中"),
        "done": sum(1 for t in tickets if t.progress == "已完成"),
        "overdue": overdue,
        "events": rt.events.count(),
    }
    workload = [{"assignee": k, **v} for k, v in sorted(by_assignee.items(), key=lambda x: -x[1]["open"])]
    return {"items": items, "workload": workload, "counts": counts}
