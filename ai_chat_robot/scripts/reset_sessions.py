"""清空 Agent 与 Web 聊天会话（含旧版电商客服记录）。"""

from __future__ import annotations

import sys
from pathlib import Path

import sqlite3

_APP_DIR = Path(__file__).resolve().parent.parent
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

from config.paths import PACKAGE_ROOT, SESSION_DB
from services.ui_session_store import clear_all_ui_sessions, init_ui_store


def _remove_sqlite_files() -> bool:
    deleted = False
    for suffix in ("", "-wal", "-shm"):
        path = Path(f"{SESSION_DB}{suffix}")
        if not path.exists():
            continue
        try:
            path.unlink()
            print(f"已删除: {path}")
            deleted = True
        except OSError as exc:
            print(f"无法删除 {path}（请先关闭 Streamlit / robot.py）: {exc}")
    return deleted


def _clear_sandbox_persist() -> None:
    persist = PACKAGE_ROOT / "sandbox" / "persist"
    if not persist.exists():
        return
    removed = 0
    for child in persist.iterdir():
        if child.is_dir():
            for f in child.rglob("*"):
                if f.is_file():
                    f.unlink()
                    removed += 1
            for d in sorted(child.rglob("*"), reverse=True):
                if d.is_dir():
                    d.rmdir()
            child.rmdir()
            removed += 1
    if removed:
        print(f"已清理沙箱持久化目录: {persist}")


def main() -> None:
    ui_count = 0
    if SESSION_DB.exists():
        init_ui_store(SESSION_DB)
        ui_count = clear_all_ui_sessions(SESSION_DB)
        with sqlite3.connect(SESSION_DB) as conn:
            tables = [
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            ]
            for name in tables:
                if name.startswith("sqlite_"):
                    continue
                if name.startswith("ui_chat_"):
                    continue
                conn.execute(f"DELETE FROM {name}")
            conn.commit()
    deleted = _remove_sqlite_files()
    if deleted or not SESSION_DB.exists():
        init_ui_store(SESSION_DB)
    _clear_sandbox_persist()
    print(f"Web 历史已清除（{ui_count} 条会话）。")
    if not deleted and SESSION_DB.exists():
        print("Agent 会话表已清空；完整删除 sessions.db 请先停止 Streamlit 后再运行本脚本。")
    else:
        print("会话已完全重置。")
    print("请重启 Streamlit / 重新运行 robot.py。")


if __name__ == "__main__":
    main()
