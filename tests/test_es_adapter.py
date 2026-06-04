"""L06 ES 适配器 + 注册表测试（全用 Stub，不连真 ES）。"""

from aisecops.L06_mcp_servers import StubLogSource, build_tool_registry
from aisecops.L12_core_support.config import Settings


async def test_stub_log_source_filters_by_host() -> None:
    src = StubLogSource()
    logs = await src.search_logs(host="WIN-APP-07")
    assert len(logs) >= 1
    assert all(log["host"] == "WIN-APP-07" for log in logs)
    assert src.last_query == {"host": "WIN-APP-07", "ip": None, "size": 10}


async def test_stub_log_source_size_limit() -> None:
    src = StubLogSource(logs=[{"host": "h", "i": i} for i in range(20)])
    logs = await src.search_logs(host="h", size=3)
    assert len(logs) == 3


def test_build_tool_registry_defaults_to_stub() -> None:
    # 显式清空 ES 凭证 → 离线 StubLogSource
    reg = build_tool_registry(Settings(es_api_key="", es_username="", es_password=""))
    assert reg.log_source is not None
    assert reg.log_source.name == "es-stub"
