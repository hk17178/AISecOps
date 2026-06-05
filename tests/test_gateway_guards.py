"""L05 Gateway 治理/抗幻觉测试 —— S7 出域脱敏 / S8 schema / S9 cross-check。"""

import pytest
from pydantic import BaseModel

from aisecops.L05_gateway.llm_gateway import (
    LLMGateway,
    LLMRequest,
    SchemaValidationError,
    StubProvider,
    TokenUsage,
)


class OutboundCapture(StubProvider):
    """假装出域的 provider，记录它实际收到的内容（验证脱敏）。"""

    name = "outbound_cap"
    outbound = True

    def __init__(self) -> None:
        super().__init__(model="cap")
        self.seen: str | None = None

    async def complete(self, request: LLMRequest) -> tuple[str, TokenUsage]:
        self.seen = request.messages[-1].content
        return await super().complete(request)


class BadProvider(StubProvider):
    """模拟真 provider（is_stub=False），用于测真 provider 的 schema 严格校验。"""

    name = "bad"
    is_stub = False


class Verdict(BaseModel):
    verdict: str
    confidence: float


# ---- S7 出域开关 + 脱敏（C-32）----


async def test_outbound_blocked_when_switch_off() -> None:
    cap = OutboundCapture()
    gw = LLMGateway([cap, StubProvider()], outbound_enabled=False)
    resp = await gw.call("登录来自 1.2.3.4", scenario="t")
    # 出域 provider 被跳过，落到本地 stub
    assert resp.metadata.provider == "stub"
    assert cap.seen is None


async def test_outbound_used_and_desensitized_when_switch_on() -> None:
    cap = OutboundCapture()
    gw = LLMGateway([cap, StubProvider()], outbound_enabled=True)
    resp = await gw.call("登录 ip 1.2.3.4 邮箱 a@b.com", scenario="t")
    assert resp.metadata.provider == "outbound_cap"
    assert resp.metadata.outbound is True
    assert resp.metadata.desensitized is True
    # provider 实际收到的内容已脱敏
    assert cap.seen is not None
    assert "1.2.3.4" not in cap.seen and "<IP>" in cap.seen
    assert "a@b.com" not in cap.seen


# ---- S8 schema 校验（C-21）----


async def test_schema_validation_ok() -> None:
    stub = StubProvider(canned='{"verdict":"真威胁","confidence":0.94}')
    gw = LLMGateway([stub])
    resp = await gw.call("x", scenario="t", response_model=Verdict)
    assert resp.parsed.verdict == "真威胁"
    assert resp.parsed.confidence == 0.94


async def test_schema_validation_fail_raises_for_real_provider() -> None:
    # 真 provider(非 stub) 输出非 JSON → 严格 raise（C-21）
    gw = LLMGateway([BadProvider(canned="这不是 JSON")])
    with pytest.raises(SchemaValidationError):
        await gw.call("x", scenario="t", response_model=Verdict)


async def test_stub_fills_placeholder_offline() -> None:
    # 离线 stub(回显非 JSON) + response_model → 填零值占位，不报错
    gw = LLMGateway([StubProvider()])
    resp = await gw.call("x", scenario="t", response_model=Verdict)
    assert resp.parsed is not None
    assert resp.parsed.confidence == 0.0


# ---- S9 双模型 cross-check（C-27）----


async def test_cross_check_agree() -> None:
    gw = LLMGateway([StubProvider(model="a"), StubProvider(model="b")])
    resp = await gw.call("same input", scenario="t", cross_check=True)
    assert resp.metadata.cross_checked is True
    assert resp.metadata.cross_check_agreed is True


async def test_cross_check_disagree() -> None:
    gw = LLMGateway(
        [
            StubProvider(model="a", canned="真威胁"),
            StubProvider(model="b", canned="误报"),
        ]
    )
    resp = await gw.call("x", scenario="t", cross_check=True)
    assert resp.metadata.cross_check_agreed is False


async def test_cross_check_insufficient_providers() -> None:
    gw = LLMGateway([StubProvider()])
    resp = await gw.call("x", scenario="t", cross_check=True)
    assert resp.metadata.cross_checked is True
    assert resp.metadata.cross_check_agreed is None


# ---- 第二梯队加固（网关修真）----

from typing import ClassVar  # noqa: E402

from aisecops.L05_gateway.llm_gateway.gateway import DEFAULT_SEED  # noqa: E402


class VerdictCC(BaseModel):
    """带 cross_check_fields：只比 verdict，不比 evidence。"""

    cross_check_fields: ClassVar[tuple[str, ...]] = ("verdict",)
    verdict: str
    confidence: float = 0.0
    evidence: list[str] = []


class RaisingProvider(StubProvider):
    """complete 抛非 ProviderError 的脏异常，验证降级链兜住（C-34，#9）。"""

    name = "raiser"

    async def complete(self, request: LLMRequest) -> tuple[str, TokenUsage]:
        raise ValueError("畸形响应体")


async def test_cross_check_field_level_agreement() -> None:
    # 同 verdict、不同 evidence/置信度 → 关键字段一致即判一致（#6，逐字符会判不一致）
    a = StubProvider(model="a", canned='{"verdict":"真威胁","confidence":0.9,"evidence":["A"]}')
    b = StubProvider(model="b", canned='{"verdict":"真威胁","confidence":0.7,"evidence":["B"]}')
    gw = LLMGateway([a, b])
    resp = await gw.call("x", scenario="t", response_model=VerdictCC, cross_check=True)
    assert resp.metadata.cross_check_agreed is True


async def test_cross_check_counts_both_provider_costs() -> None:
    # 双模型成本都计入（#7：旧实现只记 A，系统性低估约 50%）
    a = StubProvider(model="a", price_per_1k_cny=1.0)
    b = StubProvider(model="b", price_per_1k_cny=1.0)
    gw = LLMGateway([a, b])
    resp = await gw.call("一些较长的输入用于产生 token", scenario="t", cross_check=True)
    assert resp.metadata.cross_check_cost_cny > 0
    # 合计成本 > 仅 A 的成本
    a_only = resp.metadata.prompt_tokens + resp.metadata.completion_tokens
    assert resp.metadata.cost_cny > a_only / 1000 * 1.0


async def test_default_seed_injected_for_deterministic_call() -> None:
    gw = LLMGateway([StubProvider()])
    det = await gw.call("x", scenario="t", temperature=0.0)
    assert det.metadata.seed == DEFAULT_SEED  # #8：temp=0 缺省固定 seed
    creative = await gw.call("x", scenario="t", temperature=0.7)
    assert creative.metadata.seed is None  # 创意类不强制


async def test_malformed_output_degrades_to_stub_not_500() -> None:
    # 非 stub 输出畸形 → schema 降级到 stub 占位（#19），而非冒泡 500
    bad = BadProvider(canned="这不是 JSON")
    gw = LLMGateway([bad, StubProvider()])
    resp = await gw.call("x", scenario="t", response_model=Verdict)
    assert resp.metadata.stub is True
    assert resp.parsed is not None and resp.parsed.confidence == 0.0


async def test_dirty_exception_falls_through_to_stub() -> None:
    # provider 抛脏异常（非 ProviderError）也降级（#9）
    gw = LLMGateway([RaisingProvider(), StubProvider()])
    resp = await gw.call("x", scenario="t")
    assert resp.metadata.provider == "stub"
    assert resp.metadata.fallback_used is True
