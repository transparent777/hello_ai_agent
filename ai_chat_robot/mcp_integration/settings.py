"""MCP 相关环境变量。"""

from __future__ import annotations

import os
from pathlib import Path

MCP_DIR = Path(__file__).resolve().parent.parent
MCP_SERVERS_DIR = MCP_DIR / "mcp_servers"


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


# --- 本地 / 私有 MCP（stdio，可过滤工具、可审批）---
MCP_LOCAL_ENABLED = _env_bool("MCP_LOCAL_ENABLED", False)
MCP_LOCAL_SERVER_NAME = os.getenv("MCP_LOCAL_SERVER_NAME", "workspace-local")
MCP_LOCAL_TOOL_ALLOWLIST = tuple(
    s.strip()
    for s in os.getenv("MCP_LOCAL_TOOL_ALLOWLIST", "").split(",")
    if s.strip()
)
# 本地 MCP 中需要人工审批的工具名（逗号分隔）
MCP_LOCAL_APPROVAL_TOOLS = tuple(
    s.strip()
    for s in os.getenv("MCP_LOCAL_APPROVAL_TOOLS", "").split(",")
    if s.strip()
)

# --- 托管式 MCP（公开远程，模型直连；需 Responses 兼容提供商）---
MCP_HOSTED_ENABLED = _env_bool("MCP_HOSTED_ENABLED", False)
MCP_HOSTED_SERVER_LABEL = os.getenv("MCP_HOSTED_SERVER_LABEL", "workspace-hosted")
MCP_HOSTED_SERVER_URL = os.getenv("MCP_HOSTED_SERVER_URL", "").strip()
MCP_HOSTED_SERVER_DESCRIPTION = os.getenv(
    "MCP_HOSTED_SERVER_DESCRIPTION",
    "远程文件/数据 MCP 服务（托管式）",
)
MCP_HOSTED_REQUIRE_APPROVAL = os.getenv("MCP_HOSTED_REQUIRE_APPROVAL", "never").strip()
