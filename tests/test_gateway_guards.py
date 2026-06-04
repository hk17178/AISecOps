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
