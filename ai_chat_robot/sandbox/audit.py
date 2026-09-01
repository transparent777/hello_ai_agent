"""沙箱执行审计日志（P0）。"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from typing import Any

from sandbox.settings import AUDIT_LOG_PATH

_lock = threading.Lock()


def _ensure_parent() -> None:
    AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


def log_audit_event(
    event: str,
    *,
    command: str | None = None,
    exit_code: int | None = None,
    duration_ms: int | None = None,
    session_id: str | None = None,
    actor: str | None = None,
    status: str = "ok",
    detail: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    record: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "status": status,
    }
    if command is not None:
        record["command"] = command
    if exit_code is not None:
        record["exit_code"] = exit_code
    if duration_ms is not None:
        record["duration_ms"] = duration_ms
    if session_id is not None:
        record["session_id"] = session_id
    if actor is not None:
        record["actor"] = actor
    if detail is not None:
        record["detail"] = detail
    if extra:
        record.update(extra)

    line = json.dumps(record, ensure_ascii=False)
    with _lock:
        _ensure_parent()
        with AUDIT_LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
