"""编排层：模型配置、运行循环、审批恢复。"""

from config.llm import (
    APP_DIR,
    DEEPSEEK_FLASH,
    DEEPSEEK_PRO,
    SESSION_DB,
    SESSION_ID,
    build_run_config,
    persist_sandbox_session,
)
from orchestrator.runner import (
    apply_approval_decision,
    capture_pending_approval,
    describe_interruptions,
    handle_user_turn,
    resolve_interruptions,
    resume_from_state,
    run_streamed_turn,
)
from services.approval_store import load_pending_approval

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
