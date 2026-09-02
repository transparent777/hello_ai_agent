"""客服前台：只分流，不直接调用业务工具。"""

from __future__ import annotations

from agents import Agent

from specialists.analytics import analytics_specialist
from specialists.file import file_specialist
from specialists.order import order_specialist
from specialists.product import product_specialist
from guardrails import GUARDRAILS_ENABLED, ROUTER_INPUT_GUARDRAILS
from config.llm import flash_settings


def _router_handoffs() -> list:
    agents = [product_specialist, order_specialist, analytics_specialist]
    if file_specialist is not None:
        agents.append(file_specialist)
    return agents


def _router_instructions() -> str:
    lines = [
        "你是电商客服前台，只负责分流，不直接查订单或商品。",
        "你当前只能使用 transfer_to_* 转接工具，禁止调用任何业务工具。",
        "规则：",
        "1. 商品/推荐/库存 → 必须 transfer_to_product_specialist",
        "2. 订单/物流/退换货/售后 → 必须 transfer_to_order_specialist",
        "3. 数据分析/报表/定价模拟 → 必须 transfer_to_analytics_specialist",
    ]
    if file_specialist is not None:
        lines.append(
            "4. 导出 CSV/Excel 清单、查看 JSON、读写 workspace 文件 → transfer_to_file_specialist"
        )
        lines.append("5. 即使对话历史里出现过查询，新消息仍必须先转接，不能代查")
        lines.append("6. 仅简单问候可自行回复")
    else:
        lines.append("4. 即使对话历史里出现过查询，新消息仍必须先转接，不能代查")
        lines.append("5. 仅简单问候可自行回复")
    return "\n".join(lines)


customer_service_router = Agent(
    name="customer_service_router",
    instructions=_router_instructions(),
    handoffs=_router_handoffs(),
    model_settings=flash_settings,
    input_guardrails=ROUTER_INPUT_GUARDRAILS if GUARDRAILS_ENABLED else [],
)
