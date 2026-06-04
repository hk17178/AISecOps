"""L12 · 可观测性最小集成（OpenTelemetry）。

S1 阶段：用 Console 导出器验证「埋点链路可用」，不依赖外部 Collector/Grafana。
等 `make obs` 起了可观测栈，再把导出器切到 OTLP（指向 docker-compose 的 otel-collector）。

跨层定位（ADR-0008）：L12 是横切支撑层，任何层都可调用本模块做 trace/metric。
所有 LLM 调用的 metadata（C-33）后续也经此上报。
"""

from __future__ import annotations

from opentelemetry import metrics, trace
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

_SERVICE_NAME = "aisecops"
_initialized = False


def init_observability(
    service_name: str = _SERVICE_NAME,
    console: bool = True,
    metric_console: bool = False,
) -> None:
    """初始化全局 Tracer / Meter Provider。

    幂等：重复调用直接返回，不会重复注册。应用启动时调一次即可。

    参数:
        service_name: 资源标识，显示在 trace/metric 上。
        console: True 用 Console 输出 trace（S1 默认）；接 OTLP 时置 False 另配。
        metric_console: 是否周期性把 metric dump 到 Console。默认 False——
            因为 PeriodicExportingMetricReader 会在进程退出时向可能已关闭的 stdout
            写入而报噪声错误（pytest 下尤其明显）。Metric API 始终可用，无需开它。
    """
    global _initialized
    if _initialized:
        return

    resource = Resource.create({"service.name": service_name})

    # ---- Traces ----
    tracer_provider = TracerProvider(resource=resource)
    if console:
        tracer_provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(tracer_provider)

    # ---- Metrics ----
    readers = []
    if metric_console:
        readers.append(
            PeriodicExportingMetricReader(
                ConsoleMetricExporter(), export_interval_millis=60_000
            )
        )
    metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=readers))

    _initialized = True


def shutdown_observability() -> None:
    """优雅关闭：flush 并停掉 Provider（应用退出时调，避免丢数据）。"""
    tracer_provider = trace.get_tracer_provider()
    if hasattr(tracer_provider, "shutdown"):
        tracer_provider.shutdown()
    meter_provider = metrics.get_meter_provider()
    if hasattr(meter_provider, "shutdown"):
        meter_provider.shutdown()


def get_tracer(name: str = _SERVICE_NAME) -> trace.Tracer:
    """取一个 Tracer（未初始化则用全局默认 Provider）。"""
    return trace.get_tracer(name)


def get_meter(name: str = _SERVICE_NAME) -> metrics.Meter:
    """取一个 Meter（未初始化则用全局默认 Provider）。"""
    return metrics.get_meter(name)
