"""文件 Agent 配置：宿主机工作区路径与大小限制。"""

from __future__ import annotations

import os
from pathlib import Path

from config.paths import DATA_DIR, PACKAGE_ROOT, WORKSPACE_USER_DIR

_DEFAULT_WORKSPACE = WORKSPACE_USER_DIR


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
FILE_AGENT_PREVIEW_MAX_LINES = _env_int("FILE_AGENT_PREVIEW_MAX_LINES", 80)
FILE_AGENT_PREVIEW_MAX_CHARS = _env_int("FILE_AGENT_PREVIEW_MAX_CHARS", 12000)

# 电商演示数据（只读）；Agent 用 data/ 前缀访问，例如 data/products.json
DATA_READ_ROOT = DATA_DIR.resolve()

FILE_AGENT_BLOCKED_NAME_PATTERNS = (
    ".env",
    ".git",
    "sessions.db",
    "id_rsa",
    "credentials",
    "secret",
)
