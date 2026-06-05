"""L11 AI 资产合规 / Shadow AI 治理（C-3）：合规规则 + 影子发现 + 端到端 API。"""

from __future__ import annotations

from fastapi.testclient import TestClient

from aisecops.L01_human_interface.api import app
from aisecops.L11_target_estate import AiAsset, check_compliance, discover_shadow_ai

client = TestClient(app)


def test_compliance_rules_fire() -> None:
    shadow = AiAsset(id="AIA-1", name="影子AI", status="影子", risk_class="高", owner="")
    findings = {f.rule for f in check_compliance(shadow)}
    assert "ShadowAI" in findings  # 影子 → 命中
    assert "高风险未批" in findings  # 高风险未批
    assert "缺责任人" in findings  # 无属主

    banned = AiAsset(id="AIA-2", name="禁用类", risk_class="不可接受", status="待评审", owner="x")
    assert any(f.severity == "P0" and f.rule == "禁止类AI" for f in check_compliance(banned))

    leaky = AiAsset(id="AIA-3", name="出域敏感", status="已批准", outbound=True, sensitivity="机密", owner="x")
    assert any(f.rule == "敏感出域" for f in check_compliance(leaky))


def test_compliant_asset_has_no_high_severity() -> None:
    ok = AiAsset(
        id="AIA-9",
        name="合规LLM",
        status="已批准",
        outbound=False,
        sensitivity="内部",
        risk_class="有限",
        owner="安全组",
    )
    findings = check_compliance(ok, outbound_enabled=False)
    assert all(f.severity == "P2" for f in findings) or findings == []


def test_discover_shadow_ai_from_in_use_providers() -> None:
    assets = [AiAsset(id="AIA-1", name="通义", status="已批准")]
    in_use = [
        {"name": "通义", "model": "qwen", "outbound": False, "stub": False},  # 已批准 → 不算
        {"name": "野生GPT", "model": "gpt-4", "outbound": True, "stub": False},  # 未登记 → 影子候选
        {"name": "stub", "model": "x", "outbound": False, "stub": True},  # 占位 → 跳过
    ]
    cands = discover_shadow_ai(in_use, assets)
    names = {c["name"] for c in cands}
    assert names == {"野生GPT"}


def test_ai_compliance_api_crud_and_audit() -> None:
    overview = client.get("/api/ai-compliance").json()
    assert "assets" in overview and "findings" in overview and "shadow_candidates" in overview
    assert overview["counts"]["total"] >= 3  # 种子三条

    created = client.post(
        "/api/ai-compliance",
        json={"name": "测试模型", "kind": "ML模型", "status": "影子", "risk_class": "高", "owner": ""},
    ).json()
    aid = created["id"]
    # 体检应能看到这条影子资产的 finding
    findings = client.get("/api/ai-compliance").json()["findings"]
    assert any(f["asset_id"] == aid and f["rule"] == "ShadowAI" for f in findings)

    client.put(f"/api/ai-compliance/{aid}", json={"status": "已批准", "owner": "安全组"})
    assert client.delete(f"/api/ai-compliance/{aid}").json()["status"] == "deleted"
    # 审计留痕
    audit = client.get("/api/audit").json()
    assert any(e["action"] == "ai_asset_create" and e["target"] == aid for e in audit["entries"])
