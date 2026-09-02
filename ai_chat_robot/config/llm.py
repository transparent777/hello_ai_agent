"""LLM 提供商、模型与 RunConfig 构建。"""

from __future__ import annotations

import os
import sys
from typing import Any

from agents import (
    AsyncOpenAI,
    ModelSettings,
    OpenAIChatCompletionsModel,
    OpenAIProvider,
    RunConfig,
    set_tracing_disabled,
)

from config.paths import PACKAGE_ROOT, SESSION_DB
from config.settings import MAX_TURNS, SESSION_ID
from sandbox.config import merge_run_config_with_sandbox
from sandbox.health import check_sandbox_health
from sandbox.runtime import ensure_workspace_synced, is_docker_available
from sandbox.session_store import save_sandbox_resume_payload
from sandbox.settings import (
    SANDBOX_HEALTH_CHECK_ON_STARTUP,
    SANDBOX_PERSIST_SESSION,
)
from services.tracing import TRACING_ENABLED, configure_tracing

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

api_key = os.getenv("DEEPSEEK_API_KEY")
if not api_key:
    raise SystemExit(
        "未检测到 DEEPSEEK_API_KEY。请在 .env 里填入：\n"
        "DEEPSEEK_API_KEY=你的DeepSeek密钥"
    )

set_tracing_disabled(not TRACING_ENABLED)
configure_tracing()

DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_FLASH = "deepseek-v4-flash"
DEEPSEEK_PRO = "deepseek-v4-pro"
KNOWN_MODELS = frozenset({DEEPSEEK_FLASH, DEEPSEEK_PRO})

deepseek_provider = OpenAIProvider(
    api_key=api_key,
    base_url=DEEPSEEK_BASE_URL,
    use_responses=False,
)

deepseek_client = AsyncOpenAI(
    api_key=api_key,
    base_url=DEEPSEEK_BASE_URL,
)

flash_model = OpenAIChatCompletionsModel(
    model=DEEPSEEK_FLASH,
    openai_client=deepseek_client,
)
pro_model = OpenAIChatCompletionsModel(
    model=DEEPSEEK_PRO,
    openai_client=deepseek_client,
)

flash_settings = ModelSettings(
    temperature=0.3,
    extra_body={"thinking": {"type": "disabled"}},
)
pro_settings = ModelSettings(
    temperature=0.3,
    extra_body={"thinking": {"type": "disabled"}},
)

PROCESS_DEFAULT_MODEL = os.getenv("DEEPSEEK_DEFAULT_MODEL") or DEEPSEEK_FLASH
os.environ.setdefault("OPENAI_DEFAULT_MODEL", PROCESS_DEFAULT_MODEL)

APP_DIR = PACKAGE_ROOT


def build_run_config(
    run_model: str | None = None,
    *,
    with_sandbox: bool | None = None,
    session_id: str | None = None,
) -> RunConfig:
    model_name = run_model or os.getenv("RUN_DEFAULT_MODEL") or PROCESS_DEFAULT_MODEL
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
    """保存沙箱 resume 状态（供下次 run 或审批后恢复）。"""
    if not session_id or not SANDBOX_PERSIST_SESSION or result is None:
        return
    try:
        run_state = result.to_state()
        sandbox_payload = run_state._sandbox
        if isinstance(sandbox_payload, dict):
            save_sandbox_resume_payload(session_id, sandbox_payload)
    except Exception:
        pass
