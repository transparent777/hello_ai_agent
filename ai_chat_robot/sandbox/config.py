"""电商 Sandbox 配置：Docker 本地、Shell 白名单、会话持久化与记忆。"""

from __future__ import annotations

from pathlib import Path

from agents.run_config import RunConfig, SandboxArchiveLimits, SandboxRunConfig
from agents.sandbox import Manifest
from agents.sandbox.capabilities import Filesystem, Memory, Shell, Skills
from agents.sandbox.capabilities.skills import LocalDirLazySkillSource
from agents.sandbox.config import MemoryReadConfig
from agents.sandbox.entries import Dir, LocalDir
from agents.sandbox.manifest import Environment
from agents.sandbox.types import FileMode, Permissions
from agents.sandbox.workspace_paths import SandboxPathGrant

from sandbox.memory_sync import has_memory_summary, memories_dir
from sandbox.security import (
    SANDBOX_INSTRUCTIONS,
    assert_python_only_command,
    restrict_shell_toolset,
)
from sandbox.session_store import load_sandbox_resume_payload
from sandbox.settings import (
    SANDBOX_DOCKER_IMAGE,
    SANDBOX_MEMORY_ENABLED,
    SANDBOX_PIN_IMAGE_DIGEST,
    SANDBOX_PERSIST_SESSION,
)

# ai_chat_robot/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SANDBOX_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = SANDBOX_DIR / "scripts"
SKILLS_DIR = SANDBOX_DIR / "skills"
WORKSPACE_DIR = SANDBOX_DIR / "workspace"
DATA_DIR = PROJECT_ROOT / "data"
REPORTS_DIR = PROJECT_ROOT / "reports"
DEFAULT_DOCKER_IMAGE = SANDBOX_DOCKER_IMAGE

# 沙箱内路径（与 Manifest.root 一致）
SANDBOX_WORKSPACE = "/workspace"
SANDBOX_CWD = "."
SANDBOX_DATA = f"{SANDBOX_WORKSPACE}/data"
SANDBOX_SCRIPTS = f"{SANDBOX_WORKSPACE}/scripts"
SANDBOX_OUTPUT = f"{SANDBOX_WORKSPACE}/output"
SANDBOX_REPO = f"{SANDBOX_WORKSPACE}/repo"
SANDBOX_MEMORIES = f"{SANDBOX_WORKSPACE}/memories"

_READ_ONLY_DIR_PERMS = Permissions(
    owner=FileMode.READ | FileMode.EXEC,
    group=FileMode.READ | FileMode.EXEC,
    other=FileMode.READ | FileMode.EXEC,
    directory=True,
)


def _read_only_local_dir(src: Path) -> LocalDir:
    return LocalDir(src=src, permissions=_READ_ONLY_DIR_PERMS)


def build_manifest(*, session_id: str | None = None) -> Manifest:
    """声明沙箱启动时要带入工作区的文件（需先运行 sync_workspace.py）。"""
    entries: dict = {
        "repo": _read_only_local_dir(WORKSPACE_DIR / "repo"),
        "data": _read_only_local_dir(WORKSPACE_DIR / "data"),
        "scripts": _read_only_local_dir(WORKSPACE_DIR / "scripts"),
        "output": Dir(),
    }
    if session_id and SANDBOX_MEMORY_ENABLED and has_memory_summary(session_id):
        entries["memories"] = _read_only_local_dir(memories_dir(session_id))

    grants = [
        SandboxPathGrant(
            path=f"{SANDBOX_WORKSPACE}/repo",
            read_only=True,
            description="任务规格与 Agent 约定",
        ),
        SandboxPathGrant(
            path=f"{SANDBOX_WORKSPACE}/data",
            read_only=True,
            description="订单/商品 JSON 只读",
        ),
        SandboxPathGrant(
            path=f"{SANDBOX_WORKSPACE}/scripts",
            read_only=True,
            description="分析脚本只读",
        ),
    ]
    if "memories" in entries:
        grants.append(
            SandboxPathGrant(
                path=SANDBOX_MEMORIES,
                read_only=True,
                description="跨运行分析记忆（只读）",
            )
        )

    return Manifest(
        root=SANDBOX_WORKSPACE,
        entries=entries,
        environment=Environment(
            value={
                "PYTHONUNBUFFERED": "1",
                "SANDBOX_APP": "ecommerce-analytics",
            }
        ),
        extra_path_grants=tuple(grants),
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

    from sandbox.health import resolve_docker_image

    image = (
        resolve_docker_image(DEFAULT_DOCKER_IMAGE)
        if SANDBOX_PIN_IMAGE_DIGEST
        else DEFAULT_DOCKER_IMAGE
    )
    return DockerSandboxClientOptions(
        image=image,
        network_mode="none",
    )


def build_sandbox_capabilities() -> list:
    """filesystem + 受限 shell + skills +（可选）memory 只读。"""
    capabilities: list = [
        Filesystem(),
        Shell(configure_tools=restrict_shell_toolset),
    ]
    if SKILLS_DIR.exists():
        capabilities.append(
            Skills(
                lazy_from=LocalDirLazySkillSource(
                    source=LocalDir(src=SKILLS_DIR),
                ),
                skills_path=".agents/skills",
            )
        )
    if SANDBOX_MEMORY_ENABLED:
        capabilities.append(
            Memory(
                read=MemoryReadConfig(live_update=False),
                generate=None,
            )
        )
    return capabilities


def build_sandbox_run_config(
    *,
    session_id: str | None = None,
    persist_session: bool | None = None,
) -> SandboxRunConfig:
    """
    构建 SandboxRunConfig。

    persist_session=True 时尝试从 session_store 恢复 session_state（resume）。
    """
    use_persist = SANDBOX_PERSIST_SESSION if persist_session is None else persist_session
    session_state = None
    if use_persist and session_id:
        payload = load_sandbox_resume_payload(session_id)
        if payload is not None:
            from sandbox.session_store import deserialize_session_state

            try:
                session_state = deserialize_session_state(payload)
            except Exception:
                session_state = None

    return SandboxRunConfig(
        client=build_docker_client(),
        options=build_docker_options(),
        manifest=build_manifest(session_id=session_id),
        session_state=session_state,
        cwd=SANDBOX_CWD,
        archive_limits=SandboxArchiveLimits(),
    )


def merge_run_config_with_sandbox(
    base: RunConfig,
    *,
    session_id: str | None = None,
    persist_session: bool | None = None,
) -> RunConfig:
    """把现有 DeepSeek RunConfig 与 Sandbox 配置合并。"""
    return RunConfig(
        model_provider=base.model_provider,
        model=base.model,
        tracing_disabled=base.tracing_disabled,
        tool_not_found_behavior=base.tool_not_found_behavior,
        sandbox=build_sandbox_run_config(
            session_id=session_id,
            persist_session=persist_session,
        ),
    )


__all__ = [
    "SANDBOX_INSTRUCTIONS",
    "SANDBOX_DATA",
    "SANDBOX_MEMORIES",
    "SANDBOX_OUTPUT",
    "SANDBOX_REPO",
    "SANDBOX_SCRIPTS",
    "SANDBOX_WORKSPACE",
    "build_manifest",
    "build_sandbox_capabilities",
    "build_sandbox_run_config",
    "merge_run_config_with_sandbox",
    "assert_python_only_command",
]
