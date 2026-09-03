"""层级 ReAct 模式与分层步数配置。"""

from __future__ import annotations

import os

from config.settings import SHOW_REACT_STEPS

AGENT_MODE = os.getenv("AGENT_MODE", "hierarchical").strip().lower()
ROUTER_AGENT_NAME = "workspace_router"
ROUTER_MAX_TURNS = int(os.getenv("ROUTER_MAX_TURNS", "5"))
SPECIALIST_MAX_TURNS = int(os.getenv("SPECIALIST_MAX_TURNS", "12"))
SHOW_REACT_STEPS_DEFAULT = SHOW_REACT_STEPS

_ROUTER_NAMES = frozenset({ROUTER_AGENT_NAME, "customer_service_router"})


def is_router_agent(agent_name: str | None) -> bool:
    return bool(agent_name and agent_name in _ROUTER_NAMES)


def max_turns_for_agent(agent_name: str | None) -> int:
    if is_router_agent(agent_name):
        return ROUTER_MAX_TURNS
    return SPECIALIST_MAX_TURNS


def react_layer_label(agent_name: str | None) -> str:
    return "L1" if is_router_agent(agent_name) else "L2"
