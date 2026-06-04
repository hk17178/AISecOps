"""L12 可观测性最小集成 —— 证明埋点链路可用（S1.5 DoD）。"""

from aisecops.L12_core_support.observability import (
    get_meter,
    get_tracer,
    init_observability,
)


def test_init_is_idempotent() -> None:
    """重复初始化不报错（幂等）。"""
    init_observability()
    init_observability()


def test_tracer_creates_span() -> None:
    """能创建一个 span（trace 链路可用）。"""
    init_observability()
    tracer = get_tracer("test")
    with tracer.start_as_current_span("unit-test-span") as span:
        assert span is not None


def test_meter_counter() -> None:
    """能创建并累加一个计数器（metric 链路可用）。"""
    init_observability()
    meter = get_meter("test")
    counter = meter.create_counter("aisecops_test_counter")
    counter.add(1, {"scenario": "unit-test"})
