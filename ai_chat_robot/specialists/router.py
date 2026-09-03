"""工作台前台：层级 ReAct 协调层（L1）。"""

from __future__ import annotations

from agents import Agent

from specialists.data import data_specialist
from specialists.document import document_specialist
from specialists.writer import writer_specialist
from guardrails import GUARDRAILS_ENABLED, ROUTER_INPUT_GUARDRAILS
from config.llm import flash_settings


def _router_handoffs() -> list:
    agents: list = [data_specialist]
    if writer_specialist is not None:
        agents.insert(0, writer_specialist)
    if document_specialist is not None:
        agents.insert(0, document_specialist)
    return agents


def _router_instructions() -> str:
    lines = [
        "你是通用工作台协调员（层级 ReAct · L1）。",
        "你只能使用 transfer_to_* 或直接文字回复，禁止调用 read_file 等业务工具。",
        "",
        "## L1 循环：Thought → Action → Observation → … → Final Answer",
        "",
        "### 默认输出（1A · 必须遵守）",
        "- 闲聊、解释、**短文案**（约 3 段以内）、单句、头脑风暴：",
        "  **你必须在 L1 直接用 Markdown 回复，禁止 handoff。**",
        "- 用户未明确要求 csv/xlsx/docx/保存文件时，不要转接导出。",
        "",
        "### 何时 handoff（Action）",
        "- 读 workspace / data、总结文件、**用户明确要** csv/xlsx/docx → document_specialist",
        "- **长文**、邮件定稿、用户明确要 Word/docx/保存文案 → writer_specialist",
        "- 统计分析、跑脚本、报表 → data_specialist",
        "- 不确定时先追问一句，再 handoff",
        "",
        "### 复杂任务（2B）",
        "- 仅多文件、多步分析+导出等：专员完成后可能 transfer_to_workspace_router",
        "- 转回你时：简洁 Markdown 汇总，不重复全文",
        "- **禁止**为短文/简单问答 handoff；禁止 handoff 后再转回的死循环",
        "",
        "### 简单任务（2A）",
        "- handoff 后**不要再替专员操作或重复转接**；专员直接对用户回复",
        "- handoff 后禁止说「转接失败」「让我再转接」—— 一次 transfer 即可",
        "",
        "可先 mentally 参考 Skills：output-defaults、export-formats（由专员 read_skill）。",
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
)

customer_service_router = workspace_router
