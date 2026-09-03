"""Agent 注册表。"""

from __future__ import annotations

from agents import Agent

from specialists.data import data_specialist
from specialists.document import document_specialist
from specialists.writer import writer_specialist
from specialists.router import workspace_router
from specialists.wiring import apply_handoff_links

apply_handoff_links()

AGENT_REGISTRY: dict[str, Agent] = {
    "workspace_router": workspace_router,
    "data_specialist": data_specialist,
}
if document_specialist is not None:
    AGENT_REGISTRY["document_specialist"] = document_specialist
if writer_specialist is not None:
    AGENT_REGISTRY["writer_specialist"] = writer_specialist

AGENT_REGISTRY["customer_service_router"] = workspace_router
AGENT_REGISTRY["analytics_specialist"] = data_specialist
if document_specialist is not None:
    AGENT_REGISTRY["file_specialist"] = document_specialist


def get_agent_by_name(name: str) -> Agent:
    agent = AGENT_REGISTRY.get(name)
    if agent is None:
        raise ValueError(f"未知 Agent：{name!r}")
    return agent
