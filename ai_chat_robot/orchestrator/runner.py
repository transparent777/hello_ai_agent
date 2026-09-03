"""Agent 运行循环：流式、审批恢复、MCP 生命周期。"""

from __future__ import annotations

from typing import Any

from agents import Agent, RunConfig, Runner, SQLiteSession
from agents.exceptions import (
    InputGuardrailTripwireTriggered,
    MaxTurnsExceeded,
    OutputGuardrailTripwireTriggered,
    ToolInputGuardrailTripwireTriggered,
)
from agents.tracing import flush_traces, trace
from agents.stream_events import AgentUpdatedStreamEvent, RunItemStreamEvent
from openai.types.responses import ResponseTextDeltaEvent

from guardrails import (
    describe_interruption_detail,
    format_input_guardrail_message,
    format_output_guardrail_message,
    log_approval_decision,
)
from mcp_integration.runtime import collect_mcp_servers_from_agents, run_with_mcp_lifecycle
from config.agent_mode import ROUTER_MAX_TURNS, SPECIALIST_MAX_TURNS, is_router_agent
from config.llm import MAX_TURNS, persist_sandbox_session
from orchestrator.handoff_policy import (
    build_deliverable_fallback,
    detect_deliverable_intent,
    note_react_step,
    prepare_router_input,
    sanitize_user_visible_output,
)
from orchestrator.turn_state import clear_turn_state, reset_turn_state
from services.react_trace import ReactStep, ReactStepCollector, handoff_target_name
from services.stream_filter import StreamGate
from sandbox.memory_sync import refresh_memory_summary
from sandbox.metrics import record_event, track_duration
from sandbox.ops import run_with_retries, run_with_sandbox_slot
from sandbox.runtime import publish_workspace_outputs
from sandbox.settings import SANDBOX_RUN_TIMEOUT_SECONDS
from services.approval_store import (
    PendingApprovalRecord,
    build_pending_record,
    clear_pending_approval,
    save_pending_approval,
)
from specialists.registry import AGENT_REGISTRY, get_agent_by_name
from specialists.router import workspace_router


def _extract_delta(event: Any) -> str | None:
    if event.type == "raw_response_event" and isinstance(
        event.data, ResponseTextDeltaEvent
    ):
        return event.data.delta
    return None


def _hierarchical_max_turns() -> int:
    return max(MAX_TURNS, ROUTER_MAX_TURNS + SPECIALIST_MAX_TURNS)


async def _consume_stream(
    stream: Any,
    *,
    on_delta: Any | None = None,
    react_collector: ReactStepCollector | None = None,
    on_react_step: Any | None = None,
    stream_gate: StreamGate | None = None,
) -> str:
    parts: list[str] = []
    async for event in stream.stream_events():
        if isinstance(event, RunItemStreamEvent) and event.name in {
            "handoff_requested",
            "handoff_occured",
        }:
            if stream_gate is not None:
                stream_gate.note_handoff(handoff_target_name(event.item))

        if isinstance(event, AgentUpdatedStreamEvent):
            agent_name = getattr(event.new_agent, "name", "unknown")
            if react_collector is not None:
                react_collector.set_agent(agent_name)
            if stream_gate is not None:
                stream_gate.set_agent(agent_name)

        if react_collector is not None:
            step = react_collector.consume(event)
            if step is not None and on_react_step is not None:
                on_react_step(step)

        delta = _extract_delta(event)
        if delta:
            parts.append(delta)
            if on_delta is not None:
                visible = (
                    stream_gate.emit(delta)
                    if stream_gate is not None
                    else delta
                )
                if visible:
                    on_delta(visible)

    if stream_gate is not None and on_delta is not None:
        tail = stream_gate.flush()
        if tail:
            on_delta(tail)

    if stream.run_loop_exception:
        raise stream.run_loop_exception

    return "".join(parts)


async def run_streamed_turn(
    agent: Agent,
    user_input: str,
    session: SQLiteSession,
    run_config: RunConfig,
    *,
    on_delta: Any | None = None,
    on_react_step: Any | None = None,
    react_collector: ReactStepCollector | None = None,
    stream_gate: StreamGate | None = None,
) -> tuple[str, Any, list[ReactStep]]:
    """一次应用级 turn：流式消费完毕后，才视为 run 已结算。"""
    collector = react_collector or ReactStepCollector(
        initial_agent=getattr(agent, "name", "workspace_router")
    )
    stream = Runner.run_streamed(
        agent,
        user_input,
        session=session,
        run_config=run_config,
        max_turns=_hierarchical_max_turns(),
    )

    text = await _consume_stream(
        stream,
        on_delta=on_delta,
        react_collector=collector,
        on_react_step=on_react_step,
        stream_gate=stream_gate,
    )
    return text, stream, collector.steps


