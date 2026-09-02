"""商品咨询专员。"""

from __future__ import annotations

from agents import Agent

from guardrails import GUARDRAILS_ENABLED, SPECIALIST_OUTPUT_GUARDRAILS
from mcp_integration.runtime import build_hosted_mcp_tools, build_local_mcp_servers
from mcp_integration.settings import MCP_HOSTED_ENABLED, MCP_LOCAL_ENABLED
from config.llm import flash_model, flash_settings
from tools.ecommerce import search_products


def create_product_specialist() -> Agent:
    tools: list = []
    if not MCP_LOCAL_ENABLED:
        tools.append(search_products)
    if MCP_HOSTED_ENABLED:
        tools.extend(build_hosted_mcp_tools())
    mcp_hint = (
        "商品数据可通过 MCP 工具 search_products 查询（本地私有 MCP 或托管 MCP）。"
        if MCP_LOCAL_ENABLED or MCP_HOSTED_ENABLED
        else "需要查商品时调用 search_products，"
    )
    return Agent(
        name="product_specialist",
        handoff_description="处理商品咨询、比价、推荐与库存查询。",
        instructions=(
            "你是电商商品顾问。根据用户需求推荐合适商品，说明价格与库存。"
            f"{mcp_hint}"
            "回答简洁、有购买引导。"
        ),
        tools=tools,
        mcp_servers=build_local_mcp_servers() if MCP_LOCAL_ENABLED else [],
        model=flash_model,
        model_settings=flash_settings,
        output_guardrails=SPECIALIST_OUTPUT_GUARDRAILS if GUARDRAILS_ENABLED else [],
    )


product_specialist = create_product_specialist()
