"""Approval state handling and post-run publication."""

from __future__ import annotations

from typing import Any

from agents import RunConfig, SQLiteSession

from adapters.agent_runtime import persist_sandbox_session
from guardrails import describe_interruption_detail, log_approval_decision
from orchestrator.stream_runtime import run as run_stream
from sandbox.memory_sync import refresh_memory_summary
from adapters.sandbox_runtime import publish_workspace_outputs
from services.approval_store import (
    PendingApprovalRecord,
    build_pending_record,
    clear_pending_approval,
    save_pending_approval,
)
from specialists.registry import get_agent_by_name
from specialists.router import workspace_router


def describe_interruptions(run_result: Any) -> list[str]:
    if isinstance(run_result, PendingApprovalRecord):
        return run_result.describe()
    return [describe_interruption_detail(i) for i in run_result.interruptions]


def capture_pending_approval(session_id: str, run_result: Any) -> PendingApprovalRecord:
    record = build_pending_record(
        session_id,
        run_result,
        interruption_summaries=describe_interruptions(run_result),
    )
    save_pending_approval(record)
    return record


async def apply_approval_decision(
    pending: PendingApprovalRecord | Any,
    session: SQLiteSession,
    run_config: RunConfig,
    *,
    approved: bool,
    on_delta: Any | None = None,
) -> tuple[str, Any]:
    """Apply a decision, resume the paused run, and publish completed artifacts."""
    from agents.run_state import RunState

    if isinstance(pending, PendingApprovalRecord):
        record = pending
        if record.live_result is not None:
            state = record.live_result.to_state()
            interruptions = list(record.live_result.interruptions)
        else:
            state = await RunState.from_json(workspace_router, record.run_state_json)
            interruptions = state.get_interruptions()
        resume_agent = get_agent_by_name(record.resume_agent_name)
    else:
        state = pending.to_state()
        interruptions = list(pending.interruptions)
        resume_agent = pending.last_agent

    for interruption in interruptions:
        if approved:
            state.approve(interruption)
        else:
            state.reject(interruption)

    log_approval_decision(
        session_id=session.session_id,
        approved=approved,
        interruptions=interruptions,
    )
    text, result, _steps = await run_stream(
        resume_agent,
        state,
        session,
        run_config,
        on_delta=on_delta,
    )
    persist_sandbox_session(session.session_id, result)
    if result.interruptions:
        return text, capture_pending_approval(session.session_id, result)
    clear_pending_approval(session.session_id)
    publish_workspace_outputs()
    refresh_memory_summary(session.session_id)
    return text, result


async def resolve_interruptions(
    run_result: Any,
    session: SQLiteSession,
    run_config: RunConfig,
) -> Any:
    """CLI helper that interactively resolves all pending interruptions."""
    current = run_result
    while current.interruptions:
        print("\n--- 待审批操作 ---")
        for idx, desc in enumerate(describe_interruptions(current), start=1):
            print(f"{idx}. {desc}")
        choice = input("批准全部？(y/n，默认 n): ").strip().lower()
        _, current = await apply_approval_decision(
            current,
            session,
            run_config,
            approved=(choice == "y"),
            on_delta=lambda d: print(d, end="", flush=True),
        )
    return current


__all__ = [
    "apply_approval_decision",
    "capture_pending_approval",
    "describe_interruptions",
    "resolve_interruptions",
]
