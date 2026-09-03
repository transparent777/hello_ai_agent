"""宿主机文件工具：workspace_user 可读写；data/ 前缀为示例数据集只读区。"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from agents import function_tool

from config.file_agent import (
    DATA_READ_ROOT,
    FILE_AGENT_BLOCKED_NAME_PATTERNS,
    FILE_AGENT_MAX_LIST_ENTRIES,
    FILE_AGENT_MAX_READ_BYTES,
    FILE_AGENT_MAX_WRITE_BYTES,
    FILE_AGENT_PREVIEW_MAX_CHARS,
    FILE_AGENT_PREVIEW_MAX_LINES,
    FILE_AGENT_WORKSPACE,
)
from guardrails import validate_file_tool_path
from sandbox.audit import log_audit_event

DATA_VIRTUAL_PREFIX = "data/"
# Excel（尤其中文版 Windows）识别 UTF-8 需要 BOM
CSV_ENCODING = "utf-8-sig"


def _safe_csv_cell(value: object) -> object:
    """Prefix spreadsheet formula-like values so Excel treats them as text."""
    text = str(value)
    if text.startswith(("=", "+", "-", "@")):
        return "'" + text
    return value


def _encoding_for_path(relative_path: str) -> str:
    if Path(relative_path).suffix.lower() == ".csv":
        return CSV_ENCODING
    return "utf-8"


def _load_json_data(filename: str) -> list[dict]:
    path = DATA_READ_ROOT / filename
    if not path.exists():
        raise FileNotFoundError(f"未找到 {filename}，请先运行 python scripts/generate_catalog.py")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{filename} 格式无效")
    return data


def _write_csv_rows(path: Path, headers: list[str], rows: list[list]) -> int:
    with path.open("w", encoding=CSV_ENCODING, newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow([_safe_csv_cell(cell) for cell in headers])
        writer.writerows(
            [[_safe_csv_cell(cell) for cell in row] for row in rows]
        )
    return path.stat().st_size


def ensure_workspace() -> Path:
    """确保工作区目录存在。"""
    FILE_AGENT_WORKSPACE.mkdir(parents=True, exist_ok=True)
    return FILE_AGENT_WORKSPACE


def _normalize_relative_path(relative_path: str) -> str:
    raw = relative_path.strip().replace("\\", "/")
    while raw.startswith("./"):
        raw = raw[2:]
    return raw.lstrip("/")


def is_data_virtual_path(relative_path: str) -> bool:
    normalized = _normalize_relative_path(relative_path).lower()
    return normalized == "data" or normalized.startswith(DATA_VIRTUAL_PREFIX)


def is_blocked_relative_path(relative_path: str) -> str | None:
    """若路径命中黑名单则返回原因，否则 None。"""
    normalized = _normalize_relative_path(relative_path).lower()
    if not normalized:
        return "empty_path"
    parts = normalized.split("/")
    if ".." in parts:
        return "path_traversal"
    for part in parts:
        for blocked in FILE_AGENT_BLOCKED_NAME_PATTERNS:
            if blocked in part:
                return f"blocked_name:{blocked}"
    return None


def _resolve_data_path(relative_path: str) -> Path:
    blocked = is_blocked_relative_path(relative_path)
    if blocked:
        raise ValueError(f"路径不允许访问（{blocked}）")

    normalized = _normalize_relative_path(relative_path)
    if normalized == "data":
        target = DATA_READ_ROOT
    else:
        rel = normalized[len("data/") :]
        target = (DATA_READ_ROOT / rel).resolve()

    try:
        target.relative_to(DATA_READ_ROOT)
    except ValueError as exc:
        raise ValueError("路径超出 data/ 只读区范围") from exc
    return target


def resolve_safe_path(relative_path: str, *, create_parents: bool = False) -> Path:
    """将相对路径解析为绝对路径；data/ 只读，其余在工作区内。"""
    if is_data_virtual_path(relative_path):
        if create_parents:
            raise ValueError("data/ 目录为只读，不可写入")
        return _resolve_data_path(relative_path)

    blocked = is_blocked_relative_path(relative_path)
    if blocked:
        raise ValueError(f"路径不允许访问（{blocked}）")

    root = ensure_workspace()
    rel = _normalize_relative_path(relative_path)
    target = (root / rel).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise ValueError("路径超出 FILE_AGENT_WORKSPACE 范围") from exc

    if create_parents and not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
    return target


def _format_listing(root: Path, target: Path, label: str) -> str:
    if not target.exists():
        return f"目录不存在：{label}"
    if not target.is_dir():
        return f"不是目录：{label}"

    entries: list[str] = []
    for item in sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
        if len(entries) >= FILE_AGENT_MAX_LIST_ENTRIES:
            entries.append(f"... 仅显示前 {FILE_AGENT_MAX_LIST_ENTRIES} 项")
            break
        rel = item.relative_to(root).as_posix()
        prefix = "data/" if root == DATA_READ_ROOT else ""
        display = f"{prefix}{rel}" if prefix else rel
        kind = "dir" if item.is_dir() else "file"
        if kind == "file":
            size = item.stat().st_size
            entries.append(f"- [{kind}] {display} ({size} bytes)")
        else:
            entries.append(f"- [{kind}] {display}/")

    if not entries:
        return f"目录 `{label}` 为空。"
    return f"目录 `{label}` 内容：\n" + "\n".join(entries)


def list_files_impl(relative_dir: str = "") -> str:
    """列出工作区或 data/ 子目录内容。"""
    rel = _normalize_relative_path(relative_dir)
    if not rel:
        workspace_list = _format_listing(ensure_workspace(), ensure_workspace(), ".")
        data_list = ""
        if DATA_READ_ROOT.exists():
            data_list = "\n\n" + _format_listing(
                DATA_READ_ROOT, DATA_READ_ROOT, "data（只读）"
            )
        return (
            "可访问区域：\n"
            f"- workspace_user/（可读写）\n"
            f"- data/（只读，含 products.json、orders.json）\n\n"
            f"{workspace_list}{data_list}"
        )

    if is_data_virtual_path(rel):
        target = _resolve_data_path(rel if rel != "data" else "data/")
        root = DATA_READ_ROOT
        label = "data" if rel == "data" else rel
        return f"数据目录（只读）\n{_format_listing(root, target, label)}"

    root = ensure_workspace()
    target = resolve_safe_path(rel, create_parents=False)
    return f"工作区：{root}\n{_format_listing(root, target, rel or '.')}"


def _normalize_display_content(relative_path: str, raw: str) -> tuple[str, int, bool]:
    """格式化展示内容，返回 (正文, 总行数, 是否截断)。"""
    suffix = Path(relative_path).suffix.lower()
    content = raw
    total_lines = len(raw.splitlines()) or 1

    if suffix == ".json":
        try:
            content = json.dumps(json.loads(raw), ensure_ascii=False, indent=2)
            total_lines = len(content.splitlines()) or 1
        except json.JSONDecodeError:
            pass

    truncated = False
    lines = content.splitlines()
    if len(lines) > FILE_AGENT_PREVIEW_MAX_LINES:
        content = "\n".join(lines[: FILE_AGENT_PREVIEW_MAX_LINES])
        truncated = True
    if len(content) > FILE_AGENT_PREVIEW_MAX_CHARS:
        content = content[:FILE_AGENT_PREVIEW_MAX_CHARS].rstrip() + "\n…"
        truncated = True
    return content, total_lines, truncated


def _format_read_response(
    relative_path: str,
    content: str,
    *,
    zone: str,
    size: int,
    total_lines: int,
    truncated: bool,
) -> str:
    suffix = Path(relative_path).suffix.lower()
    size_label = f"{size / 1024:.1f} KB" if size >= 1024 else f"{size} bytes"
    header = (
        f"**{relative_path}**（{zone}，{size_label}，共 {total_lines} 行）"
    )
    if truncated:
        header += (
            f"\n\n> 内容较长，以下为前 {FILE_AGENT_PREVIEW_MAX_LINES} 行预览。"
            " 完整数据请在本机打开 "
            f"`ai_chat_robot/{relative_path}`，或在对话中让 Agent **统计/筛选**而非全文粘贴。"
        )

    if suffix == ".json":
        return f"{header}\n\n```json\n{content}\n```"
    if suffix == ".md":
        return f"{header}\n\n---\n\n{content}"
    return f"{header}\n\n{content}"


def read_file_impl(relative_path: str) -> str:
    """读取工作区或 data/ 内文本文件。"""
    path = resolve_safe_path(relative_path)
    if not path.exists():
        return f"文件不存在：{relative_path}"
    if not path.is_file():
        return f"不是文件：{relative_path}"

    size = path.stat().st_size
    if size > FILE_AGENT_MAX_READ_BYTES:
        return (
            f"文件过大（{size} bytes），超过读取上限 "
            f"{FILE_AGENT_MAX_READ_BYTES} bytes：{relative_path}"
        )

    content = path.read_text(encoding="utf-8", errors="replace")
    zone = "data（只读）" if is_data_virtual_path(relative_path) else "workspace_user"
    display, total_lines, truncated = _normalize_display_content(relative_path, content)
    log_audit_event(
        "file_agent_read",
        status="ok",
        detail=relative_path,
        extra={"bytes": size, "zone": zone, "truncated": truncated},
    )
    return _format_read_response(
        relative_path,
        display,
        zone=zone,
        size=size,
        total_lines=total_lines,
        truncated=truncated,
    )


def write_file_impl(relative_path: str, content: str) -> str:
    """写入工作区内文本文件（覆盖）；不可写 data/。"""
    if is_data_virtual_path(relative_path):
        return "data/ 为示例数据只读区，不可写入。请写入 workspace_user/ 下路径。"

    if len(content.encode("utf-8")) > FILE_AGENT_MAX_WRITE_BYTES:
        return (
            f"内容过大，超过写入上限 {FILE_AGENT_MAX_WRITE_BYTES} bytes。"
            "请拆分为多个较小文件。"
        )

    path = resolve_safe_path(relative_path, create_parents=True)
    existed = path.exists()
    path.write_text(content, encoding=_encoding_for_path(relative_path))
    size = path.stat().st_size
    action = "覆盖" if existed else "创建"
    encoding_note = "（UTF-8 BOM，Excel 可直接打开）" if relative_path.lower().endswith(".csv") else ""
    log_audit_event(
        "file_agent_write",
        status="ok",
        detail=relative_path,
        extra={"bytes": size, "action": action},
    )
    return f"已{action}文件 `{relative_path}`（{size} bytes）{encoding_note}。"


def export_products_csv_impl(relative_path: str = "exports/products.csv") -> str:
    """从 products.json 导出商品清单 CSV。"""
    products = _load_json_data("products.json")
    path = resolve_safe_path(relative_path, create_parents=True)
    headers = ["商品ID", "商品名称", "分类", "价格(元)", "库存", "描述"]
    rows = [
        [
            item.get("id", ""),
            item.get("name", ""),
            item.get("category", ""),
            item.get("price", ""),
            item.get("stock", ""),
            item.get("description", ""),
        ]
        for item in products
    ]
    size = _write_csv_rows(path, headers, rows)
    log_audit_event(
        "file_agent_export_csv",
        status="ok",
        detail=relative_path,
        extra={"dataset": "products", "rows": len(rows), "bytes": size},
    )
    return (
        f"已导出商品清单：`{relative_path}`（共 {len(rows)} 条，{size} bytes）。\n"
        "编码：UTF-8 BOM，请用 Excel 直接双击打开；若仍乱码，在 Excel 中选「数据 → 自文本/CSV」并选 UTF-8。"
    )


def export_orders_csv_impl(relative_path: str = "exports/orders.csv") -> str:
    """从 orders.json 导出订单清单 CSV。"""
    orders = _load_json_data("orders.json")
    path = resolve_safe_path(relative_path, create_parents=True)
    headers = [
        "订单号",
        "用户ID",
        "状态",
        "承运商",
        "运单号",
        "预计送达",
        "商品明细",
        "订单金额(元)",
    ]
    rows = []
    for order in orders:
        item_parts = [
            f"{it.get('name', '')}x{it.get('quantity', 1)}"
            for it in order.get("items", [])
        ]
        rows.append(
            [
                order.get("order_id", ""),
                order.get("user_id", ""),
                order.get("status", ""),
                order.get("carrier", ""),
                order.get("tracking_no", ""),
                order.get("eta", ""),
                "；".join(item_parts),
                order.get("total", ""),
            ]
        )
    size = _write_csv_rows(path, headers, rows)
    log_audit_event(
        "file_agent_export_csv",
        status="ok",
        detail=relative_path,
        extra={"dataset": "orders", "rows": len(rows), "bytes": size},
    )
    return (
        f"已导出订单清单：`{relative_path}`（共 {len(rows)} 条，{size} bytes）。\n"
        "编码：UTF-8 BOM，Excel 可直接打开。"
    )


@function_tool(tool_input_guardrails=[validate_file_tool_path])
def list_files(relative_dir: str = "") -> str:
    """列出目录。relative_dir 为空时展示 workspace_user 与 data/；data/ 为只读示例数据。"""
    return list_files_impl(relative_dir)


@function_tool(tool_input_guardrails=[validate_file_tool_path])
def read_file(relative_path: str) -> str:
    """读取文本文件。workspace_user 下可读写；data/products.json、data/orders.json 等为只读全量数据。"""
    return read_file_impl(relative_path)


@function_tool(
    needs_approval=True,
    tool_input_guardrails=[validate_file_tool_path],
)
def write_file(relative_path: str, content: str) -> str:
    """写入或覆盖 workspace_user 内文本文件（敏感操作，需人工审批）。.csv 自动使用 UTF-8 BOM。"""
    return write_file_impl(relative_path, content)


@function_tool(tool_input_guardrails=[validate_file_tool_path])
def export_products_csv(relative_path: str = "exports/products.csv") -> str:
    """从 data/products.json 导出商品清单 CSV 到 workspace_user（UTF-8 BOM，Excel 中文不乱码）。"""
    return export_products_csv_impl(relative_path)


@function_tool(tool_input_guardrails=[validate_file_tool_path])
def export_orders_csv(relative_path: str = "exports/orders.csv") -> str:
    """从 data/orders.json 导出订单清单 CSV 到 workspace_user（UTF-8 BOM，Excel 中文不乱码）。"""
    return export_orders_csv_impl(relative_path)
