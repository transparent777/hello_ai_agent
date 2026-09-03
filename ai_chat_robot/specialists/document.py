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
    "先 Thought 再调工具；Observation 后再决定下一步。\n"
    "- 默认在对话 Markdown 总结；仅用户明确要求格式时 export_* / write_file。\n"
    "- 导出前可 read_skill('export-formats')。\n"
    "- 简单任务直接回复；复杂任务完成后可 transfer_to_workspace_router 汇总。"
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
            "阅读与总结 workspace 文件；用户明确要求 csv/xlsx/docx 时导出。"
        ),
        instructions=(
            "你是文档与文件专员。\n"
            f"工作区：{workspace_label}；只读示例：data/ 前缀\n\n"
            "职责：\n"
            "- list_files / read_file：阅读与总结\n"
            "- 用户明确要 CSV/XLSX/DOCX 时：export_* 工具\n"
            "- 保存 md/txt：write_file（审批）\n"
            "规则：\n"
            "- 先读再答；data/ 不可写\n"
            "- 未要求文件格式时，用 Markdown 在对话里回答\n"
            + _REACT_SUFFIX
        ),
        tools=DOCUMENT_TOOLS,
        model=pro_model,
        model_settings=pro_settings,
        output_guardrails=SPECIALIST_OUTPUT_GUARDRAILS if GUARDRAILS_ENABLED else [],
    )


document_specialist = create_document_specialist()
file_specialist = document_specialist
