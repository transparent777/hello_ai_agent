"""数据分析专员（Docker 沙箱或本机回退）。"""

from __future__ import annotations

from agents import Agent

from config.llm import pro_model, pro_settings
from sandbox.analytics_tools import (
    run_order_analysis,
    run_pricing_simulation,
    run_sales_report,
)
from sandbox.config import (
    SANDBOX_INSTRUCTIONS,
    build_manifest,
    build_sandbox_capabilities,
)
from sandbox.runtime import ensure_workspace_synced, is_docker_available
from sandbox.settings import SANDBOX_ALLOW_LOCAL_FALLBACK


def create_analytics_specialist() -> Agent:
    shared_instructions = (
        "你是电商数据分析专员。根据用户需求：\n"
        "- 分析订单数据 → 跑订单分析\n"
        "- 定价/打折模拟 → 跑定价脚本\n"
        "- 生成报表 → 跑报表脚本\n"
        "开始前阅读 repo/task.md；若存在 memories/memory_summary.md 可参考历史分析。\n"
        "用中文总结关键数字，并说明结果文件位置（如 output/report.md）。"
    )

    if is_docker_available():
        from agents.sandbox import SandboxAgent

        ensure_workspace_synced()
        return SandboxAgent(
            name="analytics_specialist",
            handoff_description=(
                "处理订单数据分析、定价模拟、销售报表生成（Docker 沙箱）。"
            ),
            instructions=f"{SANDBOX_INSTRUCTIONS}\n\n{shared_instructions}",
            model=pro_model,
            model_settings=pro_settings,
            default_manifest=build_manifest(),
            capabilities=build_sandbox_capabilities(),
        )

    if SANDBOX_ALLOW_LOCAL_FALLBACK:
        return Agent(
            name="analytics_specialist",
            handoff_description=(
                "处理订单数据分析、定价模拟、销售报表生成（本机脚本回退）。"
            ),
            instructions=(
                f"{shared_instructions}\n"
                "使用工具 run_order_analysis / run_pricing_simulation / run_sales_report，"
                "不要假装已经执行脚本。"
            ),
            tools=[run_order_analysis, run_pricing_simulation, run_sales_report],
            model=pro_model,
            model_settings=pro_settings,
        )

    return Agent(
        name="analytics_specialist",
        handoff_description="数据分析需要 Docker 沙箱，当前环境不可用。",
        instructions=(
            "你是电商数据分析专员，但当前 Docker 沙箱不可用。\n"
            "请明确告知用户：需要启动 Docker Desktop 后才能进行订单分析、定价模拟或报表生成。\n"
            "不要假装已经执行脚本或编造分析结果。"
        ),
        model=pro_model,
        model_settings=pro_settings,
    )


analytics_specialist = create_analytics_specialist()
