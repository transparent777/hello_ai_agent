"""MCP 集成：托管式与本地/私有式服务器配置。"""

from mcp_integration.runtime import (
    build_hosted_mcp_tools,
    build_local_mcp_servers,
    collect_mcp_servers_from_agents,
    mcp_status_summary,
    run_with_mcp_lifecycle,
)

__all__ = [
    "build_hosted_mcp_tools",
    "build_local_mcp_servers",
    "collect_mcp_servers_from_agents",
    "mcp_status_summary",
    "run_with_mcp_lifecycle",
]
