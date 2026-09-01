"""文件工具与路径沙箱单元测试。"""

from __future__ import annotations

import asyncio
import sys
import tempfile
from pathlib import Path

_APP_DIR = Path(__file__).resolve().parent.parent
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

from agents import Agent, RunContextWrapper
from agents.tool_context import ToolContext
from agents.tool_guardrails import ToolInputGuardrailData

import file_tools
from file_tools import (
    ensure_workspace,
    list_files_impl,
    read_file_impl,
    resolve_safe_path,
    write_file_impl,
)
from guardrails import block_off_topic, validate_file_tool_path


def _with_workspace(tmp_path: Path):
    original = file_tools.FILE_AGENT_WORKSPACE
    file_tools.FILE_AGENT_WORKSPACE = tmp_path
    return original


def _restore_workspace(original: Path) -> None:
    file_tools.FILE_AGENT_WORKSPACE = original


def test_resolve_safe_path_blocks_traversal():
    with tempfile.TemporaryDirectory() as td:
        original = _with_workspace(Path(td))
        try:
            try:
                resolve_safe_path("../outside.txt")
                assert False, "should raise"
            except ValueError:
                pass
        finally:
            _restore_workspace(original)


def test_resolve_safe_path_allows_nested():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        original = _with_workspace(root)
        try:
            target = resolve_safe_path("notes/a.txt", create_parents=True)
            assert target == (root / "notes" / "a.txt").resolve()
        finally:
            _restore_workspace(original)


def test_read_write_roundtrip():
    with tempfile.TemporaryDirectory() as td:
        original = _with_workspace(Path(td))
        try:
            ensure_workspace()
            write_file_impl("demo/x.txt", "hello agent")
            out = read_file_impl("demo/x.txt")
            assert "hello agent" in out
        finally:
            _restore_workspace(original)


def test_list_files_shows_entries():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        original = _with_workspace(root)
        try:
            (root / "a.txt").write_text("1", encoding="utf-8")
            (root / "sub").mkdir()
            out = list_files_impl("")
            assert "a.txt" in out
            assert "sub/" in out
        finally:
            _restore_workspace(original)


def _run_input_guardrail(guardrail, text: str):
    ctx = RunContextWrapper(context=None)
    agent = Agent(name="test", instructions="test")
    return asyncio.run(guardrail.run(agent, text, ctx))


def test_allow_file_task_query():
    out = _run_input_guardrail(block_off_topic, "列出 workspace_user 里的文件")
    assert out.output.tripwire_triggered is False


def test_validate_file_tool_path_rejects_traversal():
    data = ToolInputGuardrailData(
        context=ToolContext(
            context=None,
            tool_name="read_file",
            tool_call_id="call_1",
            tool_arguments='{"relative_path": "../.env"}',
        ),
        agent=Agent(name="file_specialist", instructions="test"),
    )
    result = asyncio.run(validate_file_tool_path.run(data))
    assert result.behavior["type"] == "reject_content"


if __name__ == "__main__":
    test_resolve_safe_path_blocks_traversal()
    test_resolve_safe_path_allows_nested()
    test_read_write_roundtrip()
    test_list_files_shows_entries()
    test_allow_file_task_query()
    test_validate_file_tool_path_rejects_traversal()
    print("test_file_tools: OK")
