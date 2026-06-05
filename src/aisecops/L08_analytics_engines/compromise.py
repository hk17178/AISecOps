"""L08 · 失陷研判（C-2 安全分析：多信号加权融合，hybrid / 非纯 LLM C-4）。

把确定性算法的产出（IoC 命中 / Kill Chain 推进深度 / UEBA 风险 / 攻击图枢纽度）按权重融合成
单台主机的失陷分（0-1）与等级，给出可解释理由。供调查/分诊把"像不像失陷"量化。
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class CompromiseVerdict(BaseModel):
    host: str
    score: float = 0.0  # 0-1
    level: str = "低"  # 低 / 中 / 高 / 危急
    signals: dict[str, float] = Field(default_factory=dict)
    reasons: list[str] = Field(default_factory=list)


def _level(score: float) -> str:
    if score >= 0.8:
        return "危急"
    if score >= 0.6:
        return "高"
    if score >= 0.35:
        return "中"
    return "低"


def compromise_judgment(
    host: str,
    *,
    ioc_hits: int = 0,
    kill_chain_depth: int = 0,
    ueba_risk: float = 0.0,
    pivot_degree: int = 0,
) -> CompromiseVerdict:
    """多信号加权 → 失陷分。各信号先归一化到 0-1 再加权。"""
    s_ioc = min(1.0, ioc_hits / 3.0)  # 命中 3 条 IoC 即满
    s_kc = min(1.0, kill_chain_depth / 7.0)  # 推进越深越危险
    s_ueba = max(0.0, min(1.0, ueba_risk))
    s_pivot = min(1.0, pivot_degree / 6.0)  # 度中心性越高越像跳板
    signals = {
        "ioc": round(s_ioc, 3),
        "kill_chain": round(s_kc, 3),
        "ueba": round(s_ueba, 3),
        "pivot": round(s_pivot, 3),
    }
    score = round(0.35 * s_ioc + 0.3 * s_kc + 0.2 * s_ueba + 0.15 * s_pivot, 3)

    reasons: list[str] = []
    if ioc_hits:
        reasons.append(f"命中威胁情报 {ioc_hits} 条")
    if kill_chain_depth >= 4:
        reasons.append(f"杀伤链已推进至第 {kill_chain_depth}/7 阶段")
    if s_ueba >= 0.6:
        reasons.append(f"实体行为高度异常(UEBA {s_ueba})")
    if pivot_degree >= 4:
        reasons.append(f"在攻击图中是高连接枢纽(度 {pivot_degree})")
    if not reasons:
        reasons.append("各信号均不显著")
    return CompromiseVerdict(host=host, score=score, level=_level(score), signals=signals, reasons=reasons)
