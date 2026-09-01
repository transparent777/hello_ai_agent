"""Sandbox 运行时：Docker 检测、工作区同步、报表发布。"""

from __future__ import annotations

import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from sandbox.config import REPORTS_DIR, WORKSPACE_DIR

OUTPUT_DIR = WORKSPACE_DIR / "output"


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


def ensure_workspace_synced() -> None:
    """确保 sandbox/workspace 已有 data 与 scripts（Docker Manifest 与本机回退共用）。"""
    data_ok = (WORKSPACE_DIR / "data" / "orders.json").exists()
    scripts_ok = (WORKSPACE_DIR / "scripts" / "analyze_orders.py").exists()
    if data_ok and scripts_ok:
        return

    from sandbox.sync_workspace import main as sync_main

    sync_main()


def publish_workspace_outputs() -> list[str]:
    """将 output/ 中的结果复制到 reports/，返回已发布文件路径。"""
    if not OUTPUT_DIR.exists():
        return []

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = REPORTS_DIR / stamp
    run_dir.mkdir(parents=True, exist_ok=True)

    published: list[str] = []
    for src in OUTPUT_DIR.iterdir():
        if src.is_file() and src.name != ".gitkeep":
            dest = run_dir / src.name
            shutil.copy2(src, dest)
            published.append(str(dest))
    return published


def sandbox_mode_label() -> str:
    return "Docker 沙箱" if is_docker_available() else "本机脚本回退（未检测到 Docker）"
