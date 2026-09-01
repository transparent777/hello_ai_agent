"""Tracing：调试日志 + Eval 高信号样本采集。"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agents.tracing import add_trace_processor, set_tracing_disabled
from agents.tracing.processor_interface import TracingProcessor
from agents.tracing.processors import BatchTraceProcessor
from agents.tracing.spans import Span
from agents.tracing.traces import Trace

PROJECT_ROOT = Path(__file__).resolve().parent
LOGS_DIR = PROJECT_ROOT / "logs"
DEFAULT_TRACE_LOG = LOGS_DIR / "agent_traces.jsonl"
DEFAULT_EVAL_SAMPLES = LOGS_DIR / "eval_samples.jsonl"

_configured = False
_lock = threading.Lock()


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


TRACING_ENABLED = _env_bool("TRACING_ENABLED", True)
TRACING_EVAL_ENABLED = _env_bool("TRACING_EVAL_ENABLED", True)
TRACING_LOG_PATH = Path(os.getenv("TRACING_LOG_PATH", str(DEFAULT_TRACE_LOG)))
TRACING_EVAL_SAMPLES_PATH = Path(
    os.getenv("TRACING_EVAL_SAMPLES_PATH", str(DEFAULT_EVAL_SAMPLES))
)


class JsonlTracingExporter:
    """将 trace/span 导出为 JSONL，便于调试单次工作流。"""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def export(self, items: list[Trace | Span[Any]]) -> None:
        lines: list[str] = []
        for item in items:
            payload = item.export()
            if payload is None:
                continue
            lines.append(json.dumps(payload, ensure_ascii=False, default=str))
        if not lines:
            return
        with self._lock:
            with self.path.open("a", encoding="utf-8") as fh:
                for line in lines:
                    fh.write(line + "\n")


class EvalSampleProcessor(TracingProcessor):
    """从完成的 trace 中提取高信号样本，供后续 eval 数据集使用。"""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._spans: dict[str, list[dict[str, Any]]] = {}
        self._lock = threading.Lock()

    def on_trace_start(self, trace: Trace) -> None:
        self._spans[trace.trace_id] = []

    def on_trace_end(self, trace: Trace) -> None:
        spans = self._spans.pop(trace.trace_id, [])
        if not spans:
            return
        if not _trace_is_eval_candidate(spans):
            return
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "trace_id": trace.trace_id,
            "workflow_name": trace.name,
            "span_count": len(spans),
            "spans": spans,
        }
        line = json.dumps(record, ensure_ascii=False, default=str)
        with self._lock:
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")

    def on_span_start(self, span: Span[Any]) -> None:
        _ = span

    def on_span_end(self, span: Span[Any]) -> None:
        exported = span.export()
        if exported is None:
            return
        bucket = self._spans.get(span.trace_id)
        if bucket is None:
            return
        bucket.append(exported)

    def shutdown(self) -> None:
        self._spans.clear()

    def force_flush(self) -> None:
        return


def _trace_is_eval_candidate(spans: list[dict[str, Any]]) -> bool:
    """保留含 agent/generation/guardrail/mcp 且无明显错误的 trace。"""
    interesting = {"agent", "generation", "guardrail", "mcp_tools", "function"}
    has_signal = False
    for span in spans:
        data = span.get("span_data") or {}
        span_type = data.get("type")
        if span_type in interesting:
            has_signal = True
        errors = span.get("errors") or data.get("errors")
        if errors:
            return False
    return has_signal


def configure_tracing() -> None:
    """按环境变量注册 tracing processor（进程内只配置一次）。"""
    global _configured
    with _lock:
        if _configured:
            return
        set_tracing_disabled(not TRACING_ENABLED)
        if not TRACING_ENABLED:
            _configured = True
            return

        add_trace_processor(BatchTraceProcessor(JsonlTracingExporter(TRACING_LOG_PATH)))
        if TRACING_EVAL_ENABLED:
            add_trace_processor(EvalSampleProcessor(TRACING_EVAL_SAMPLES_PATH))
        _configured = True


def tracing_status_summary() -> str:
    if not TRACING_ENABLED:
        return "关闭"
    parts = [f"调试日志 → {TRACING_LOG_PATH.name}"]
    if TRACING_EVAL_ENABLED:
        parts.append(f"Eval 样本 → {TRACING_EVAL_SAMPLES_PATH.name}")
    return " · ".join(parts)


def get_recent_trace_count(max_lines: int = 500) -> int:
    if not TRACING_LOG_PATH.is_file():
        return 0
    try:
        lines = TRACING_LOG_PATH.read_text(encoding="utf-8").splitlines()
    except OSError:
        return 0
    return min(len(lines), max_lines)
