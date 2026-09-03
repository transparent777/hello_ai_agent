"""各专员工具集（单一来源）。"""

from __future__ import annotations

from tools.export import export_docx, export_table_csv, export_table_xlsx
from tools.file import (
    export_orders_csv,
    export_products_csv,
    list_files,
    read_file,
    write_file,
)
from tools.skill import list_skills, read_skill

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
