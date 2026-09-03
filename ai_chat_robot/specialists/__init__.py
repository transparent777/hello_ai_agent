"""多 Agent 定义与注册表。"""

from specialists.data import analytics_specialist, data_specialist
from specialists.document import document_specialist, file_specialist
from specialists.registry import AGENT_REGISTRY, get_agent_by_name
from specialists.router import customer_service_router, workspace_router

__all__ = [
    "AGENT_REGISTRY",
    "analytics_specialist",
    "customer_service_router",
    "data_specialist",
    "document_specialist",
    "file_specialist",
    "get_agent_by_name",
    "workspace_router",
]
