"""The chat-turn use case, independent from Streamlit and terminal I/O."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, TypeAlias

ChatTurnRunner: TypeAlias = Callable[..., Awaitable[tuple[str | None, Any | None, list[Any]]]]


class ChatTurnService:
    """Execute one Agent turn through an injected runtime implementation."""

    def __init__(self, runner: ChatTurnRunner) -> None:
        self._runner = runner

    async def execute(
        self,
        agent: Any,
        prompt: str,
        session: Any,
        run_config: Any,
        *,
        on_delta: Callable[[str], None] | None = None,
        on_react_step: Callable[[Any], None] | None = None,
    ) -> tuple[str | None, Any | None, list[Any]]:
        return await self._runner(
            agent,
            prompt,
            session,
            run_config,
            on_delta=on_delta,
            on_react_step=on_react_step,
        )
