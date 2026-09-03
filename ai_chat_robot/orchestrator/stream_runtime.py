"""Agent SDK stream execution and event translation."""

from __future__ import annotations

from typing import Any

from agents import Agent, RunConfig, Runner, SQLiteSession
from agents.stream_events import AgentUpdatedStreamEvent, RunItemStreamEvent
from openai.types.responses import ResponseTextDeltaEvent

from adapters.agent_runtime import MAX_TURNS
from config.agent_mode import ROUTER_MAX_TURNS, SPECIALIST_MAX_TURNS
from services.react_trace import ReactStep, ReactStepCollector, handoff_target_name
from services.stream_filter import StreamGate


def hierarchical_max_turns() -> int:
    return max(MAX_TURNS, ROUTER_MAX_TURNS + SPECIALIST_MAX_TURNS)


def extract_delta(event: Any) -> str | None:
    if event.type == "raw_response_event" and isinstance(
        event.data, ResponseTextDeltaEvent
    ):
        return event.data.delta
    return None


async def consume_stream(
    stream: Any,
    *,
    on_delta: Any | None = None,
    react_collector: ReactStepCollector | None = None,
    on_react_step: Any | None = None,
    stream_gate: StreamGate | None = None,
) -> str:
    """Consume SDK events and expose only application-level callbacks."""
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

        delta = extract_delta(event)
        if delta:
            parts.append(delta)
            if on_delta is not None:
                visible = (
                    stream_gate.emit(delta) if stream_gate is not None else delta
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


async def run(
    agent: Agent,
    input_or_state: Any,
    session: SQLiteSession,
    run_config: RunConfig,
    *,
    on_delta: Any | None = None,
    on_react_step: Any | None = None,
    react_collector: ReactStepCollector | None = None,
    stream_gate: StreamGate | None = None,
) -> tuple[str, Any, list[ReactStep]]:
    """Run a new turn or resume a RunState using the same stream pipeline."""
    collector = react_collector or ReactStepCollector(
        initial_agent=getattr(agent, "name", "workspace_router")
    )
    stream = Runner.run_streamed(
        agent,
        input_or_state,
        session=session,
        run_config=run_config,
        max_turns=hierarchical_max_turns(),
    )
    text = await consume_stream(
        stream,
        on_delta=on_delta,
        react_collector=collector,
        on_react_step=on_react_step,
        stream_gate=stream_gate,
    )
    return text, stream, collector.steps


__all__ = ["consume_stream", "extract_delta", "hierarchical_max_turns", "run"]
