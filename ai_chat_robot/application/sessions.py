"""Session use case facade over the current SQLite adapter.

The facade gives Web/CLI adapters one stable API while the storage can later
move from SQLite to another repository without changing entrypoints.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from services.ui_session_store import (
    append_message,
    clear_all_ui_sessions,
    clear_session_messages,
    count_messages,
    init_ui_store,
    list_sessions,
    load_messages,
    prune_empty_sessions,
)


class SessionService:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def initialize(self) -> None:
        init_ui_store(self.db_path)

    def prune_empty(self) -> int:
        return prune_empty_sessions(self.db_path)

    def load_messages(self, session_id: str, *, owner_id: str | None = None) -> list[dict[str, str]]:
        return load_messages(self.db_path, session_id, owner_id=owner_id)

    def count_messages(self, session_id: str, *, owner_id: str | None = None) -> int:
        return count_messages(self.db_path, session_id, owner_id=owner_id)

    def list_sessions(
        self, *, min_messages: int = 1, owner_id: str | None = None
    ) -> list[dict[str, Any]]:
        return list_sessions(self.db_path, min_messages=min_messages, owner_id=owner_id)

    def append_message(
        self,
        session_id: str,
        role: str,
        content: str,
        *,
        meta_json: str | None = None,
        owner_id: str | None = None,
    ) -> None:
        append_message(
            self.db_path,
            session_id,
            role,
            content,
            meta_json=meta_json,
            owner_id=owner_id,
        )

    def clear_session(self, session_id: str, *, owner_id: str | None = None) -> None:
        clear_session_messages(self.db_path, session_id, owner_id=owner_id)

    def clear_all(self, *, owner_id: str | None = None) -> int:
        return clear_all_ui_sessions(self.db_path, owner_id=owner_id)
