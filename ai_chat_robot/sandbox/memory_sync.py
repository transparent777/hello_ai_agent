"""沙箱跨运行记忆：从 output 汇总到 memories/memory_summary.md（批次 E2）。"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from sandbox.settings import SANDBOX_MEMORY_ENABLED, SANDBOX_PERSIST_ROOT

WORKSPACE_OUTPUT = Path(__file__).resolve().parent / "workspace" / "output"
_MEMORY_FILES = (
    ("analysis_summary.json", "订单分析摘要"),
    ("pricing.json", "定价模拟结果"),
    ("report.md", "综合报表"),
)


def _session_dir(session_id: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in session_id)
    return SANDBOX_PERSIST_ROOT / safe


def memories_dir(session_id: str) -> Path:
    return _session_dir(session_id) / "memories"


def memory_summary_path(session_id: str) -> Path:
    return memories_dir(session_id) / "memory_summary.md"


def has_memory_summary(session_id: str) -> bool:
    return memory_summary_path(session_id).is_file()


def refresh_memory_summary(session_id: str) -> bool:
    """根据 workspace/output 更新持久化 memory_summary.md。有更新返回 True。"""
    if not SANDBOX_MEMORY_ENABLED:
        return False

    sections: list[str] = []
    for filename, title in _MEMORY_FILES:
        src = WORKSPACE_OUTPUT / filename
        if not src.is_file():
            continue
        try:
            body = src.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if not body:
            continue
        if len(body) > 4000:
            body = body[:4000] + "\n\n...(已截断)"
        sections.append(f"### {title}（{filename}）\n\n{body}")

    if not sections:
        return False

    mem_dir = memories_dir(session_id)
    mem_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    header = (
        f"# 数据分析记忆\n\n"
        f"会话：`{session_id}`  \n"
        f"最近更新：{stamp}\n\n"
        f"以下为历次分析留在 output/ 中的要点，供后续任务参考。\n\n"
    )
    memory_summary_path(session_id).write_text(
        header + "\n\n".join(sections) + "\n",
        encoding="utf-8",
    )
    return True
