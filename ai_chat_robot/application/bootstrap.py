"""Composition root for application services."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from application.approvals import ApprovalService
from application.chat import ChatTurnService
from application.sessions import SessionService
from config.paths import SESSION_DB
from orchestrator import apply_approval_decision, handle_user_turn


@dataclass(frozen=True)
class ApplicationServices:
    sessions: SessionService
    chat: ChatTurnService
    approvals: ApprovalService


def build_services(db_path: Path | None = None) -> ApplicationServices:
    """Build shared use-case services for Web, CLI, and future adapters."""
    sessions = SessionService(db_path or SESSION_DB)
    return ApplicationServices(
        sessions=sessions,
        chat=ChatTurnService(handle_user_turn),
        approvals=ApprovalService(apply_approval_decision),
    )


__all__ = ["ApplicationServices", "build_services"]
