"""文件 Agent 配置：宿主机工作区路径与大小限制。"""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

_DEFAULT_WORKSPACE = PROJECT_ROOT / "workspace_user"


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name, "true" if default else "false").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        return int(raw)
    except ValueError:
        return default


FILE_AGENT_ENABLED = _env_bool("FILE_AGENT_ENABLED", True)

_workspace_raw = os.getenv("FILE_AGENT_WORKSPACE", "").strip()
FILE_AGENT_WORKSPACE = (
    Path(_workspace_raw).expanduser().resolve()
    if _workspace_raw
    else _DEFAULT_WORKSPACE.resolve()
)

FILE_AGENT_MAX_READ_BYTES = _env_int("FILE_AGENT_MAX_READ_BYTES", 1_048_576)
FILE_AGENT_MAX_WRITE_BYTES = _env_int("FILE_AGENT_MAX_WRITE_BYTES", 524_288)
FILE_AGENT_MAX_LIST_ENTRIES = _env_int("FILE_AGENT_MAX_LIST_ENTRIES", 200)

# 禁止读取/写入的相对路径片段（小写比较）
FILE_AGENT_BLOCKED_NAME_PATTERNS = (
    ".env",
    ".git",
    "sessions.db",
    "id_rsa",
    "credentials",
    "secret",
)
