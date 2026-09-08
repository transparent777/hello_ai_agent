from __future__ import annotations

from services.stream_filter import DeltaSanitizer, StreamGate


def _sanitize_chunks(chunks: list[str]) -> str:
    sanitizer = DeltaSanitizer()
    output = [sanitizer.feed(chunk) for chunk in chunks]
    output.append(sanitizer.flush())
    return "".join(output)


def test_chinese_text_streams_without_corruption() -> None:
    text = "中文流式输出：你好，世界。"
    assert _sanitize_chunks(list(text)) == text


def test_dsml_block_is_removed_when_markers_are_split() -> None:
    text = (
        "开始"
        "<｜｜DSML｜｜tool_calls>"
        '<invoke name="transfer_to_writer_specialist">{}'
        "</｜｜DSML｜｜tool_calls>"
        "最终答案"
    )

    assert _sanitize_chunks(list(text)) == "开始最终答案"


def test_unclosed_dsml_block_never_leaks_tool_payload() -> None:
    chunks = ["可见", "<｜", "｜DS", "ML｜｜tool_calls>", "invoke name=", "secret"]
    assert _sanitize_chunks(chunks) == "可见"


def test_split_monologue_line_is_hidden() -> None:
    chunks = list("Let me call a tool first.\n这是最终答案。")
    assert _sanitize_chunks(chunks) == "\n这是最终答案。"


def test_deliverable_gate_hides_specialist_stream() -> None:
    gate = StreamGate(deliverable_task=True)
    gate.set_agent("writer_specialist")
    assert gate.emit("内部执行过程") is None

    gate.set_agent("workspace_router")
    assert gate.emit("最终答复") == "最终答复"
    assert gate.flush() is None
