"""MCP 运行时：构建服务器、生命周期、状态摘要。"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from agents import Agent
from agents.tool import HostedMCPTool

from mcp_integration.settings import (
    MCP_HOSTED_ENABLED,
    MCP_HOSTED_REQUIRE_APPROVAL,
    MCP_HOSTED_SERVER_DESCRIPTION,
    MCP_HOSTED_SERVER_LABEL,
    MCP_HOSTED_SERVER_URL,
    MCP_LOCAL_APPROVAL_TOOLS,
    MCP_LOCAL_ENABLED,
    MCP_LOCAL_SERVER_NAME,
    MCP_LOCAL_TOOL_ALLOWLIST,
    MCP_SERVERS_DIR,
)
from sandbox.audit import log_audit_event

T = TypeVar("T")

_local_mcp_servers: list[Any] | None = None


def build_local_mcp_servers() -> list[Any]:
    """本地 stdio MCP：运行时掌控连接、工具过滤与审批策略。"""
    global _local_mcp_servers
    if not MCP_LOCAL_ENABLED:
        return []
    if _local_mcp_servers is not None:
        return _local_mcp_servers

    from agents.mcp import MCPServerStdio, create_static_tool_filter

    server_script = MCP_SERVERS_DIR / "ecommerce_stdio_server.py"
    approval_policy: dict[str, Any] | str = "never"
    if MCP_LOCAL_APPROVAL_TOOLS:
        approval_policy = {"always": {"tool_names": list(MCP_LOCAL_APPROVAL_TOOLS)}}

    server = MCPServerStdio(
        params={
            "command": "python",
            "args": [str(server_script)],
            "cwd": str(MCP_SERVERS_DIR.parent),
        },
        name=MCP_LOCAL_SERVER_NAME,
        cache_tools_list=True,
        tool_filter=create_static_tool_filter(
            allowed_tool_names=list(MCP_LOCAL_TOOL_ALLOWLIST),
        ),
        require_approval=approval_policy,
    )
    _local_mcp_servers = [server]
    return _local_mcp_servers


def build_hosted_mcp_tools() -> list[HostedMCPTool]:
    """托管式远程 MCP：配置 server_url 后由模型自动列举/调用工具。"""
    if not MCP_HOSTED_ENABLED or not MCP_HOSTED_SERVER_URL:
        return []

    require_approval: Any = MCP_HOSTED_REQUIRE_APPROVAL
    if require_approval not in {"always", "never"}:
        require_approval = "never"

    tool_config: dict[str, Any] = {
        "type": "mcp",
        "server_label": MCP_HOSTED_SERVER_LABEL,
        "server_url": MCP_HOSTED_SERVER_URL,
        "server_description": MCP_HOSTED_SERVER_DESCRIPTION,
        "require_approval": require_approval,
    }
    log_audit_event(
        "mcp_hosted_configured",
        status="ok",
        extra={"server_label": MCP_HOSTED_SERVER_LABEL},
    )
    return [HostedMCPTool(tool_config=tool_config)]


def collect_mcp_servers_from_agents(*agents: Agent) -> list[Any]:
    seen: set[int] = set()
    servers: list[Any] = []
    for agent in agents:
        for server in getattr(agent, "mcp_servers", []) or []:
            key = id(server)
            if key in seen:
                continue
            seen.add(key)
            servers.append(server)
    return servers


async def run_with_mcp_lifecycle(
    servers: list[Any],
    coro_factory: Callable[[], Awaitable[T]],
) -> T:
    """在 MCP connect/cleanup 生命周期内执行一次 Agent turn。"""
    if not servers:
        return await coro_factory()

    from agents.mcp import MCPServerManager

    async with MCPServerManager(servers) as manager:
        _ = manager
        return await coro_factory()


def mcp_status_summary() -> str:
    parts: list[str] = []
    if MCP_LOCAL_ENABLED:
        parts.append(f"本地 MCP（{MCP_LOCAL_SERVER_NAME}）")
    if MCP_HOSTED_ENABLED and MCP_HOSTED_SERVER_URL:
        parts.append(f"托管 MCP（{MCP_HOSTED_SERVER_LABEL}）")
    if not parts:
        return "未启用"
    return " + ".join(parts)
