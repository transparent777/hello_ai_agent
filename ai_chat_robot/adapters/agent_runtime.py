"""Agent Runtime adapter: SDK RunConfig plus optional Docker sandbox."""

from __future__ import annotations

import os
from typing import Any

from agents import RunConfig

from adapters.llm_provider import KNOWN_MODELS, deepseek_provider
from config.paths import PACKAGE_ROOT
from config.settings import MAX_TURNS, SESSION_ID
from sandbox.config import merge_run_config_with_sandbox
from sandbox.health import check_sandbox_health
from sandbox.runtime import ensure_workspace_synced, is_docker_available
from sandbox.session_store import save_sandbox_resume_payload
from sandbox.settings import (
    SANDBOX_HEALTH_CHECK_ON_STARTUP,
    SANDBOX_PERSIST_SESSION,
)
from services.tracing import TRACING_ENABLED

APP_DIR = PACKAGE_ROOT
SANDBOX_AGENT_SUPPORTED = False


def build_run_config(
    run_model: str | None = None,
    *,
    with_sandbox: bool | None = None,
    session_id: str | None = None,
) -> RunConfig:
    model_name = run_model or os.getenv("RUN_DEFAULT_MODEL") or "deepseek-v4-flash"
    if model_name not in KNOWN_MODELS:
        raise ValueError(f"未知模型 {model_name!r}，请使用 {sorted(KNOWN_MODELS)}")

    base = RunConfig(
        model_provider=deepseek_provider,
        model=model_name,
        tracing_disabled=not TRACING_ENABLED,
        tool_not_found_behavior="return_error_to_model",
    )
    use_sandbox = is_docker_available() if with_sandbox is None else with_sandbox
    if not use_sandbox:
        return base

    ensure_workspace_synced()
    if SANDBOX_HEALTH_CHECK_ON_STARTUP:
        health = check_sandbox_health()
        if not health.ok:
            raise RuntimeError("沙箱健康检查未通过: " + "; ".join(health.issues))
    return merge_run_config_with_sandbox(
        base,
        session_id=session_id,
        persist_session=SANDBOX_PERSIST_SESSION,
    )


def persist_sandbox_session(session_id: str | None, result: Any) -> None:
    if not session_id or not SANDBOX_PERSIST_SESSION or result is None:
        return
    try:
        run_state = result.to_state()
        sandbox_payload = run_state._sandbox
        if isinstance(sandbox_payload, dict):
            save_sandbox_resume_payload(session_id, sandbox_payload)
    except Exception:
        # Persistence must not turn a completed Agent turn into a failure.
        pass


__all__ = [
    "APP_DIR",
    "MAX_TURNS",
    "SESSION_ID",
    "build_run_config",
    "persist_sandbox_session",
]
