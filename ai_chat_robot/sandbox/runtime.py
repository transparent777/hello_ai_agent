"""Sandbox 运行时：Docker 检测、工作区同步、报表发布。"""

from __future__ import annotations

import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from sandbox.settings import (
    SANDBOX_ALLOW_LOCAL_FALLBACK,
    SANDBOX_CLEANUP_ON_STARTUP,
    SANDBOX_DOCKER_IMAGE,
    SANDBOX_REQUIRE_DOCKER,
)

SANDBOX_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = SANDBOX_DIR / "workspace"
REPORTS_DIR = SANDBOX_DIR.parent / "reports"
OUTPUT_DIR = WORKSPACE_DIR / "output"
_startup_done = False


def is_docker_available() -> bool:
    """检查 docker 命令是否可用且 daemon 在运行。"""
    if not shutil.which("docker"):
        return False
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=15,
            check=False,
        )
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def analytics_backend_available() -> bool:
    """数据分析后端是否可用（Docker 或显式允许的本机回退）。"""
    if is_docker_available():
        return True
    return SANDBOX_ALLOW_LOCAL_FALLBACK


def ensure_workspace_synced() -> None:
    """确保 sandbox/workspace 已有 data、repo 与 scripts。"""
    global _startup_done
    data_ok = (WORKSPACE_DIR / "data" / "orders.json").exists()
    repo_ok = (WORKSPACE_DIR / "repo" / "task.md").exists()
    scripts_ok = (WORKSPACE_DIR / "scripts" / "analyze_orders.py").exists()
    if not (data_ok and repo_ok and scripts_ok):
        from sandbox.sync_workspace import main as sync_main

        sync_main()

    if _startup_done:
        return
    _startup_done = True

    if SANDBOX_CLEANUP_ON_STARTUP and is_docker_available():
        from sandbox.ops import cleanup_stale_sandbox_containers

        cleanup_stale_sandbox_containers(SANDBOX_DOCKER_IMAGE)


def publish_workspace_outputs() -> list[str]:
    """审查后将 output/ 复制到 reports/，返回已发布文件路径。"""
    from sandbox.artifact_review import review_output_dir

    if not OUTPUT_DIR.exists():
        return []

    review = review_output_dir(OUTPUT_DIR)
    if not review.approved:
        return []

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = REPORTS_DIR / stamp
    run_dir.mkdir(parents=True, exist_ok=True)

    published: list[str] = []
    for src in review.approved:
        dest = run_dir / src.name
        shutil.copy2(src, dest)
        published.append(str(dest))
    return published


def sandbox_mode_label() -> str:
    if is_docker_available():
        return "Docker 沙箱"
    if SANDBOX_ALLOW_LOCAL_FALLBACK:
        return "本机脚本回退（未检测到 Docker）"
    if SANDBOX_REQUIRE_DOCKER:
        return "不可用（需要 Docker）"
    return "本机脚本回退（未检测到 Docker）"
