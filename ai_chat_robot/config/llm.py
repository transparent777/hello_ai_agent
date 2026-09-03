"""Backward-compatible exports for the LLM/runtime adapters.

New code should import SDK clients from ``adapters.llm_provider`` and runtime
construction from ``adapters.agent_runtime``. This module remains temporarily
so existing specialist and script imports continue to work during migration.
"""

from adapters.agent_runtime import (
    APP_DIR,
    MAX_TURNS,
    SESSION_ID,
    build_run_config,
    persist_sandbox_session,
)
from adapters.llm_provider import (
    DEEPSEEK_BASE_URL,
    DEEPSEEK_FLASH,
    DEEPSEEK_PRO,
    KNOWN_MODELS,
    PROCESS_DEFAULT_MODEL,
    SANDBOX_AGENT_SUPPORTED,
    deepseek_provider,
    flash_model,
    flash_settings,
    pro_model,
    pro_settings,
)
from config.paths import SESSION_DB

__all__ = [
    "APP_DIR",
    "DEEPSEEK_BASE_URL",
    "DEEPSEEK_FLASH",
    "DEEPSEEK_PRO",
    "KNOWN_MODELS",
    "MAX_TURNS",
    "PROCESS_DEFAULT_MODEL",
    "SANDBOX_AGENT_SUPPORTED",
    "SESSION_DB",
    "SESSION_ID",
    "build_run_config",
    "deepseek_provider",
    "flash_model",
    "flash_settings",
    "persist_sandbox_session",
    "pro_model",
    "pro_settings",
]
