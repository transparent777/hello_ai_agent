from __future__ import annotations

import asyncio
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

from application import ApprovalService, ChatTurnService, SessionService
from services.react_trace import ReactStep


def test_chat_turn_service_delegates() -> None:
    calls: list[tuple] = []

    async def runner(*args, **kwargs):
        calls.append((args, kwargs))
        return "ok", None, []

    result = asyncio.run(
        ChatTurnService(runner).execute(
            "agent", "prompt", "session", "config", on_delta=lambda _: None
        )
    )
    assert result == ("ok", None, [])
    assert calls[0][0][:4] == ("agent", "prompt", "session", "config")


def test_approval_service_delegates() -> None:
    async def runner(*args, **kwargs):
        return "ok", kwargs["approved"]

    result = asyncio.run(
        ApprovalService(runner).decide(
            "pending", "session", "config", approved=True
        )
    )
    assert result == ("ok", True)


def test_session_service_scopes_owner(tmp_path: Path) -> None:
    service = SessionService(tmp_path / "ui.db")
    service.initialize()
    service.append_message("web_owner_one_session", "user", "one", owner_id="owner_one")
    service.append_message("web_owner_two_session", "user", "two", owner_id="owner_two")

    sessions = service.list_sessions(owner_id="owner_one")
    assert [s["session_id"] for s in sessions] == ["web_owner_one_session"]
    assert service.load_messages(
        "web_owner_one_session", owner_id="owner_one"
    )[0]["content"] == "one"


def test_session_service_deduplicates_message_id(tmp_path: Path) -> None:
    service = SessionService(tmp_path / "ui.db")
    service.initialize()
    session_id = "web_owner_one_session"

    assert service.append_message(
        session_id,
        "assistant",
        "first",
        message_id="turn-1:assistant",
        owner_id="owner_one",
    )
    assert not service.append_message(
        session_id,
        "assistant",
        "duplicate",
        message_id="turn-1:assistant",
        owner_id="owner_one",
    )
    assert service.count_messages(session_id, owner_id="owner_one") == 1
    assert service.load_messages(session_id, owner_id="owner_one") == [
        {"role": "assistant", "content": "first"}
    ]


def test_runner_stream_entrypoints_delegate(monkeypatch) -> None:
    import orchestrator.runner as runner

    calls: list[tuple] = []

    async def fake_stream(*args, **kwargs):
        calls.append((args, kwargs))
        return "text", "result", []

    monkeypatch.setattr(runner, "_run_stream", fake_stream)
    result = asyncio.run(runner.run_streamed_turn("agent", "input", "session", "config"))
    resumed = asyncio.run(runner.resume_from_state("agent", "state", "session", "config"))

    assert result == ("text", "result", [])
    assert resumed == result
    assert [call[0][1] for call in calls] == ["input", "state"]


def test_handle_user_turn_runs_stream_once_and_does_not_duplicate_steps(
    monkeypatch,
) -> None:
    import orchestrator.runner as runner

    calls = 0
    step = ReactStep("L1", "workspace_router", "action", "test")
    result = SimpleNamespace(interruptions=[], final_output="完成")

    async def fake_stream(*args, **kwargs):
        nonlocal calls
        calls += 1
        kwargs["on_delta"]("完成")
        kwargs["on_react_step"](step)
        return "完成", result, [step]

    monkeypatch.setattr(runner, "run_streamed_turn", fake_stream)
    monkeypatch.setattr(runner, "collect_mcp_servers_from_agents", lambda *args: [])
    monkeypatch.setattr(runner, "publish_workspace_outputs", lambda: [])
    monkeypatch.setattr(runner, "refresh_memory_summary", lambda session_id: None)
    monkeypatch.setattr(runner, "persist_sandbox_session", lambda *args: None)
    monkeypatch.setattr(runner, "flush_traces", lambda: None)
    monkeypatch.setattr(runner, "trace", lambda *args, **kwargs: nullcontext())

    deltas: list[str] = []
    text, actual_result, steps = asyncio.run(
        runner.handle_user_turn(
            SimpleNamespace(name="workspace_router"),
            "你好",
            SimpleNamespace(session_id="test-session"),
            SimpleNamespace(sandbox=None),
            on_delta=deltas.append,
        )
    )

    assert calls == 1
    assert deltas == ["完成"]
    assert text == "完成"
    assert actual_result is result
    assert steps == [step]


def test_orchestrator_exports_are_lazy() -> None:
    import importlib

    orchestrator = importlib.import_module("orchestrator")
    assert callable(orchestrator.run_streamed_turn)
    assert callable(orchestrator.apply_approval_decision)


def test_capability_registry_preserves_legacy_tools() -> None:
    from capabilities.registry import DOCUMENT_TOOLS, WRITER_TOOLS
    from tools.registry import DOCUMENT_TOOLS as LEGACY_DOCUMENT_TOOLS

    assert DOCUMENT_TOOLS is LEGACY_DOCUMENT_TOOLS
    assert all(
        any(tool is document_tool for document_tool in DOCUMENT_TOOLS)
        for tool in WRITER_TOOLS
    )


def test_specialists_have_a_return_path_to_workspace_router() -> None:
    from specialists.registry import AGENT_REGISTRY

    router = AGENT_REGISTRY["workspace_router"]
    for name in ("document_specialist", "writer_specialist", "data_specialist"):
        agent = AGENT_REGISTRY.get(name)
        if agent is not None:
            assert router in agent.handoffs


def test_bootstrap_builds_shared_services(tmp_path: Path) -> None:
    from application import build_services

    services = build_services(tmp_path / "ui.db")
    assert services.sessions.db_path == tmp_path / "ui.db"
    assert callable(services.chat._runner)
    assert callable(services.approvals._runner)
