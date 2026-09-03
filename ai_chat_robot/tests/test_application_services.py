from __future__ import annotations

import asyncio
from pathlib import Path

from application import ApprovalService, ChatTurnService, SessionService


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


def test_orchestrator_exports_are_lazy() -> None:
    import importlib

    orchestrator = importlib.import_module("orchestrator")
    assert callable(orchestrator.run_streamed_turn)
    assert callable(orchestrator.apply_approval_decision)


def test_capability_registry_preserves_legacy_tools() -> None:
    from capabilities.registry import DOCUMENT_TOOLS, WRITER_TOOLS
    from tools.registry import DOCUMENT_TOOLS as LEGACY_DOCUMENT_TOOLS

    assert DOCUMENT_TOOLS is LEGACY_DOCUMENT_TOOLS
    assert set(WRITER_TOOLS).issubset(set(DOCUMENT_TOOLS))


def test_bootstrap_builds_shared_services(tmp_path: Path) -> None:
    from application import build_services

    services = build_services(tmp_path / "ui.db")
    assert services.sessions.db_path == tmp_path / "ui.db"
    assert callable(services.chat._runner)
    assert callable(services.approvals._runner)
