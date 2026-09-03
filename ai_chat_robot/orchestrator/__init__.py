"""编排层：模型配置、运行循环、审批恢复。"""

from importlib import import_module

from adapters.agent_runtime import (
    APP_DIR,
    SESSION_ID,
    build_run_config,
    persist_sandbox_session,
)
from adapters.llm_provider import DEEPSEEK_FLASH, DEEPSEEK_PRO
from config.paths import SESSION_DB
from services.approval_store import load_pending_approval

_RUNNER_EXPORTS = {
    "apply_approval_decision",
    "capture_pending_approval",
    "describe_interruptions",
    "handle_user_turn",
    "resolve_interruptions",
    "resume_from_state",
    "run_streamed_turn",
}


def __getattr__(name: str):
    """Load Runner lazily to avoid a specialists/router import cycle."""
    if name in _RUNNER_EXPORTS:
        runner = import_module(".runner", __name__)
        return getattr(runner, name)
    raise AttributeError(name)

__all__ = [
    "APP_DIR",
    "DEEPSEEK_FLASH",
    "DEEPSEEK_PRO",
    "SESSION_DB",
    "SESSION_ID",
    "apply_approval_decision",
    "build_run_config",
    "capture_pending_approval",
    "describe_interruptions",
    "handle_user_turn",
    "persist_sandbox_session",
    "resolve_interruptions",
    "resume_from_state",
    "run_streamed_turn",
    "restore_pending_approval",
]


def restore_pending_approval(session_id: str):
    """从磁盘恢复待审批快照（Web 刷新/切换会话后调用）。"""
    return load_pending_approval(session_id)
