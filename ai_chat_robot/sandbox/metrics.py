"""沙箱与 Agent 运行指标（P1）。"""

from __future__ import annotations

import json
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator

from sandbox.settings import METRICS_LOG_PATH

_lock = threading.Lock()
_counters: dict[str, int] = {}
_timings_ms: dict[str, list[int]] = {}


def _ensure_parent() -> None:
    METRICS_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


def _append_metric(record: dict[str, Any]) -> None:
    line = json.dumps(record, ensure_ascii=False)
    with _lock:
        _ensure_parent()
        with METRICS_LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")


def increment_counter(name: str, *, amount: int = 1) -> None:
    with _lock:
        _counters[name] = _counters.get(name, 0) + amount


def record_timing(name: str, duration_ms: int) -> None:
    with _lock:
        bucket = _timings_ms.setdefault(name, [])
        bucket.append(duration_ms)
        if len(bucket) > 200:
            del bucket[:-200]


@contextmanager
def track_duration(metric_name: str) -> Iterator[None]:
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        record_timing(metric_name, elapsed_ms)
        _append_metric(
            {
                "ts": datetime.now(timezone.utc).isoformat(),
                "type": "timing",
                "name": metric_name,
                "duration_ms": elapsed_ms,
            }
        )


def record_event(name: str, **fields: Any) -> None:
    increment_counter(name)
    _append_metric(
        {
            "ts": datetime.now(timezone.utc).isoformat(),
            "type": "event",
            "name": name,
            **fields,
        }
    )


def get_metrics_summary() -> dict[str, Any]:
    with _lock:
        timings: dict[str, dict[str, float | int]] = {}
        for name, values in _timings_ms.items():
            if not values:
                continue
            timings[name] = {
                "count": len(values),
                "avg_ms": round(sum(values) / len(values), 1),
                "max_ms": max(values),
            }
        return {"counters": dict(_counters), "timings": timings}
