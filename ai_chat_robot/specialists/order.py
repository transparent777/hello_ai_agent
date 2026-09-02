"""订单与售后专员。"""

from __future__ import annotations

from agents import Agent

from guardrails import GUARDRAILS_ENABLED, SPECIALIST_OUTPUT_GUARDRAILS
from config.llm import pro_model, pro_settings
from tools.ecommerce import get_order_status, process_refund

order_specialist = Agent(
    name="order_specialist",
    handoff_description="处理订单查询、物流跟踪、退换货与售后问题。",
    instructions=(
        "你是电商订单与售后专员。帮用户查订单、解释物流状态，"
        "处理退换货规则说明。需要订单详情时调用订单查询工具；"
        "用户明确要求退款时调用退款工具（会进入人工审批）。"
    ),
    tools=[get_order_status, process_refund],
    model=pro_model,
    model_settings=pro_settings,
    output_guardrails=SPECIALIST_OUTPUT_GUARDRAILS if GUARDRAILS_ENABLED else [],
)
