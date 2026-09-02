"""多 Agent 定义与注册表。"""

from specialists.analytics import analytics_specialist
from specialists.file import file_specialist
from specialists.order import order_specialist
from specialists.product import product_specialist
from specialists.registry import AGENT_REGISTRY, get_agent_by_name
from specialists.router import customer_service_router

__all__ = [
    "AGENT_REGISTRY",
    "analytics_specialist",
    "customer_service_router",
    "file_specialist",
    "get_agent_by_name",
    "order_specialist",
    "product_specialist",
]
