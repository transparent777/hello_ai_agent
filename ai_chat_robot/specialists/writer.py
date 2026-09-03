"""写作专员：文案、讨论与按需导出 Word。"""

from __future__ import annotations

from agents import Agent

from config.file_agent import FILE_AGENT_ENABLED
from guardrails import GUARDRAILS_ENABLED, SPECIALIST_OUTPUT_GUARDRAILS
from config.llm import pro_model, pro_settings
from tools.file import ensure_workspace
from tools.registry import WRITER_TOOLS

_REACT_SUFFIX = (
    "\n\n## 层级 ReAct（L2）\n"
    "每步：Thought（简短）→ Action（工具）→ Observation（工具返回）。\n"
    "- 默认在对话中用 Markdown 回复，不主动落盘。\n"
    "- 用户明确要求 Word/保存文件时，用 export_docx 或 write_file。\n"
    "- 不确定格式时先 read_skill('output-defaults')。\n"
    "- 简单任务：直接 Final Answer。\n"
    "- 复杂任务（多版本长文、需 L1 综合）：完成后才可 transfer_to_workspace_router。"
)


def create_writer_specialist() -> Agent | None:
    if not FILE_AGENT_ENABLED:
        return None
    ensure_workspace()
    return Agent(
        name="writer_specialist",
        handoff_description=(
            "长文案、邮件定稿；用户明确要求 Word/docx 或保存到文件时使用。"
            "短句/闲聊不要转接。"
        ),
        instructions=(
            "你是写作与内容专员，擅长中文表达与结构化文案。\n"
            "能力：\n"
            "- 对话中直接用 Markdown 输出草稿（默认）\n"
            "- 用户要求 Word → export_docx\n"
            "- 用户要求保存 md/txt → write_file（需审批）\n"
            "- 可参考 workspace 已有文件（read_file）\n"
            "- 写作前可 read_skill('writing-style') 与 output-defaults\n"
            "规则：\n"
            "- 不要编造用户未提供的文件内容\n"
            "- 未要求落盘时，不要调用 write_file / export_docx\n"
            "- 简单短文任务不应 handoff 到你；若被误转接，直接输出文案即可，"
            "**不要** transfer_to_workspace_router\n"
            + _REACT_SUFFIX
        ),
        tools=WRITER_TOOLS,
        model=pro_model,
        model_settings=pro_settings,
        output_guardrails=SPECIALIST_OUTPUT_GUARDRAILS if GUARDRAILS_ENABLED else [],
    )


writer_specialist = create_writer_specialist()
