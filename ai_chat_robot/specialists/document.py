"""文档专员：阅读、总结、整理与写入工作区文件。"""

from __future__ import annotations

from agents import Agent

from config.file_agent import FILE_AGENT_ENABLED
from guardrails import GUARDRAILS_ENABLED, SPECIALIST_OUTPUT_GUARDRAILS
from config.llm import pro_model, pro_settings
from tools.file import ensure_workspace
from tools.registry import DOCUMENT_TOOLS

_REACT_SUFFIX = (
    "\n\n## 层级 ReAct（L2）\n"
    "- 仅阅读/总结：可在 L2 直接 Markdown 回复用户。\n"
    "- **用户明确要求 csv/xlsx/docx 导出**：调用 export_* 后，"
    "**必须** transfer_to_workspace_router，交接「验收：已导出 → 路径 …」。\n"
    "- 导出后不要对用户终稿，交给 L1 验收。\n"
)


def create_document_specialist() -> Agent | None:
    if not FILE_AGENT_ENABLED:
        return None
    ensure_workspace()
    from config.file_agent import FILE_AGENT_WORKSPACE

    workspace_label = str(FILE_AGENT_WORKSPACE)
    return Agent(
        name="document_specialist",
        handoff_description=(
            "阅读与总结 workspace；用户明确要求 csv/xlsx/docx 时导出并回 L1 验收。"
        ),
        instructions=(
            "你是文档与文件专员（L2）。\n"
            f"工作区：{workspace_label}；只读：data/\n"
            "阅读/总结：可直接回复。\n"
            "导出任务：export_* → transfer_to_workspace_router（验收摘要）。\n"
            + _REACT_SUFFIX
        ),
        tools=DOCUMENT_TOOLS,
        model=pro_model,
        model_settings=pro_settings,
        output_guardrails=SPECIALIST_OUTPUT_GUARDRAILS if GUARDRAILS_ENABLED else [],
    )


document_specialist = create_document_specialist()
file_specialist = document_specialist
