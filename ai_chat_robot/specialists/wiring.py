"""专员 → L1 回传：仅用于交付物验收，禁止无谓回环。"""

from __future__ import annotations

# 需要回 L1 验收的专员（完成工具交付后 handoff，由 Router 终稿）
_VERIFY_BACK_AGENTS = ("document_specialist", "writer_specialist", "data_specialist")


def apply_handoff_links() -> None:
    """为交付型专员挂载「回 workspace_router 验收」handoff。"""
    from specialists.router import workspace_router
    from specialists.data import data_specialist
    from specialists.document import document_specialist
    from specialists.writer import writer_specialist

    for specialist in (document_specialist, writer_specialist, data_specialist):
        if specialist is None:
            continue
        existing = list(getattr(specialist, "handoffs", None) or [])
        if workspace_router not in existing:
            specialist.handoffs = [workspace_router]
