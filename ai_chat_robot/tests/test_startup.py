from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_specialist_import_has_no_optional_rag_startup_noise() -> None:
    script = (
        "import warnings; "
        "warnings.filterwarnings('error', message='.*validate_default.*'); "
        "from specialists import workspace_router"
    )
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=False,
    )

    combined_output = result.stdout + result.stderr
    assert result.returncode == 0, combined_output
    assert "resource module not available on Windows" not in combined_output
    assert "UnsupportedFieldAttributeWarning" not in combined_output


def test_rag_import_suppresses_known_third_party_noise() -> None:
    script = (
        "import warnings; "
        "warnings.filterwarnings('error', message='.*validate_default.*'); "
        "from rag.hybrid import BM25Retriever"
    )
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=False,
    )

    combined_output = result.stdout + result.stderr
    assert result.returncode == 0, combined_output
    assert "resource module not available on Windows" not in combined_output
    assert "UnsupportedFieldAttributeWarning" not in combined_output
