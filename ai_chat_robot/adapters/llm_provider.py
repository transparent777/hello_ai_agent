"""DeepSeek/OpenAI SDK adapter.

This module owns SDK client construction. Configuration parsing remains in
``config`` and application code consumes the exported model objects only.
"""

from __future__ import annotations

import os
import sys

from agents import (
    AsyncOpenAI,
    ModelSettings,
    OpenAIChatCompletionsModel,
    OpenAIProvider,
    set_tracing_disabled,
)

from services.tracing import TRACING_ENABLED, configure_tracing

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_FLASH = "deepseek-v4-flash"
DEEPSEEK_PRO = "deepseek-v4-pro"
KNOWN_MODELS = frozenset({DEEPSEEK_FLASH, DEEPSEEK_PRO})
SANDBOX_AGENT_SUPPORTED = False

api_key = os.getenv("DEEPSEEK_API_KEY")
if not api_key:
    raise SystemExit(
        "未检测到 DEEPSEEK_API_KEY。请在 .env 里填入：\n"
        "DEEPSEEK_API_KEY=你的DeepSeek密钥"
    )

set_tracing_disabled(not TRACING_ENABLED)
configure_tracing()

deepseek_provider = OpenAIProvider(
    api_key=api_key,
    base_url=DEEPSEEK_BASE_URL,
    use_responses=False,
)
deepseek_client = AsyncOpenAI(api_key=api_key, base_url=DEEPSEEK_BASE_URL)

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

__all__ = [
    "DEEPSEEK_BASE_URL",
    "DEEPSEEK_FLASH",
    "DEEPSEEK_PRO",
    "KNOWN_MODELS",
    "SANDBOX_AGENT_SUPPORTED",
    "deepseek_provider",
    "flash_model",
    "flash_settings",
    "pro_model",
    "pro_settings",
    "PROCESS_DEFAULT_MODEL",
]
