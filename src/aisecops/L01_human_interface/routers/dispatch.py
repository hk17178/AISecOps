from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from aisecops.L02_agents import mask_url, match_dispatch_rules

from ..runtime import rt

router = APIRouter()


class ToggleIn(BaseModel):
    enabled: bool
    actor: str = "未知"


def _send_to_channel(channel_id: str, title: str, content: str) -> dict[str, Any] | None:
    """对一个渠道发送并记录。渠道不存在返回 None。"""
    ch = rt.channels.get(channel_id)
    if ch is None:
        return None
    ok, error, note = rt.notifier.send(ch.kind, ch.url, title, content)
    rec = rt.records.add(ch.name, ch.kind, title, "成功" if ok else "失败", note, error)
    return rec.model_dump()


@router.get("/api/channels")
async def get_channels() -> dict[str, Any]:
    """渠道列表（webhook 地址脱敏，不回明文）。"""
    return {
        "channels": [
            {
                "id": c.id,
                "name": c.name,
                "kind": c.kind,
                "url_masked": mask_url(c.url),
                "configured": bool(c.url),
                "enabled": c.enabled,
            }
            for c in rt.channels.all()
        ],
        "kinds": ["wechat", "dingtalk", "webhook"],
        "outbound_enabled": rt.settings.allow_outbound,
    }


class ChannelIn(BaseModel):
    name: str
    kind: str = "wechat"
    url: str = ""
    actor: str = "未知"


@router.post("/api/channels")
async def create_channel(body: ChannelIn) -> dict[str, Any]:
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="渠道名不能为空")
    if body.kind not in ("wechat", "dingtalk", "webhook"):
        raise HTTPException(status_code=400, detail="kind 须为 wechat/dingtalk/webhook")
    ch = rt.channels.create(body.name.strip(), body.kind, body.url.strip())
    rt.ctx.audit.append(
        actor=body.actor, action="channel_create", target=ch.id, details={"name": ch.name, "kind": ch.kind}
    )
    return {"id": ch.id, "name": ch.name, "kind": ch.kind, "configured": bool(ch.url), "enabled": ch.enabled}


@router.put("/api/channels/{channel_id}")
async def toggle_channel(channel_id: str, body: ToggleIn) -> dict[str, Any]:
    ch = rt.channels.set_enabled(channel_id, body.enabled)
    if ch is None:
        raise HTTPException(status_code=404, detail=f"渠道 {channel_id} 不存在")
    rt.ctx.audit.append(actor=body.actor, action="channel_toggle", target=channel_id, details={"enabled": body.enabled})
    return {"id": ch.id, "enabled": ch.enabled}


@router.delete("/api/channels/{channel_id}")
async def delete_channel(channel_id: str, actor: str = "未知") -> dict[str, Any]:
    removed = rt.channels.remove(channel_id)
    if removed:
        rt.ctx.audit.append(actor=actor, action="channel_delete", target=channel_id, details={})
    return {"status": "deleted" if removed else "not_found", "id": channel_id}


@router.post("/api/channels/{channel_id}/test")
async def test_channel(channel_id: str, actor: str = "未知") -> dict[str, Any]:
    """发一条测试消息（真发与否取决于出域开关；离线 stub 返回未真实出域）。"""
    rec = _send_to_channel(channel_id, "AISECOPS 测试通知", "这是一条连通性测试消息。")
    if rec is None:
        raise HTTPException(status_code=404, detail=f"渠道 {channel_id} 不存在")
    rt.ctx.audit.append(actor=actor, action="channel_test", target=channel_id, details={"status": rec["status"]})
    return rec


@router.get("/api/dispatch-rules")
async def get_dispatch_rules() -> dict[str, Any]:
    chans = {c.id: c.name for c in rt.channels.all()}
    return {
        "rules": [
            {**r.model_dump(), "channel_name": chans.get(r.channel_id, "（渠道已删）")} for r in rt.dispatch_rules.all()
        ]
    }


class DispatchRuleIn(BaseModel):
    name: str
    channel_id: str
    trigger_verdict: str = "真威胁"
    trigger_severity: str = ""
    trigger_keyword: str = ""
    actor: str = "未知"


@router.post("/api/dispatch-rules")
async def create_dispatch_rule(body: DispatchRuleIn) -> dict[str, Any]:
    if not body.name.strip() or not body.channel_id:
        raise HTTPException(status_code=400, detail="规则名与渠道不能为空")
    if rt.channels.get(body.channel_id) is None:
        raise HTTPException(status_code=400, detail=f"渠道 {body.channel_id} 不存在")
    r = rt.dispatch_rules.create(
        body.name.strip(), body.channel_id, body.trigger_verdict, body.trigger_severity, body.trigger_keyword
    )
    rt.ctx.audit.append(actor=body.actor, action="dispatch_rule_create", target=r.id, details={"name": r.name})
    return r.model_dump()


@router.put("/api/dispatch-rules/{rule_id}")
async def toggle_dispatch_rule(rule_id: str, body: ToggleIn) -> dict[str, Any]:
    r = rt.dispatch_rules.set_enabled(rule_id, body.enabled)
    if r is None:
        raise HTTPException(status_code=404, detail=f"规则 {rule_id} 不存在")
    rt.ctx.audit.append(
        actor=body.actor, action="dispatch_rule_toggle", target=rule_id, details={"enabled": body.enabled}
    )
    return r.model_dump()


@router.delete("/api/dispatch-rules/{rule_id}")
async def delete_dispatch_rule(rule_id: str, actor: str = "未知") -> dict[str, Any]:
    removed = rt.dispatch_rules.remove(rule_id)
    if removed:
        rt.ctx.audit.append(actor=actor, action="dispatch_rule_delete", target=rule_id, details={})
    return {"status": "deleted" if removed else "not_found", "id": rule_id}


@router.get("/api/dispatch/records")
async def get_dispatch_records() -> dict[str, Any]:
    return {"records": [r.model_dump() for r in rt.records.recent(50)]}


class DispatchRunIn(BaseModel):
    """对一条告警按外发规则分发。"""

    alert_id: str = ""
    actor: str = "未知"


@router.post("/api/dispatch/run")
async def dispatch_run(body: DispatchRunIn) -> dict[str, Any]:
    """按外发规则分发某条告警：命中规则 → 发到对应渠道 + 记录（命中即发）。"""
    alert = next((a for a in rt.alerts.recent(500) if a.id == body.alert_id), None)
    if alert is None:
        raise HTTPException(status_code=404, detail=f"告警 {body.alert_id} 不存在")
    fields = alert.model_dump()
    matched = match_dispatch_rules(fields, rt.dispatch_rules.all())
    sent = []
    title = f"[{alert.severity}] {alert.host} · {alert.title}"
    content = f"研判：{alert.verdict}（{alert.confidence}）来源：{alert.source}"
    for rule in matched:
        rec = _send_to_channel(rule.channel_id, title, content)
        if rec is not None:
            rt.dispatch_rules.bump_hit(rule.id)
            sent.append({"rule": rule.name, "record": rec})
    rt.ctx.audit.append(
        actor=body.actor,
        action="dispatch_run",
        target=body.alert_id,
        details={"matched": len(matched), "sent": len(sent)},
    )
    return {"matched": len(matched), "sent": sent}
