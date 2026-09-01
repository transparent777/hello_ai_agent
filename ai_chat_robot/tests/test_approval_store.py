"""审批 state 持久化单元测试。"""

from __future__ import annotations

from approval_store import (
    PendingApprovalRecord,
    clear_pending_approval,
    load_pending_approval,
    save_pending_approval,
)


def test_approval_pending_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "approval_store.SANDBOX_PERSIST_ROOT",
        tmp_path,
    )
    monkeypatch.setattr("approval_store.APPROVAL_PERSIST_ENABLED", True)

    record = PendingApprovalRecord(
        session_id="web_test01",
        resume_agent_name="order_specialist",
        interruption_summaries=["工具 `process_refund` 需要人工审批"],
        run_state_json={"$schemaVersion": "1.14", "current_turn": 1},
        saved_at="2026-09-01T00:00:00+00:00",
    )
    save_pending_approval(record)
    loaded = load_pending_approval("web_test01")
    assert loaded is not None
    assert loaded.resume_agent_name == "order_specialist"
    assert loaded.interruption_summaries[0].startswith("工具")

    clear_pending_approval("web_test01")
    assert load_pending_approval("web_test01") is None
