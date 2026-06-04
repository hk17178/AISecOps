"""L12 审计哈希链测试（C-23）。"""

from datetime import datetime, timezone

from aisecops.L12_core_support.audit import GENESIS_HASH, AuditLog


def _clock() -> datetime:
    return datetime(2026, 6, 4, tzinfo=timezone.utc)


def test_chain_links_and_verifies() -> None:
    log = AuditLog(clock=_clock)
    log.append("orchestrator", "dispatch", target="alert_triage")
    log.append("triage", "verdict", target="WIN-APP-07", details={"verdict": "真威胁"})
    entries = log.entries
    assert len(entries) == 2
    assert entries[0].prev_hash == GENESIS_HASH
    assert entries[1].prev_hash == entries[0].entry_hash
    assert log.verify() is True


def test_tamper_is_detected() -> None:
    log = AuditLog(clock=_clock)
    log.append("a", "action1")
    log.append("b", "action2")
    # 篡改一条历史记录
    log.entries[0].action = "tampered"
    assert log.verify() is False
