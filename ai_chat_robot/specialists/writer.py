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
    "Thought 只在内部推理，**禁止**输出给用户。\n"
    "用户要 docx 时流程：read_skill('essay-docx') → 撰写纯文本 → **必须** export_docx → 汇报路径。\n"
    "- export_docx 的 body：**纯文本**，无 Markdown（无 **、#、>）。\n"
    f"- 默认保存到 exports/ 下，工作区根目录：{FILE_AGENT_WORKSPACE}\n"
    "- 调用 export_docx 后根据工具返回的绝对路径回复用户；不要只说「已生成」而不给路径。\n"
    "- 不要在对话里重复粘贴整篇长文（给用户路径 + 简短摘要即可）。\n"
    "- 禁止 transfer_to_workspace_router，除非用户明确要求协调员汇总。"
)


def create_writer_specialist() -> Agent | None:
    if not FILE_AGENT_ENABLED:
        return None
    ensure_workspace()
    return Agent(
        name="writer_specialist",
        handoff_description=(
            "长文案、思政/议论文、邮件；用户明确要求 Word/docx 或保存文件。"
            "须实际调用 export_docx，不是只在聊天里写。"
        ),
        instructions=(
            "你是写作与内容专员。\n"
            "## 用户要 docx / Word 时（硬性）\n"
            "1. read_skill('essay-docx')\n"
            "2. 写好 title + body（纯文本）\n"
            "3. **必须**调用 export_docx(relative_path='exports/标题.docx', ...)\n"
            "4. 把工具返回的相对路径与本机绝对路径告诉用户\n"
            "未调用 export_docx 就声称「已生成文件」= 错误。\n"
            "## 仅对话、未要求文件\n"
            "- 用 Markdown 在聊天里回复即可，不调 export_docx\n"
            "## 禁止\n"
            "- 输出「转接失败」「让我重新转接」「Thought:」等内部过程\n"
            "- body 里使用 Markdown 符号（会导致 Word 版式混乱）\n"
            + _REACT_SUFFIX
        ),
        tools=WRITER_TOOLS,
        model=pro_model,
        model_settings=pro_settings,
        output_guardrails=SPECIALIST_OUTPUT_GUARDRAILS if GUARDRAILS_ENABLED else [],
    )


writer_specialist = create_writer_specialist()
