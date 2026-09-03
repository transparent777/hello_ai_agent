"""数据专员：统计分析、报表生成与脚本化处理（Docker 沙箱）。"""

from __future__ import annotations

from agents import Agent

from config.llm import pro_model, pro_settings, SANDBOX_AGENT_SUPPORTED
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


def create_data_specialist() -> Agent:
    shared_instructions = (
        "你是数据处理与报表专员。根据用户需求在沙箱中执行分析脚本：\n"
        "- 数据集统计、分布分析 → run_order_analysis（读取 data/ 下示例 JSON）\n"
        "- 参数化模拟（如折扣）→ run_pricing_simulation\n"
        "- 生成 Markdown 报表 → run_sales_report\n"
        "开始前阅读 repo/task.md；若存在 memories/memory_summary.md 可参考历史结论。\n"
        "用中文解释关键数字，并说明产物路径（如 output/report.md、reports/）。\n"
        "复杂多步任务完成后，可 transfer_to_workspace_router 请 L1 汇总。"
    )

    if is_docker_available() and SANDBOX_AGENT_SUPPORTED:
        from agents.sandbox import SandboxAgent

        ensure_workspace_synced()
        return SandboxAgent(
            name="data_specialist",
            handoff_description=(
                "统计分析、批量数据处理、生成报表（Docker 沙箱内跑 Python 脚本）。"
            ),
            instructions=f"{SANDBOX_INSTRUCTIONS}\n\n{shared_instructions}",
            model=pro_model,
            model_settings=pro_settings,
            default_manifest=build_manifest(),
            capabilities=build_sandbox_capabilities(),
        )

    if is_docker_available() or SANDBOX_ALLOW_LOCAL_FALLBACK:
        return Agent(
            name="data_specialist",
            handoff_description=(
                "统计分析、批量数据处理、生成报表（Docker 沙箱或本机脚本）。"
            ),
            instructions=(
                f"{shared_instructions}\n"
                "使用 run_order_analysis / run_pricing_simulation / run_sales_report，"
                "不要假装已经执行脚本。"
            ),
            tools=[run_order_analysis, run_pricing_simulation, run_sales_report],
            model=pro_model,
            model_settings=pro_settings,
        )

    return Agent(
        name="data_specialist",
        handoff_description="数据处理需要 Docker 沙箱，当前环境不可用。",
        instructions=(
            "你是数据处理专员，但当前 Docker 沙箱不可用。\n"
            "请明确告知用户：需要启动 Docker Desktop 后才能跑统计分析或生成报表。\n"
            "不要假装已经执行脚本或编造分析结果。"
        ),
        model=pro_model,
        model_settings=pro_settings,
    )


data_specialist = create_data_specialist()

# 兼容旧名称
analytics_specialist = data_specialist
