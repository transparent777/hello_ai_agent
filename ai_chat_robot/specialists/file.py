"""文件与数据导出专员。"""

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


def create_file_specialist() -> Agent | None:
    if not FILE_AGENT_ENABLED:
        return None
    ensure_workspace()
    from config.file_agent import FILE_AGENT_WORKSPACE

    workspace_label = str(FILE_AGENT_WORKSPACE)
    return Agent(
        name="file_specialist",
        handoff_description=(
            "读取 data/ 全量 JSON、导出商品/订单 CSV 清单（Excel 不乱码），"
            "或处理 workspace_user 内文件读写（写入需审批）。"
        ),
        instructions=(
            "你是文件与数据专员，可访问两类路径（均用相对路径）：\n"
            f"1. **data/**（只读）：电商全量 JSON，如 data/products.json、data/orders.json\n"
            f"2. **workspace_user/**（可读写）：用户工作区，根目录 {workspace_label}\n"
            "规则：\n"
            "- 用户要**导出 CSV/Excel 清单** → 必须调用 export_products_csv 或 export_orders_csv，"
            "不要手写 CSV 字符串（易乱码）\n"
            "- 导出默认路径：exports/products.csv、exports/orders.csv\n"
            "- 查原始 JSON → read_file('data/products.json') 等\n"
            "- 普通文本写入 → write_file（会触发人工审批）；.csv 写入会自动加 UTF-8 BOM\n"
            "- 用中文说明文件路径与条数"
        ),
        tools=[list_files, read_file, write_file, export_products_csv, export_orders_csv],
        model=pro_model,
        model_settings=pro_settings,
        output_guardrails=SPECIALIST_OUTPUT_GUARDRAILS if GUARDRAILS_ENABLED else [],
    )


file_specialist = create_file_specialist()
