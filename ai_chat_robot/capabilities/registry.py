"""Canonical capability registry used by Agent definitions."""

from capabilities.analytics import (
    run_order_analysis,
    run_pricing_simulation,
    run_sales_report,
)
from capabilities.exports import export_docx, export_table_csv, export_table_xlsx
from capabilities.files import (
    export_orders_csv,
    export_products_csv,
    list_files,
    read_file,
    write_file,
)
from capabilities.skills import list_skills, read_skill

ROUTER_TOOLS: list = []

DOCUMENT_TOOLS = [
    list_skills,
    read_skill,
    list_files,
    read_file,
    export_products_csv,
    export_orders_csv,
    export_table_csv,
    export_table_xlsx,
    export_docx,
    write_file,
]

WRITER_TOOLS = [
    list_skills,
    read_skill,
    read_file,
    export_docx,
    write_file,
]

ANALYTICS_TOOLS = [
    run_order_analysis,
    run_pricing_simulation,
    run_sales_report,
]

__all__ = [
    "ANALYTICS_TOOLS",
    "DOCUMENT_TOOLS",
    "ROUTER_TOOLS",
    "WRITER_TOOLS",
]
