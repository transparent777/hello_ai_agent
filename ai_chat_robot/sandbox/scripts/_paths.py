"""沙箱工作区路径解析（本机 / Docker 通用）。"""

from __future__ import annotations

import os
from pathlib import Path


def workspace_root() -> Path:
    """Docker 内为 /workspace；本机为 sandbox/workspace。"""
    if Path("/workspace/data").exists():
        return Path("/workspace")

    env = os.getenv("SANDBOX_WORKSPACE")
    if env:
        return Path(env)

    scripts_dir = Path(__file__).resolve().parent
    # 已同步布局：sandbox/workspace/scripts/...
    if (scripts_dir.parent / "data").exists():
        return scripts_dir.parent
    # 源码布局：sandbox/scripts/...
    workspace = scripts_dir.parent / "workspace"
    return workspace


def data_dir() -> Path:
    return workspace_root() / "data"


def output_dir() -> Path:
    path = workspace_root() / "output"
    path.mkdir(parents=True, exist_ok=True)
    return path
