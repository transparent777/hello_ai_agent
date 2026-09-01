"""沙箱 session_state 持久化（批次 E1）。"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from sandbox.audit import log_audit_event
from sandbox.settings import SANDBOX_PERSIST_ROOT, SANDBOX_PERSIST_SESSION

SANDBOX_RESUME_FILE = "sandbox_resume.json"


def _session_dir(session_id: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in session_id)
    return SANDBOX_PERSIST_ROOT / safe


def load_sandbox_resume_payload(session_id: str) -> dict[str, Any] | None:
    if not SANDBOX_PERSIST_SESSION:
        return None
    path = _session_dir(session_id) / SANDBOX_RESUME_FILE
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def save_sandbox_resume_payload(session_id: str, payload: dict[str, Any]) -> None:
    if not SANDBOX_PERSIST_SESSION:
        return
    session_dir = _session_dir(session_id)
    session_dir.mkdir(parents=True, exist_ok=True)
    path = session_dir / SANDBOX_RESUME_FILE
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    log_audit_event(
        "sandbox_state_saved",
        status="ok",
        session_id=session_id,
        extra={"backend_id": payload.get("backend_id")},
    )


def clear_persisted_session(session_id: str) -> None:
    from approval_store import clear_pending_approval

    clear_pending_approval(session_id)
    session_dir = _session_dir(session_id)
    if session_dir.exists():
        shutil.rmtree(session_dir, ignore_errors=True)
        log_audit_event("sandbox_state_cleared", status="ok", session_id=session_id)


def deserialize_session_state(payload: dict[str, Any]):
    """将持久化的 resume payload 转为 SandboxSessionState。"""
    from sandbox.config import build_docker_client

    session_state_raw = payload.get("session_state")
    if not isinstance(session_state_raw, dict):
        raise ValueError("sandbox_resume payload 缺少 session_state")
    client = build_docker_client()
    return client.deserialize_session_state(session_state_raw)
