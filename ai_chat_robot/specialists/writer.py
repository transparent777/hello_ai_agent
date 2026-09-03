"""写作专员：文案、讨论与按需导出 Word。"""

from __future__ import annotations

from agents import Agent

from config.file_agent import FILE_AGENT_ENABLED, FILE_AGENT_WORKSPACE
from guardrails import GUARDRAILS_ENABLED, SPECIALIST_OUTPUT_GUARDRAILS
from config.llm import pro_model, pro_settings
from tools.file import ensure_workspace
from tools.registry import WRITER_TOOLS

_REACT_SUFFIX = (
    "\n\n## 层级 ReAct（L2）\n"
    "**交付 docx 时：禁止向用户输出任何文字（中文/英文均不可）。**\n"
    "只允许连续调用工具：read_skill → export_docx → transfer_to_workspace_router。\n"
    "禁止在正文中出现 DSML、transfer_to、Let me、Thought 等字样。\n"
    "## 用户要 docx / 交付文件时\n"
    "1. read_skill('essay-docx')\n"
    "2. **必须** export_docx（body 纯文本，无 Markdown）\n"
    "3. **必须** transfer_to_workspace_router，交接摘要格式：\n"
    "   「验收：已 export_docx → <相对路径>；绝对路径：<工具返回路径>；主题：<一句话>」\n"
    "4. **不要**对用户做终稿（不要长文+路径一起当最终回复），交给 L1 验收后输出。\n"
    f"5. 工作区根目录：{FILE_AGENT_WORKSPACE}\n"
    "## 仅对话、未要求文件\n"
    "- 若在 L2 被误转接且用户只要聊天：简短回复即可，无需回 L1。\n"
)


def create_writer_specialist() -> Agent | None:
    if not FILE_AGENT_ENABLED:
        return None
    ensure_workspace()
    return Agent(
        name="writer_specialist",
        handoff_description=(
            "长文案、计划表、思政文；用户明确要求 Word/docx。"
            "完成后回 L1 验收，不直接对用户终稿。"
        ),
        instructions=(
            "你是写作专员（L2），负责执行，不负责对用户终稿。\n"
            "docx 任务：read_skill → export_docx → transfer_to_workspace_router（验收摘要）。\n"
            "禁止：转接失败、Thought 外露、未 export 就声称已生成。\n"
            + _REACT_SUFFIX
        ),
        tools=WRITER_TOOLS,
        model=pro_model,
        model_settings=pro_settings,
        output_guardrails=SPECIALIST_OUTPUT_GUARDRAILS if GUARDRAILS_ENABLED else [],
    )


writer_specialist = create_writer_specialist()
