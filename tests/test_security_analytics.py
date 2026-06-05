"""L08 安全分析半边（C-2）：kill_chain / attack_graph(图算法) / ueba(统计) / compromise。"""

from __future__ import annotations

from aisecops.L08_analytics_engines import (
    build_attack_graph,
    compromise_judgment,
    reconstruct_kill_chain,
    ueba_score,
)


def test_kill_chain_reconstructs_and_orders_by_stage() -> None:
    logs = [
        {"time": "2026-06-04 09:00", "event": "对外端口扫描 scan"},
        {"time": "2026-06-04 10:00", "event": "钓鱼邮件附件投递"},
        {"time": "2026-06-04 11:00", "event": "漏洞利用提权 横向移动 psexec"},
        {"time": "2026-06-04 12:00", "event": "vssadmin 删除卷影 文件加密 勒索"},
    ]
    kc = reconstruct_kill_chain(logs)
    assert "侦察" in kc.stages_hit and "目标行动" in kc.stages_hit
    assert kc.depth == 7  # 推进到最后阶段
    assert kc.coverage > 0.5
    assert kc.steps[0].order <= kc.steps[-1].order  # 按阶段/时间有序


def test_attack_graph_pivots_and_reachable_path() -> None:
    # a → b → CROWN(关键资产)，b 应是高度枢纽，且有可达路径
    logs = [
        {"src_ip": "1.1.1.1", "dst_ip": "10.0.0.5"},  # 外部 → 跳板
        {"src_ip": "10.0.0.5", "dst_ip": "10.0.0.9"},  # 跳板 → 其它
        {"src_ip": "10.0.0.5", "dst_ip": "CROWN"},  # 跳板 → 关键资产
    ]
    g = build_attack_graph(logs, critical={"CROWN"})
    assert g.pivots and g.pivots[0]["node"] == "10.0.0.5"  # 度中心性最高
    assert any(p[-1] == "CROWN" and "10.0.0.5" in p for p in g.paths)  # 还原出可达路径


def test_ueba_flags_statistical_anomaly() -> None:
    # 一个用户大量非工作时间 + 失败登录，应被 z-score 评为最高风险
    logs = []
    for _ in range(8):
        logs.append({"user": "normal", "time": "2026-06-04 10:00", "event": "登录成功", "host": "h1"})
    for i in range(6):
        logs.append({"user": "evil", "time": "2026-06-04 03:00", "event": "登录失败 failed", "host": f"h{i}"})
    risks = ueba_score(logs)
    assert risks[0].entity == "evil"
    assert risks[0].risk > 0.5
    assert risks[0].reasons  # 有可解释理由


def test_compromise_judgment_weighting_and_level() -> None:
    high = compromise_judgment("h1", ioc_hits=3, kill_chain_depth=7, ueba_risk=0.9, pivot_degree=6)
    low = compromise_judgment("h2", ioc_hits=0, kill_chain_depth=0, ueba_risk=0.0, pivot_degree=0)
    assert high.score > low.score
    assert high.level in ("高", "危急") and low.level == "低"
    assert 0.0 <= high.score <= 1.0
