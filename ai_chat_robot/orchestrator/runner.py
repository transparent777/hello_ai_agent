"""Compatibility facade for the application turn orchestrator."""

from __future__ import annotations

from typing import Any

from agents import Agent, RunConfig, SQLiteSession
from agents.exceptions import (
    InputGuardrailTripwireTriggered,
    MaxTurnsExceeded,
    OutputGuardrailTripwireTriggered,
    ToolInputGuardrailTripwireTriggered,
)
from agents.tracing import flush_traces, trace

from adapters.agent_runtime import persist_sandbox_session
from config.agent_mode import is_router_agent
from guardrails import format_input_guardrail_message, format_output_guardrail_message
from mcp_integration.runtime import collect_mcp_servers_from_agents, run_with_mcp_lifecycle
from orchestrator.approval_runtime import (
    apply_approval_decision,
    capture_pending_approval,
    describe_interruptions,
    resolve_interruptions,
)
from orchestrator.handoff_policy import (
    build_deliverable_fallback,
    detect_deliverable_intent,
    note_react_step,
    prepare_router_input,
    sanitize_user_visible_output,
)
from orchestrator.stream_runtime import hierarchical_max_turns, run as _run_stream
from orchestrator.turn_state import clear_turn_state, reset_turn_state
from sandbox.memory_sync import refresh_memory_summary
from sandbox.metrics import record_event, track_duration
from sandbox.ops import run_with_retries, run_with_sandbox_slot
from adapters.sandbox_runtime import publish_workspace_outputs
from sandbox.settings import SANDBOX_RUN_TIMEOUT_SECONDS
from services.react_trace import ReactStep
from services.stream_filter import StreamGate
from specialists.registry import AGENT_REGISTRY


async def run_streamed_turn(*args: Any, **kwargs: Any):
    """Backward-compatible entry point for a new streamed turn."""
    return await _run_stream(*args, **kwargs)


async def resume_from_state(*args: Any, **kwargs: Any):
    """Backward-compatible entry point for resuming a paused turn."""
    return await _run_stream(*args, **kwargs)


def _hierarchical_max_turns() -> int:
    return hierarchical_max_turns()


def _guardrail_retryable(exc: BaseException) -> bool:
    return not isinstance(
        exc,
        (
            InputGuardrailTripwireTriggered,
            OutputGuardrailTripwireTriggered,
            ToolInputGuardrailTripwireTriggered,
        ),
    )


def _finalize_user_output(
    text: str | None,
    result: Any,
    steps: list[ReactStep],
) -> str | None:
    cleaned = sanitize_user_visible_output(text or "")
    if cleaned:
        return cleaned
    fallback = build_deliverable_fallback(steps)
    if fallback:
        return fallback
    return text


async def handle_user_turn(
    agent: Agent,
    user_input: str,
    session: SQLiteSession,
    run_config: RunConfig,
    *,
    on_delta: Any | None = None,
    on_react_step: Any | None = None,
    actor: str | None = None,
) -> tuple[str | None, Any | None, list[ReactStep]]:
    """Execute one user turn, including lifecycle, retries, and finalization."""
    servers = collect_mcp_servers_from_agents(*AGENT_REGISTRY.values())
    react_steps: list[ReactStep] = []
    turn_token = reset_turn_state()
    stream_gate = StreamGate(deliverable_task=detect_deliverable_intent(user_input))
    agent_input = (
        prepare_router_input(user_input)
        if is_router_agent(getattr(agent, "name", None))
        else user_input
    )

    def _collect_step(step: ReactStep) -> None:
        note_react_step(step)
        react_steps.append(step)
        if on_react_step is not None:
            on_react_step(step)

    async def _execute_turn() -> tuple[str | None, Any | None, list[ReactStep]]:
        try:
            with track_duration("agent_turn_total_ms"):

                async def _run_once() -> tuple[str, Any, list[ReactStep]]:
                    kwargs = {
                        "on_delta": on_delta,
                        "on_react_step": _collect_step,
                        "stream_gate": stream_gate,
                    }
                    operation = lambda: run_streamed_turn(
                        agent, agent_input, session, run_config, **kwargs
                    )
                    if run_config.sandbox is not None:
                        return await run_with_sandbox_slot(
                            operation,
                            timeout_seconds=SANDBOX_RUN_TIMEOUT_SECONDS,
                        )
                    return await operation()

                _, result, steps = await run_with_retries(
                    _run_once,
                    retryable=_guardrail_retryable,
                )
                react_steps.extend(steps)

            if result.interruptions:
                pending = capture_pending_approval(session.session_id, result)
                persist_sandbox_session(session.session_id, result)
                record_event("agent_turn_interrupted")
                return None, pending, react_steps

            published = publish_workspace_outputs()
            refresh_memory_summary(session.session_id)
            persist_sandbox_session(session.session_id, result)
            record_event(
                "agent_turn_completed",
                sandbox=run_config.sandbox is not None,
                published_files=len(published),
            )
            return _finalize_user_output(result.final_output, result, react_steps), result, react_steps

        except InputGuardrailTripwireTriggered as exc:
            record_event("input_guardrail_triggered")
            return format_input_guardrail_message(exc), None, react_steps
        except OutputGuardrailTripwireTriggered as exc:
            record_event("output_guardrail_triggered")
            fallback = build_deliverable_fallback(react_steps)
            return (fallback or format_output_guardrail_message(exc), None, react_steps)
        except ToolInputGuardrailTripwireTriggered as exc:
            record_event("tool_input_guardrail_triggered")
            return (
                f"**安全拦截**：工具调用未通过执行前审查（{exc.guardrail.get_name()}）。",
                None,
                react_steps,
            )
        except MaxTurnsExceeded:
            record_event("agent_turn_max_turns_exceeded")
            print(f"\n[运行时失败] 超过最大轮次限制（max_turns={_hierarchical_max_turns()}）。")
        except Exception as exc:
            record_event("agent_turn_failed", error=type(exc).__name__)
            print(f"\n[运行时失败] {type(exc).__name__}: {exc}")
        return None, None, react_steps

    try:
        with trace(
            "workspace_user_turn",
            metadata={"session_id": session.session_id, "actor": actor or "user"},
        ):
            outcome = await run_with_mcp_lifecycle(servers, _execute_turn)
        flush_traces()
        return outcome
    finally:
        clear_turn_state(turn_token)


__all__ = [
    "apply_approval_decision",
    "capture_pending_approval",
    "describe_interruptions",
    "handle_user_turn",
    "resolve_interruptions",
    "resume_from_state",
    "run_streamed_turn",
]
