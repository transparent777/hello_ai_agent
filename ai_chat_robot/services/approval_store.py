"""人工审批 RunState 持久化：刷新页面后仍可 approve/reject 并恢复同一轮。"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sandbox.audit import log_audit_event
from sandbox.settings import SANDBOX_PERSIST_ROOT

APPROVAL_PENDING_FILE = "approval_pending.json"
_SCHEMA_VERSION = 1


def _env_bool(name: str, default: bool) -> bool:
    import os

    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


APPROVAL_PERSIST_ENABLED = _env_bool("APPROVAL_PERSIST_ENABLED", True)


def _session_dir(session_id: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in session_id)
    return SANDBOX_PERSIST_ROOT / safe


@dataclass
class PendingApprovalRecord:
    """待审批运行快照（可仅驻内存，或已落盘）。"""

    session_id: str
    resume_agent_name: str
    interruption_summaries: list[str]
    run_state_json: dict[str, Any]
    saved_at: str
    live_result: Any = field(default=None, repr=False, compare=False)

    def describe(self) -> list[str]:
        return list(self.interruption_summaries)


def _approval_path(session_id: str) -> Path:
    return _session_dir(session_id) / APPROVAL_PENDING_FILE


def save_pending_approval(record: PendingApprovalRecord) -> None:
    if not APPROVAL_PERSIST_ENABLED:
        return
    session_dir = _session_dir(record.session_id)
    session_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": _SCHEMA_VERSION,
        "session_id": record.session_id,
        "resume_agent_name": record.resume_agent_name,
        "interruption_summaries": record.interruption_summaries,
        "run_state": record.run_state_json,
        "saved_at": record.saved_at,
    }
    _approval_path(record.session_id).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    log_audit_event(
        "approval_state_saved",
        status="ok",
        session_id=record.session_id,
        extra={
            "resume_agent": record.resume_agent_name,
            "pending_count": len(record.interruption_summaries),
        },
    )


def load_pending_approval(session_id: str) -> PendingApprovalRecord | None:
    if not APPROVAL_PERSIST_ENABLED:
        return None
    path = _approval_path(session_id)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    run_state = data.get("run_state")
    if not isinstance(run_state, dict):
        return None
    summaries = data.get("interruption_summaries")
    if not isinstance(summaries, list):
        summaries = []
    resume_agent = data.get("resume_agent_name")
    if not isinstance(resume_agent, str) or not resume_agent:
        return None
    return PendingApprovalRecord(
        session_id=session_id,
        resume_agent_name=resume_agent,
        interruption_summaries=[str(s) for s in summaries],
        run_state_json=run_state,
        saved_at=str(data.get("saved_at") or ""),
    )


def clear_pending_approval(session_id: str) -> None:
    path = _approval_path(session_id)
    if path.is_file():
        path.unlink(missing_ok=True)
        log_audit_event("approval_state_cleared", status="ok", session_id=session_id)


def has_pending_approval(session_id: str) -> bool:
    return APPROVAL_PERSIST_ENABLED and _approval_path(session_id).is_file()


def build_pending_record(
    session_id: str,
    run_result: Any,
    *,
    interruption_summaries: list[str],
) -> PendingApprovalRecord:
    state = run_result.to_state()
    return PendingApprovalRecord(
        session_id=session_id,
        resume_agent_name=run_result.last_agent.name,
        interruption_summaries=interruption_summaries,
        run_state_json=state.to_json(),
        saved_at=datetime.now(timezone.utc).isoformat(),
        live_result=run_result,
    )
