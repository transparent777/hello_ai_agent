"""Approval use case shared by Web and CLI adapters."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, TypeAlias

ApprovalRunner: TypeAlias = Callable[..., Awaitable[tuple[str, Any]]]


class ApprovalService:
    """Apply an approval decision through an injected orchestration runtime."""

    def __init__(self, runner: ApprovalRunner) -> None:
        self._runner = runner

    async def decide(
        self,
        pending: Any,
        session: Any,
        run_config: Any,
        *,
        approved: bool,
        on_delta: Callable[[str], None] | None = None,
    ) -> tuple[str, Any]:
        return await self._runner(
            pending,
            session,
            run_config,
            approved=approved,
            on_delta=on_delta,
        )
