"""L12 出站网络安全 + 出域脱敏（C-22 / C-32，审查 #2/#13/#25）。"""

from __future__ import annotations

from aisecops.L05_gateway.llm_gateway.desensitize import desensitize
from aisecops.L12_core_support.net_guard import is_outbound_url, ssrf_guard


def test_hostname_with_numeric_prefix_not_misjudged_internal() -> None:
    # #25：10.example.com 是公网主机名，旧 startswith 会误判为内网
    assert is_outbound_url("https://10.example.com/hook") is True
    assert is_outbound_url("http://192.168.1.5:9200") is False  # 真私网 IP
    assert is_outbound_url("http://localhost:8000") is False


def test_ssrf_blocks_internal_for_webhook() -> None:
    # 外发 webhook：内网/回环/云元数据一律拒（allow_private=False）
    assert ssrf_guard("http://127.0.0.1/x", allow_private=False)[0] is False
    assert ssrf_guard("http://169.254.169.254/latest/meta-data", allow_private=False)[0] is False
    assert ssrf_guard("http://10.0.0.5/hook", allow_private=False)[0] is False


def test_ssrf_allows_internal_infra_but_blocks_metadata() -> None:
    # 连通测试内部数据源：放行私网，但仍拒链路本地(云元数据)
    assert ssrf_guard("http://10.0.0.9:9200", allow_private=True)[0] is True
    assert ssrf_guard("http://169.254.169.254/", allow_private=True)[0] is False


def test_desensitize_covers_hash_domain_sid() -> None:
    raw = (
        "样本 e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 "
        "来自 evil-c2.example.com 用户 S-1-5-21-100-200-300-1001 邮箱 a@b.com ip 1.2.3.4"
    )
    out = desensitize(raw)
    assert "<HASH>" in out and "e3b0c44298" not in out
    assert "<DOMAIN>" in out and "evil-c2" not in out
    assert "<SID>" in out and "S-1-5-21" not in out
    assert "<EMAIL>" in out and "<IP>" in out
