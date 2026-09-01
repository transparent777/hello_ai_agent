"""Web 聊天 UI 记录：与 Agent SQLiteSession 分开，专门保存可展示的对话历史。"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_ui_store(db_path: Path) -> None:
    with _connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ui_chat_sessions (
                session_id TEXT PRIMARY KEY,
                title TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ui_chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES ui_chat_sessions (session_id)
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_ui_chat_messages_session
            ON ui_chat_messages (session_id, id)
            """
        )
        conn.commit()


def touch_session(db_path: Path, session_id: str, title: str | None = None) -> None:
    now = datetime.now().isoformat(timespec="seconds")
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT session_id FROM ui_chat_sessions WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        if row is None:
            conn.execute(
                """
                INSERT INTO ui_chat_sessions (session_id, title, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (session_id, title or "新对话", now, now),
            )
        else:
            conn.execute(
                """
                UPDATE ui_chat_sessions
                SET updated_at = ?, title = COALESCE(?, title)
                WHERE session_id = ?
                """,
                (now, title, session_id),
            )
        conn.commit()


def append_message(
    db_path: Path,
    session_id: str,
    role: str,
    content: str,
) -> None:
    now = datetime.now().isoformat(timespec="seconds")
    title = None
    if role == "user":
        title = content[:40] + ("…" if len(content) > 40 else "")

    touch_session(db_path, session_id, title=title)
    with _connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO ui_chat_messages (session_id, role, content, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (session_id, role, content, now),
        )
        conn.commit()


def load_messages(db_path: Path, session_id: str) -> list[dict[str, str]]:
    with _connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT role, content FROM ui_chat_messages
            WHERE session_id = ?
            ORDER BY id ASC
            """,
            (session_id,),
        ).fetchall()
    return [{"role": row["role"], "content": row["content"]} for row in rows]


def count_messages(db_path: Path, session_id: str) -> int:
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM ui_chat_messages WHERE session_id = ?",
            (session_id,),
        ).fetchone()
    return int(row["n"]) if row else 0


def list_sessions(db_path: Path, *, min_messages: int = 1) -> list[dict[str, str]]:
    with _connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT session_id, title, created_at, updated_at,
                   (SELECT COUNT(*) FROM ui_chat_messages m
                    WHERE m.session_id = s.session_id) AS message_count
            FROM ui_chat_sessions s
            ORDER BY updated_at DESC
            """
        ).fetchall()
    sessions = [dict(row) for row in rows if int(row["message_count"]) >= min_messages]
    return sessions


def prune_empty_sessions(db_path: Path) -> int:
    """删除无消息的空会话记录，返回清理数量。"""
    with _connect(db_path) as conn:
        cursor = conn.execute(
            """
            DELETE FROM ui_chat_sessions
            WHERE session_id NOT IN (
                SELECT DISTINCT session_id FROM ui_chat_messages
            )
            """
        )
        conn.commit()
        return cursor.rowcount


def clear_session_messages(db_path: Path, session_id: str) -> None:
    with _connect(db_path) as conn:
        conn.execute(
            "DELETE FROM ui_chat_messages WHERE session_id = ?",
            (session_id,),
        )
        conn.execute(
            "DELETE FROM ui_chat_sessions WHERE session_id = ?",
            (session_id,),
        )
        conn.commit()


def delete_session(db_path: Path, session_id: str) -> None:
    clear_session_messages(db_path, session_id)
