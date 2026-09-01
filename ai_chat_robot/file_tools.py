"""宿主机文件工具：仅在 FILE_AGENT_WORKSPACE 内 list / read / write。"""

from __future__ import annotations

from pathlib import Path

from agents import function_tool

from file_agent_settings import (
    FILE_AGENT_MAX_LIST_ENTRIES,
    FILE_AGENT_MAX_READ_BYTES,
    FILE_AGENT_MAX_WRITE_BYTES,
    FILE_AGENT_WORKSPACE,
    FILE_AGENT_BLOCKED_NAME_PATTERNS,
)
from guardrails import validate_file_tool_path
from sandbox.audit import log_audit_event


def ensure_workspace() -> Path:
    """确保工作区目录存在。"""
    FILE_AGENT_WORKSPACE.mkdir(parents=True, exist_ok=True)
    return FILE_AGENT_WORKSPACE


def _normalize_relative_path(relative_path: str) -> str:
    raw = relative_path.strip().replace("\\", "/")
    while raw.startswith("./"):
        raw = raw[2:]
    return raw.lstrip("/")


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


def resolve_safe_path(relative_path: str, *, create_parents: bool = False) -> Path:
    """
    将工作区相对路径解析为绝对路径；越界或非法则抛 ValueError。
    """
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


def list_files_impl(relative_dir: str = "") -> str:
    """列出工作区子目录内容。"""
    root = ensure_workspace()
    target = root if not relative_dir.strip() else resolve_safe_path(relative_dir, create_parents=False)

    if not target.exists():
        return f"目录不存在：{relative_dir or '.'}"
    if not target.is_dir():
        return f"不是目录：{relative_dir}"

    entries: list[str] = []
    for item in sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
        if len(entries) >= FILE_AGENT_MAX_LIST_ENTRIES:
            entries.append(f"... 仅显示前 {FILE_AGENT_MAX_LIST_ENTRIES} 项")
            break
        rel = item.relative_to(root).as_posix()
        kind = "dir" if item.is_dir() else "file"
        if kind == "file":
            size = item.stat().st_size
            entries.append(f"- [{kind}] {rel} ({size} bytes)")
        else:
            entries.append(f"- [{kind}] {rel}/")

    prefix = f"工作区：{root}\n"
    if not entries:
        return prefix + (f"目录 `{relative_dir or '.'}` 为空。")
    label = relative_dir or "."
    return prefix + f"目录 `{label}` 内容：\n" + "\n".join(entries)


def read_file_impl(relative_path: str) -> str:
    """读取工作区内文本文件。"""
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
    log_audit_event(
        "file_agent_read",
        status="ok",
        detail=relative_path,
        extra={"bytes": size},
    )
    return f"文件 `{relative_path}`（{size} bytes）：\n```\n{content}\n```"


def write_file_impl(relative_path: str, content: str) -> str:
    """写入工作区内文本文件（覆盖）。"""
    if len(content.encode("utf-8")) > FILE_AGENT_MAX_WRITE_BYTES:
        return (
            f"内容过大，超过写入上限 {FILE_AGENT_MAX_WRITE_BYTES} bytes。"
            "请拆分为多个较小文件。"
        )

    path = resolve_safe_path(relative_path, create_parents=True)
    existed = path.exists()
    path.write_text(content, encoding="utf-8")
    size = path.stat().st_size
    action = "覆盖" if existed else "创建"
    log_audit_event(
        "file_agent_write",
        status="ok",
        detail=relative_path,
        extra={"bytes": size, "action": action},
    )
    return f"已{action}文件 `{relative_path}`（{size} bytes）。"


@function_tool(tool_input_guardrails=[validate_file_tool_path])
def list_files(relative_dir: str = "") -> str:
    """列出 FILE_AGENT_WORKSPACE 内某目录的文件与子目录。relative_dir 为空表示根目录。"""
    return list_files_impl(relative_dir)


@function_tool(tool_input_guardrails=[validate_file_tool_path])
def read_file(relative_path: str) -> str:
    """读取工作区内文本文件内容。路径相对于 workspace_user，例如 notes/todo.txt。"""
    return read_file_impl(relative_path)


@function_tool(
    needs_approval=True,
    tool_input_guardrails=[validate_file_tool_path],
)
def write_file(relative_path: str, content: str) -> str:
    """写入或覆盖工作区内文本文件（敏感操作，需人工审批）。"""
    return write_file_impl(relative_path, content)
