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
