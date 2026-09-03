"""工作台前台：层级 ReAct 协调层（L1）— 判断、派发、验收、终稿。"""

from __future__ import annotations

from functools import partial

from agents import Agent, handoff

from specialists.data import data_specialist
from specialists.document import document_specialist
from specialists.writer import writer_specialist
from guardrails import (
    GUARDRAILS_ENABLED,
    ROUTER_INPUT_GUARDRAILS,
    ROUTER_OUTPUT_GUARDRAILS,
)
from adapters.llm_provider import flash_settings
from config.settings import ROUTER_VERIFY_MAX_RETRIES
from orchestrator.handoff_policy import can_router_dispatch_specialist


def _dispatch_gate(specialist_name: str, _ctx: object, calling_agent: object) -> bool:
    _ = calling_agent
    return can_router_dispatch_specialist(
        _ctx,
        calling_agent,
        specialist_name=specialist_name,
    )


def _router_handoffs() -> list:
    agents: list = []
    if document_specialist is not None:
        agents.append(
            handoff(
                document_specialist,
                is_enabled=partial(_dispatch_gate, document_specialist.name),
            )
        )
    if writer_specialist is not None:
        agents.append(
            handoff(
                writer_specialist,
                is_enabled=partial(_dispatch_gate, writer_specialist.name),
            )
        )
    agents.append(
        handoff(
            data_specialist,
            is_enabled=partial(_dispatch_gate, data_specialist.name),
        )
    )
    return agents


def _router_instructions() -> str:
    lines = [
        "你是通用工作台协调员（层级 ReAct · L1）。职责：**判断 → 派发 → 验收 → 对用户终稿**。",
        "你只能 transfer_to_* 或直接回复，禁止调用 read_file / export_docx 等业务工具。",
        "",
        "## 工作流（必须遵守）",
        "",
        "### ① 判断（Thought）",
        "- 闲聊、解释、短文案（≤3 段）、无文件需求 → **L1 直接 Markdown 终稿**，不 handoff。",
        "- 需要读文件、导出 csv/xlsx/docx、长文写作、数据分析 → 进入 ②。",
        "",
        "### ② 派发（Action）",
        "- **信息不足**（如缺作文主题、课程要求、数据范围）→ 先用中文与用户对齐 1～3 个关键问题，"
        "可自然说明将交给哪位专员处理；**本轮不 handoff**。",
        "- **信息已足够** → 调用 transfer_to_* handoff；专员执行期间不要向用户直播中间过程。",
        "- document：读文件 / 表格导出",
        "- writer：长文、计划表、思政文、docx",
        "- data：统计脚本、报表",
        "",
        "### ③ 验收（Observation）",
        "- 专员 transfer_to_workspace_router 回传后，检查是否满足用户要求：",
        "  · docx/csv/xlsx：工具是否成功、是否给出 exports/ 路径",
        "  · 分析：是否有关键结论与产物路径",
        "- **验收通过** → ④ 对用户终稿（路径 + 简短摘要）。",
        "  **本轮禁止再次调用任何 transfer_to_*（一票终稿，避免回环）。**",
        f"- **验收不通过** → 最多再派发 {ROUTER_VERIFY_MAX_RETRIES} 次，并说明缺什么。",
        "",
        "### ④ 终稿（Final Answer）",
        "- **仅用中文**输出：文件路径、内容摘要、可选建议。",
        "- 不要重复专员的全文，不要输出英文内心独白或 DSML/工具调用原文。",
        "",
        "### 禁止",
        "- 「转接失败」「似乎没有产生实际效果」「让我再转接」等话术",
        "- 验收已通过仍再次 handoff（避免 Router↔专员死循环）",
    ]
    if document_specialist is None:
        lines.append("注意：FILE_AGENT_ENABLED=false，文件/写作专员不可用。")
    return "\n".join(lines)


workspace_router = Agent(
    name="workspace_router",
    instructions=_router_instructions(),
    handoffs=_router_handoffs(),
    model_settings=flash_settings,
    input_guardrails=ROUTER_INPUT_GUARDRAILS if GUARDRAILS_ENABLED else [],
    output_guardrails=ROUTER_OUTPUT_GUARDRAILS if GUARDRAILS_ENABLED else [],
)

customer_service_router = workspace_router
