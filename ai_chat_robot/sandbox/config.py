"""电商 Sandbox 配置：Docker 本地、Shell 白名单、不跨天保留。"""

from __future__ import annotations

import os
from pathlib import Path

from agents.run_config import RunConfig, SandboxRunConfig
from agents.sandbox import Manifest
from agents.sandbox.capabilities import Filesystem, Shell
from agents.sandbox.capabilities.shell import ShellToolSet
from agents.sandbox.entries import Dir, LocalDir

from sandbox.security import (
    SANDBOX_INSTRUCTIONS,
    assert_python_only_command,
    restrict_shell_toolset,
)

# ai_chat_robot/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SANDBOX_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = SANDBOX_DIR / "scripts"
WORKSPACE_DIR = SANDBOX_DIR / "workspace"
DATA_DIR = PROJECT_ROOT / "data"
REPORTS_DIR = PROJECT_ROOT / "reports"
DEFAULT_DOCKER_IMAGE = os.getenv("SANDBOX_DOCKER_IMAGE", "python:3.11-slim")

# 沙箱内路径（与 Manifest.root 一致）
SANDBOX_WORKSPACE = "/workspace"
SANDBOX_CWD = "."
SANDBOX_DATA = f"{SANDBOX_WORKSPACE}/data"
SANDBOX_SCRIPTS = f"{SANDBOX_WORKSPACE}/scripts"
SANDBOX_OUTPUT = f"{SANDBOX_WORKSPACE}/output"


def build_manifest() -> Manifest:
    """声明沙箱启动时要带入工作区的文件（需先运行 sync_workspace.py）。"""
    return Manifest(
        root=SANDBOX_WORKSPACE,
        entries={
            "data": LocalDir(src=WORKSPACE_DIR / "data"),
            "scripts": LocalDir(src=WORKSPACE_DIR / "scripts"),
            "output": Dir(),
        },
    )


def build_docker_client():
    """Docker 本地客户端（SDK 0.22+：client 与 options 分离）。"""
    try:
        import docker
        from agents.sandbox.sandboxes.docker import DockerSandboxClient
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            '缺少 Docker Python 包。请执行: pip install "openai-agents[docker]" docker'
        ) from exc

    return DockerSandboxClient(docker_client=docker.from_env())


def build_docker_options():
    """Docker 创建会话时的选项：默认禁外网（network_mode=none）。"""
    from agents.sandbox.sandboxes.docker import DockerSandboxClientOptions

    return DockerSandboxClientOptions(
        image=DEFAULT_DOCKER_IMAGE,
        network_mode="none",
    )


def build_sandbox_capabilities() -> list:
    """filesystem + 受限 shell（仅 python）。"""
    return [
        Filesystem(),
        Shell(configure_tools=restrict_shell_toolset),
    ]


def build_sandbox_run_config(
    *,
    persist_session: bool = False,
) -> SandboxRunConfig:
    """
    构建 SandboxRunConfig。

    persist_session=False：不跨天保留（你的第 5 项决策），每次 run 由 Runner 管理生命周期。
    """
    config = SandboxRunConfig(
        client=build_docker_client(),
        options=build_docker_options(),
        manifest=build_manifest(),
        cwd=SANDBOX_CWD,
    )
    if persist_session:
        # 预留：若以后要做跨天保留，在此注入 snapshot / session_state
        pass
    return config


def merge_run_config_with_sandbox(
    base: RunConfig,
    *,
    persist_session: bool = False,
) -> RunConfig:
    """把现有 DeepSeek RunConfig 与 Sandbox 配置合并。"""
    return RunConfig(
        model_provider=base.model_provider,
        model=base.model,
        tracing_disabled=base.tracing_disabled,
        tool_not_found_behavior=base.tool_not_found_behavior,
        sandbox=build_sandbox_run_config(persist_session=persist_session),
    )


__all__ = [
    "SANDBOX_INSTRUCTIONS",
    "SANDBOX_DATA",
    "SANDBOX_OUTPUT",
    "SANDBOX_SCRIPTS",
    "SANDBOX_WORKSPACE",
    "build_manifest",
    "build_sandbox_capabilities",
    "build_sandbox_run_config",
    "merge_run_config_with_sandbox",
    "assert_python_only_command",
]
