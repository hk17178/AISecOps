"""调用元数据记录（C-33）。

每次 LLM 调用产出 CallMetadata，并上报 L12 OTel 指标（次数 / token / 成本）。
成本以「分」（整数）计入指标，避免 Counter 的 float/int 类型摩擦。
"""

from __future__ import annotations

from aisecops.L12_core_support.observability import get_meter

from .models import CallMetadata


class MetadataRecorder:
    """记录调用元数据：进 OTel 指标 + 内存 history（便于查询/测试）。"""

    def __init__(self) -> None:
        meter = get_meter("L05.gateway")
        self._calls = meter.create_counter("aisecops_llm_calls", description="LLM 调用次数")
        self._tokens = meter.create_counter("aisecops_llm_tokens", description="LLM token 总量")
        self._cost_cents = meter.create_counter("aisecops_llm_cost_cents", description="LLM 成本（人民币分）")
        self.history: list[CallMetadata] = []

    def record(self, meta: CallMetadata) -> None:
        attrs = {
            "scenario": meta.scenario,
            "provider": meta.provider,
            "budget_tag": meta.budget_tag,
        }
        self._calls.add(1, attrs)
        self._tokens.add(meta.total_tokens, attrs)
        self._cost_cents.add(int(round(meta.cost_cny * 100)), attrs)
        self.history.append(meta)
