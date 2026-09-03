"""导出工具：CSV / XLSX / DOCX。"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from agents import function_tool

from guardrails import validate_file_tool_path
from sandbox.audit import log_audit_event
from tools.file import CSV_ENCODING, resolve_safe_path, write_file_impl

try:
    from docx import Document
except ImportError:  # pragma: no cover
    Document = None  # type: ignore[misc, assignment]

try:
    from openpyxl import Workbook
except ImportError:  # pragma: no cover
    Workbook = None  # type: ignore[misc, assignment]


def _parse_table_json(table_json: str) -> tuple[list[str], list[list]]:
    data = json.loads(table_json)
    if isinstance(data, dict) and "headers" in data and "rows" in data:
        headers = [str(h) for h in data["headers"]]
        rows = [[str(cell) for cell in row] for row in data["rows"]]
        return headers, rows
    if isinstance(data, list) and data and isinstance(data[0], dict):
        headers = list(data[0].keys())
        rows = [[str(item.get(h, "")) for h in headers] for item in data]
        return headers, rows
    raise ValueError("table_json 需为 {headers, rows} 或对象数组")


def export_table_csv_impl(relative_path: str, table_json: str) -> str:
    headers, rows = _parse_table_json(table_json)
    path = resolve_safe_path(relative_path, create_parents=True)
    with path.open("w", encoding=CSV_ENCODING, newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(rows)
    size = path.stat().st_size
    log_audit_event(
        "file_agent_export_csv",
        status="ok",
        detail=relative_path,
        extra={"rows": len(rows), "bytes": size},
    )
    return f"已导出 CSV：`{relative_path}`（{len(rows)} 行，{size} bytes）。"


def export_table_xlsx_impl(relative_path: str, table_json: str, sheet_name: str = "Sheet1") -> str:
    if Workbook is None:
        return "缺少 openpyxl，请执行：pip install openpyxl"
    headers, rows = _parse_table_json(table_json)
    path = resolve_safe_path(relative_path, create_parents=True)
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_name[:31] or "Sheet1"
    ws.append(headers)
    for row in rows:
        ws.append(row)
    wb.save(path)
    size = path.stat().st_size
    log_audit_event(
        "file_agent_export_xlsx",
        status="ok",
        detail=relative_path,
        extra={"rows": len(rows), "bytes": size},
    )
    return f"已导出 XLSX：`{relative_path}`（{len(rows)} 行，{size} bytes）。"


def export_docx_impl(relative_path: str, title: str, body: str) -> str:
    if Document is None:
        return "缺少 python-docx，请执行：pip install python-docx"
    path = resolve_safe_path(relative_path, create_parents=True)
    doc = Document()
    if title.strip():
        doc.add_heading(title.strip(), level=1)
    for block in body.replace("\r\n", "\n").split("\n\n"):
        paragraph = block.strip()
        if paragraph:
            doc.add_paragraph(paragraph)
    doc.save(path)
    size = path.stat().st_size
    log_audit_event(
        "file_agent_export_docx",
        status="ok",
        detail=relative_path,
        extra={"bytes": size},
    )
    return f"已导出 DOCX：`{relative_path}`（{size} bytes）。"


@function_tool(tool_input_guardrails=[validate_file_tool_path])
def export_table_csv(relative_path: str, table_json: str) -> str:
    """将表格 JSON 导出为 CSV（UTF-8 BOM）。table_json: {headers:[], rows:[][]} 或对象数组。"""
    return export_table_csv_impl(relative_path, table_json)


@function_tool(tool_input_guardrails=[validate_file_tool_path])
def export_table_xlsx(
    relative_path: str,
    table_json: str,
    sheet_name: str = "Sheet1",
) -> str:
    """将表格 JSON 导出为 Excel xlsx。"""
    return export_table_xlsx_impl(relative_path, table_json, sheet_name=sheet_name)


@function_tool(tool_input_guardrails=[validate_file_tool_path])
def export_docx(relative_path: str, title: str, body: str) -> str:
    """将标题与正文导出为 Word docx。body 用空行分段。"""
    return export_docx_impl(relative_path, title, body)
