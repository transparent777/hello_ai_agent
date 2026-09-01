"""本地 stdio MCP 服务：把电商查询工具暴露给 Agent（私有、可过滤/审批）。"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv

load_dotenv(_ROOT / ".env")
load_dotenv(_ROOT.parent / ".env")

from ecommerce_tools import get_order_status_impl, search_products_impl
from mcp.server.mcpserver import MCPServer

server = MCPServer("ecommerce-local-mcp")


@server.tool(name="search_products", description="按关键词搜索商品目录")
def mcp_search_products(keyword: str) -> str:
    return search_products_impl(keyword)


@server.tool(name="get_order_status", description="查询订单状态与物流")
def mcp_get_order_status(order_id: str) -> str:
    return get_order_status_impl(order_id)


if __name__ == "__main__":
    server.run(transport="stdio")
