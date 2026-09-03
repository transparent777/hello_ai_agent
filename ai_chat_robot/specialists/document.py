"""文档专员：阅读、总结、整理与写入工作区文件。"""

from __future__ import annotations

from agents import Agent

from config.file_agent import FILE_AGENT_ENABLED
from guardrails import GUARDRAILS_ENABLED, SPECIALIST_OUTPUT_GUARDRAILS
from config.llm import pro_model, pro_settings
from tools.file import (
    ensure_workspace,
    export_orders_csv,
    export_products_csv,
    list_files,
    read_file,
    write_file,
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
            "阅读与总结 workspace 内文件，列出目录，整理内容，"
            "或将结果写入工作区（写入需审批）。"
        ),
        instructions=(
            "你是文档与文件专员，帮助用户阅读、理解和整理文本数据。\n"
            f"工作区根目录：{workspace_label}（对话中用相对路径，如 demo/hello.txt）\n"
            "可选只读示例数据：data/ 前缀（如 data/orders.json，供对照或引用）\n\n"
            "职责：\n"
            "- **阅读**：用 list_files 浏览目录，read_file 读取 txt/md/csv/json 等\n"
            "- **总结**：读完文件后，用中文给出结构化摘要（要点、结论、待办）\n"
            "- **导出**：从 data/products.json、data/orders.json 导出 CSV → "
            "export_products_csv / export_orders_csv（输出到 exports/，Excel 友好 UTF-8 BOM）\n"
            "- **整理**：可将摘要写入 write_file（会触发人工审批）\n\n"
            "规则：\n"
            "- 先读再答，不要编造文件内容\n"
            "- 长文件先概括再列细节；必要时说明已截断预览\n"
            "- data/ 只读，不可 write_file 到 data/\n"
            "- 写入默认放 exports/ 或 notes/ 等子目录\n"
            "- 用中文回复，标明文件路径与行数/大小"
        ),
        tools=[
            list_files,
            read_file,
            export_products_csv,
            export_orders_csv,
            write_file,
        ],
        model=pro_model,
        model_settings=pro_settings,
        output_guardrails=SPECIALIST_OUTPUT_GUARDRAILS if GUARDRAILS_ENABLED else [],
    )


document_specialist = create_document_specialist()

# 兼容旧名称
file_specialist = document_specialist
