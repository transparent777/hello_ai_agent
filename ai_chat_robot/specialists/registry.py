"""Agent 注册表。"""

from __future__ import annotations

from agents import Agent

from specialists.analytics import analytics_specialist
from specialists.file import file_specialist
from specialists.order import order_specialist
from specialists.product import product_specialist
from specialists.router import customer_service_router

AGENT_REGISTRY: dict[str, Agent] = {
    "customer_service_router": customer_service_router,
    "product_specialist": product_specialist,
    "order_specialist": order_specialist,
    "analytics_specialist": analytics_specialist,
}
if file_specialist is not None:
    AGENT_REGISTRY["file_specialist"] = file_specialist


def get_agent_by_name(name: str) -> Agent:
    agent = AGENT_REGISTRY.get(name)
    if agent is None:
        raise ValueError(f"未知 Agent：{name!r}")
    return agent
