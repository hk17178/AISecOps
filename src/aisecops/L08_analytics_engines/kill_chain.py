"""L08 · Kill Chain 还原（C-2 安全分析算法，非 LLM / C-4）。

按 Lockheed Martin 七阶段，用确定性关键词规则把事件映射到杀伤链阶段，按时间排序还原
推进链，给出已触达阶段、最深推进（depth）、覆盖度。结果是结构化"骨架"，供 LLM 叙述
（C-24 有据可依），而非让 LLM 凭空编攻击链。
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

# 七阶段（自下而上推进越深越危险）
STAGES = ("侦察", "武器化", "投递", "利用", "安装", "命令控制", "目标行动")

# 阶段关键词规则（命中即归入该阶段；靠后的阶段优先匹配，体现"推进更深"）
_STAGE_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("目标行动", ("加密", "勒索", "exfil", "外泄", "删除卷影", "vssadmin", "破坏", "拖库")),
    ("命令控制", ("c2", "回连", "beacon", "外联", "command", "心跳", "dns 隧道")),
    ("安装", ("计划任务", "服务创建", "持久化", "schtasks", "run key", "启动项", "install")),
    ("利用", ("漏洞", "exploit", "提权", "privilege", "注入", "溢出", "横向", "psexec", "wmi")),
    ("投递", ("钓鱼", "附件", "下载", "phishing", "邮件", "宏", "payload 投递")),
    ("武器化", ("免杀", "打包", "weaponize", "生成载荷", "混淆")),
    ("侦察", ("扫描", "scan", "探测", "枚举", "recon", "端口", "暴力破解", "brute")),
]


class KillChainStep(BaseModel):
    """杀伤链上的一步。"""

    stage: str
    order: int  # 阶段在七阶段中的序号(0-6)
    event: str
    ts: str = ""


class KillChainResult(BaseModel):
    """Kill Chain 还原结果。"""

    stages_hit: list[str] = Field(default_factory=list)
    steps: list[KillChainStep] = Field(default_factory=list)
    depth: int = 0  # 最深推进阶段序号+1（0=无）
    coverage: float = 0.0  # 触达阶段数 / 7
    summary: str = ""


def _event_text(log: dict[str, Any]) -> str:
    parts = [str(log.get(k, "")) for k in ("event", "title", "message", "action", "cmd", "detail")]
    return " ".join(p for p in parts if p) or str(log)


def _stage_of(text: str) -> tuple[str, int] | None:
    low = text.lower()
    for stage, words in _STAGE_RULES:
        if any(w.lower() in low for w in words):
            return stage, STAGES.index(stage)
    return None


def reconstruct_kill_chain(logs: list[dict[str, Any]]) -> KillChainResult:
    """把日志映射到杀伤链阶段并按时间还原（确定性）。"""
    steps: list[KillChainStep] = []
    for log in logs:
        hit = _stage_of(_event_text(log))
        if hit is None:
            continue
        stage, order = hit
        steps.append(KillChainStep(stage=stage, order=order, event=_event_text(log)[:120], ts=str(log.get("time", ""))))
    steps.sort(key=lambda s: (s.ts, s.order))
    hit_orders = sorted({s.order for s in steps})
    stages_hit = [STAGES[o] for o in hit_orders]
    depth = (max(hit_orders) + 1) if hit_orders else 0
    coverage = round(len(hit_orders) / len(STAGES), 3)
    summary = (
        f"推进至「{STAGES[depth - 1]}」(第 {depth}/7 阶段)，触达 {len(stages_hit)} 个阶段"
        if depth
        else "未匹配到明确杀伤链阶段"
    )
    return KillChainResult(stages_hit=stages_hit, steps=steps, depth=depth, coverage=coverage, summary=summary)
