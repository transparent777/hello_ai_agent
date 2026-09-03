"""专员 handoff 回协调层（复杂任务汇总）。"""

from __future__ import annotations


def apply_handoff_links() -> None:
    from specialists.router import workspace_router
    from specialists.data import data_specialist
    from specialists.document import document_specialist
    from specialists.writer import writer_specialist

    for specialist in (document_specialist, writer_specialist, data_specialist):
        if specialist is None:
            continue
        existing = list(getattr(specialist, "handoffs", None) or [])
        if workspace_router not in existing:
            specialist.handoffs = [*existing, workspace_router]
