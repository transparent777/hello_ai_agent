"""Sandbox 与 Web 运维相关配置（环境变量）。"""

from __future__ import annotations

import os
from pathlib import Path

from config.paths import LOGS_DIR, PACKAGE_ROOT

SANDBOX_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    return int(raw)


# --- P0: 安全与沙箱策略 ---
SANDBOX_ALLOW_LOCAL_FALLBACK = _env_bool("SANDBOX_ALLOW_LOCAL_FALLBACK", False)
SANDBOX_REQUIRE_DOCKER = _env_bool("SANDBOX_REQUIRE_DOCKER", True)
SANDBOX_DOCKER_IMAGE = os.getenv("SANDBOX_DOCKER_IMAGE", "python:3.11-slim")
SANDBOX_PIN_IMAGE_DIGEST = _env_bool("SANDBOX_PIN_IMAGE_DIGEST", True)
SANDBOX_MAX_CONCURRENT_SESSIONS = _env_int("SANDBOX_MAX_CONCURRENT_SESSIONS", 2)
SANDBOX_EXEC_TIMEOUT_SECONDS = _env_int("SANDBOX_EXEC_TIMEOUT_SECONDS", 120)
SANDBOX_CLEANUP_ON_STARTUP = _env_bool("SANDBOX_CLEANUP_ON_STARTUP", True)
SANDBOX_STALE_CONTAINER_MAX_AGE_HOURS = _env_int("SANDBOX_STALE_CONTAINER_MAX_AGE_HOURS", 24)

# --- P0: Web 认证 ---
WEB_APP_API_KEY = os.getenv("WEB_APP_API_KEY", "").strip()

# --- P1: 可靠性 ---
SANDBOX_RUN_TIMEOUT_SECONDS = _env_int("SANDBOX_RUN_TIMEOUT_SECONDS", 300)
SANDBOX_RUN_MAX_RETRIES = _env_int("SANDBOX_RUN_MAX_RETRIES", 2)
SANDBOX_HEALTH_CHECK_ON_STARTUP = _env_bool("SANDBOX_HEALTH_CHECK_ON_STARTUP", True)

# --- 产物审查 ---
ARTIFACT_MAX_BYTES = _env_int("SANDBOX_ARTIFACT_MAX_BYTES", 10 * 1024 * 1024)

# --- E: 沙箱持久化与记忆 ---
SANDBOX_PERSIST_SESSION = _env_bool("SANDBOX_PERSIST_SESSION", True)
SANDBOX_MEMORY_ENABLED = _env_bool("SANDBOX_MEMORY_ENABLED", True)
SANDBOX_PERSIST_ROOT = Path(
    os.getenv("SANDBOX_PERSIST_ROOT", str(SANDBOX_DIR / "persist"))
)

# --- 审计与指标 ---
AUDIT_LOG_PATH = Path(
    os.getenv("SANDBOX_AUDIT_LOG", str(LOGS_DIR / "sandbox_audit.jsonl"))
)
METRICS_LOG_PATH = Path(
    os.getenv("SANDBOX_METRICS_LOG", str(LOGS_DIR / "sandbox_metrics.jsonl"))
)
