"""pytest 入口：沙箱 E2E。"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_sandbox_e2e_analyze_orders() -> None:
    script = ROOT / "scripts" / "run_sandbox_e2e.py"
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )
    if "SKIP:" in (proc.stdout or ""):
        return
    assert proc.returncode == 0, proc.stdout + proc.stderr
