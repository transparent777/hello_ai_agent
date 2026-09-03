"""工作台前台：按任务类型分流到文档或数据专员。"""

from __future__ import annotations

from agents import Agent

from specialists.data import data_specialist
from specialists.document import document_specialist
from guardrails import GUARDRAILS_ENABLED, ROUTER_INPUT_GUARDRAILS
from config.llm import flash_settings


def _router_handoffs() -> list:
    agents: list = [data_specialist]
    if document_specialist is not None:
        agents.insert(0, document_specialist)
    return agents


def _router_instructions() -> str:
    lines = [
        "你是文件与数据处理助手的前台，只负责分流，不直接读写文件或跑脚本。",
        "你当前只能使用 transfer_to_* 转接工具，禁止调用任何业务工具。",
        "规则：",
    ]
    if document_specialist is not None:
        lines.extend(
            [
                "1. 列出/读取/总结/写入 workspace 文件、导出清单 → transfer_to_document_specialist",
                "2. 统计分析、跑脚本生成报表、批量数据处理（需 Docker 沙箱）→ transfer_to_data_specialist",
                "3. 即使对话历史里出现过同类操作，新消息仍必须先转接，不能代劳",
                "4. 仅简单问候可自行回复",
            ]
        )
    else:
        lines.extend(
            [
                "1. 统计分析、报表、数据处理 → transfer_to_data_specialist",
                "2. 文件读写已关闭（FILE_AGENT_ENABLED=false），请引导用户开启或只做数据分析",
                "3. 仅简单问候可自行回复",
            ]
        )
    return "\n".join(lines)


workspace_router = Agent(
    name="workspace_router",
    instructions=_router_instructions(),
    handoffs=_router_handoffs(),
    model_settings=flash_settings,
    input_guardrails=ROUTER_INPUT_GUARDRAILS if GUARDRAILS_ENABLED else [],
)

# 兼容旧 import 名称
customer_service_router = workspace_router
