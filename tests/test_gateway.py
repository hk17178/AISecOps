"""L05 LLM Gateway 测试 —— 全 stub，不联网、不烧 token（C-18）。

覆盖：基本调用 / 可复现(C-30) / 元数据(C-33) / 降级(C-34) / 预算(自用关键)。
"""

from datetime import datetime, timezone

import pytest

from aisecops.L05_gateway.llm_gateway import (
    BudgetExceeded,
    BudgetTracker,
    GatewayError,
    LLMGateway,
    MetadataRecorder,
    StubProvider,
)


async def test_call_returns_structured_response() -> None:
    gw = LLMGateway([StubProvider()])
    resp = await gw.call("检测到横向移动", scenario="L07/alert_triage")
    assert resp.content.startswith("[stub:L07/alert_triage]")
    assert resp.metadata.scenario == "L07/alert_triage"
    assert resp.metadata.stub is True
    assert resp.metadata.total_tokens > 0


async def test_reproducible_with_same_input() -> None:
    """temperature=0 + 相同输入 → 相同输出（C-30 可复现）。"""
    gw = LLMGateway([StubProvider()])
    r1 = await gw.call("same input", scenario="t", temperature=0, seed=42)
    r2 = await gw.call("same input", scenario="t", temperature=0, seed=42)
    assert r1.content == r2.content


async def test_metadata_recorded() -> None:
    """每次调用必产 metadata 并被记录（C-33）。"""
    recorder = MetadataRecorder()
    gw = LLMGateway([StubProvider()], recorder=recorder)
    await gw.call("x", scenario="t")
    assert len(recorder.history) == 1
    assert recorder.history[0].provider == "stub"


async def test_fallback_to_backup_provider() -> None:
    """主 provider 失败 → 自动降级到备用（C-34）。"""
    gw = LLMGateway([StubProvider(model="primary", fail=True), StubProvider(model="backup")])
    resp = await gw.call("x", scenario="t")
    assert resp.metadata.fallback_used is True
    assert resp.metadata.model == "backup"


async def test_all_providers_fail_raises() -> None:
    gw = LLMGateway([StubProvider(fail=True), StubProvider(fail=True)])
    with pytest.raises(GatewayError):
        await gw.call("x", scenario="t")


async def test_budget_blocks_when_exceeded() -> None:
    """超月度预算后，后续调用被预算闸门拦截（自用关键）。"""
    fixed_clock = lambda: datetime(2026, 6, 1, tzinfo=timezone.utc)  # noqa: E731
    budget = BudgetTracker(monthly_cap_cny=0.01, clock=fixed_clock)
    # price 很高 → 一次调用就花掉远超上限的钱
    gw = LLMGateway([StubProvider(price_per_1k_cny=100.0)], budget=budget)

    first = await gw.call("x" * 400, scenario="t")  # 第一次放行
    assert first.metadata.cost_cny > 0.01
    with pytest.raises(BudgetExceeded):
        await gw.call("y", scenario="t")  # 第二次被拦


def test_budget_tracker_unit() -> None:
    fixed_clock = lambda: datetime(2026, 6, 15, tzinfo=timezone.utc)  # noqa: E731
    budget = BudgetTracker(monthly_cap_cny=1.0, clock=fixed_clock)
    assert budget.remaining() == 1.0
    budget.record(0.4)
    assert abs(budget.spent() - 0.4) < 1e-9
    assert abs(budget.remaining() - 0.6) < 1e-9
    budget.check()  # 未超，不抛
    budget.record(0.7)
    with pytest.raises(BudgetExceeded):
        budget.check()
