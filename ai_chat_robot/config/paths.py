"""项目路径常量（单一来源）。"""

from __future__ import annotations

from pathlib import Path

# ai_chat_robot/
PACKAGE_ROOT = Path(__file__).resolve().parent.parent
# ai agent/
REPO_ROOT = PACKAGE_ROOT.parent

DATA_DIR = PACKAGE_ROOT / "data"
LOGS_DIR = PACKAGE_ROOT / "logs"
WORKSPACE_USER_DIR = PACKAGE_ROOT / "workspace_user"
SESSION_DB = PACKAGE_ROOT / "sessions.db"
EVAL_DIR = PACKAGE_ROOT / "eval"