async def resume_from_state(
    agent: Agent,
    state: Any,
    session: SQLiteSession,
    run_config: RunConfig,
    *,
    on_delta: Any | None = None,
    on_react_step: Any | None = None,
    react_collector: ReactStepCollector | None = None,
    stream_gate: StreamGate | None = None,
) -> tuple[str, Any, list[ReactStep]]:
    """从 RunState 恢复暂停或中断的同一轮，不传新 user message。"""
    collector = react_collector or ReactStepCollector(
        initial_agent=getattr(agent, "name", "workspace_router")
    )
    stream = Runner.run_streamed(
        agent,
        state,
        session=session,
        run_config=run_config,
        max_turns=_hierarchical_max_turns(),
    )

    text = await _consume_stream(
        stream,
        on_delta=on_delta,
        react_collector=collector,
        on_react_step=on_react_step,
        stream_gate=stream_gate,
    )
    return text, stream, collector.steps


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
    """审批后从 state 恢复，继续同一轮任务。"""
    from agents.run_state import RunState

    if isinstance(pending, PendingApprovalRecord):
        record = pending
        if record.live_result is not None:
            state = record.live_result.to_state()
            interruptions = list(record.live_result.interruptions)
        else:
            state = await RunState.from_json(
                workspace_router,
                record.run_state_json,
            )
            interruptions = state.get_interruptions()
        resume_agent = get_agent_by_name(record.resume_agent_name)
    else:
        run_result = pending
        state = run_result.to_state()
        interruptions = list(run_result.interruptions)
        resume_agent = run_result.last_agent

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

    text, result, _steps = await resume_from_state(
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
    """终端版：审批 = 暂停的任务，从 state 继续而非新 user turn。"""
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
    """处理一轮用户输入。返回 (回复文本, run_result, react_steps)。"""
    _ = actor
    servers = collect_mcp_servers_from_agents(*AGENT_REGISTRY.values())
    react_steps: list[ReactStep] = []
    turn_token = reset_turn_state()
    deliverable_task = detect_deliverable_intent(user_input)
    stream_gate = StreamGate(deliverable_task=deliverable_task)
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
                    if run_config.sandbox is not None:
                        return await run_with_sandbox_slot(
                            lambda: run_streamed_turn(
                                agent,
                                agent_input,
                                session,
                                run_config,
                                on_delta=on_delta,
                                on_react_step=_collect_step,
                                stream_gate=stream_gate,
                            ),
                            timeout_seconds=SANDBOX_RUN_TIMEOUT_SECONDS,
                        )
                    return await run_streamed_turn(
                        agent,
                        agent_input,
                        session,
                        run_config,
                        on_delta=on_delta,
                        on_react_step=_collect_step,
                        stream_gate=stream_gate,
                    )

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
            final_text = _finalize_user_output(result.final_output, result, react_steps)
            return final_text, result, react_steps

        except InputGuardrailTripwireTriggered as exc:
            record_event("input_guardrail_triggered")
            return format_input_guardrail_message(exc), None, react_steps
        except OutputGuardrailTripwireTriggered as exc:
            record_event("output_guardrail_triggered")
            fallback = build_deliverable_fallback(react_steps)
            if fallback:
                return fallback, None, react_steps
            return format_output_guardrail_message(exc), None, react_steps
        except ToolInputGuardrailTripwireTriggered as exc:
            record_event("tool_input_guardrail_triggered")
            return (
                f"**安全拦截**：工具调用未通过执行前审查（{exc.guardrail.get_name()}）。",
                None,
                react_steps,
            )
        except MaxTurnsExceeded:
            record_event("agent_turn_max_turns_exceeded")
            print(
                f"\n[运行时失败] 超过最大轮次限制（max_turns={_hierarchical_max_turns()}）。"
                "请简化问题或提高 AGENT_MAX_TURNS / SPECIALIST_MAX_TURNS。"
            )
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
