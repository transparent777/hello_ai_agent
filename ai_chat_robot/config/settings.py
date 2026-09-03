"""应用级环境变量与启动配置。"""

from __future__ import annotations

import os

from dotenv import load_dotenv

from config.paths import PACKAGE_ROOT, REPO_ROOT

load_dotenv(PACKAGE_ROOT / ".env")
load_dotenv(REPO_ROOT / ".env")


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


GUARDRAILS_ENABLED = _env_bool("GUARDRAILS_ENABLED", True)
MAX_TURNS = int(os.getenv("AGENT_MAX_TURNS", "12"))
SESSION_ID = os.getenv("FILE_AGENT_SESSION_ID", "file_agent_session")
ROUTER_VERIFY_MAX_RETRIES = int(os.getenv("ROUTER_VERIFY_MAX_RETRIES", "1"))
SHOW_REACT_STEPS = _env_bool("SHOW_REACT_STEPS", False)
