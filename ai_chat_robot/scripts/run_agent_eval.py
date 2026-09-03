"""基于 dataset.json 的轻量 Agent 评估运行器。"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

_APP_DIR = Path(__file__).resolve().parent.parent
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

from agents import SQLiteSession
from agents.tracing import flush_traces

from orchestrator import SESSION_DB, build_run_config, handle_user_turn
from services.tracing import TRACING_EVAL_SAMPLES_PATH, configure_tracing
from specialists import workspace_router

DATASET = _APP_DIR / "eval" / "dataset.json"


def _score_case(text: str | None, case: dict) -> tuple[bool, str]:
    if case.get("expected_tripwire"):
        ok = text is not None and ("护栏" in text or "助手" in text or "拦截" in text)
        return ok, "guardrail_tripwire" if ok else f"expected tripwire, got: {text!r}"

    if not text:
        return False, "empty response"
    keywords = case.get("expected_keywords") or []
    missing = [kw for kw in keywords if kw not in text]
    if missing:
        return False, f"missing keywords: {missing}"
    return True, "ok"


async def _run_case(case: dict) -> dict:
    session_id = f"eval_{case['id']}"
    session = SQLiteSession(session_id, db_path=SESSION_DB)
    run_config = build_run_config(session_id=session_id)

    text, result, _steps = await handle_user_turn(
        workspace_router,
        case["prompt"],
        session,
        run_config,
    )
    ok, detail = _score_case(text, case)
    return {
        "id": case["id"],
        "ok": ok,
        "detail": detail,
        "response_preview": (text or "")[:200],
        "interrupted": result is not None and hasattr(result, "interruption_summaries"),
    }


async def main() -> int:
    configure_tracing()
    cases = json.loads(DATASET.read_text(encoding="utf-8"))
    results = []
    for case in cases:
        print(f"Running {case['id']} ...")
        results.append(await _run_case(case))
    flush_traces()

    passed = sum(1 for r in results if r["ok"])
    report_path = _APP_DIR / "eval" / "last_report.json"
    report_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nEval: {passed}/{len(results)} passed")
    print(f"Report: {report_path}")
    print(f"High-signal traces: {TRACING_EVAL_SAMPLES_PATH}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
