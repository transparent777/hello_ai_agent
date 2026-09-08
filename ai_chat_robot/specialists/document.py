"""文档专员：阅读、总结、整理与写入工作区文件。"""

from __future__ import annotations

from agents import Agent

from config.file_agent import FILE_AGENT_ENABLED
from guardrails import GUARDRAILS_ENABLED, SPECIALIST_OUTPUT_GUARDRAILS
from adapters.llm_provider import pro_model, pro_settings
from capabilities.files import ensure_workspace
from capabilities.registry import DOCUMENT_TOOLS

_REACT_SUFFIX = (
    "\n\n## 层级 ReAct（L2）\n"
    "- 阅读、总结、分析或导出完成后，**必须** transfer_to_workspace_router。\n"
    "- 回交内容只写中文验收摘要、事实依据、引用来源和文件路径。\n"
    "- 不直接面向用户输出终稿，不输出计划、思考过程或英文工具说明。\n"
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
            "阅读、总结和分析 workspace；完成后统一回 L1 验收。"
        ),
        instructions=(
            "你是文档与文件专员（L2）。\n"
            f"工作区：{workspace_label}；只读：data/\n"
            "你只向 workspace_router 提供内部工作结果，不直接回复用户。\n"
            "当用户问项目说明、学习笔记、手册/政策类问题时，优先调用 retrieve_knowledge_base 检索知识库，"
            "回答时注明引用来源。\n"
            "所有任务完成后：transfer_to_workspace_router（中文验收摘要）。\n"
            + _REACT_SUFFIX
        ),
        tools=DOCUMENT_TOOLS,
        model=pro_model,
        model_settings=pro_settings,
        output_guardrails=SPECIALIST_OUTPUT_GUARDRAILS if GUARDRAILS_ENABLED else [],
    )


document_specialist = create_document_specialist()
file_specialist = document_specialist
