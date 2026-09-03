"""单轮对话内的 handoff / 验收状态（供 Router is_enabled 与兜底回复）。"""

from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass, field


@dataclass
class TurnState:
    verification_received: bool = False
    specialist_dispatches: dict[str, int] = field(default_factory=dict)
    export_paths: list[str] = field(default_factory=list)

    def record_dispatch(self, specialist_name: str) -> None:
        key = specialist_name.removeprefix("transfer_to_")
        self.specialist_dispatches[key] = self.specialist_dispatches.get(key, 0) + 1

    def can_dispatch(self, specialist_name: str, *, max_retries: int) -> bool:
        if self.verification_received:
            return False
        key = specialist_name.removeprefix("transfer_to_")
        limit = 1 + max(0, max_retries)
        return self.specialist_dispatches.get(key, 0) < limit


_turn_state: ContextVar[TurnState | None] = ContextVar("turn_state", default=None)


def reset_turn_state() -> Token:
    return _turn_state.set(TurnState())


def clear_turn_state(token: Token) -> None:
    _turn_state.reset(token)


def get_turn_state() -> TurnState:
    state = _turn_state.get()
    if state is None:
        state = TurnState()
        _turn_state.set(state)
    return state
