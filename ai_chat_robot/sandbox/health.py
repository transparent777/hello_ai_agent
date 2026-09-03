"""沙箱启动健康检查（P1）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sandbox.runtime import is_docker_available
from sandbox.settings import SANDBOX_DOCKER_IMAGE, SANDBOX_PIN_IMAGE_DIGEST


@dataclass
class SandboxHealthReport:
    ok: bool
    docker_available: bool
    image: str
    image_present: bool = False
    image_digest_pinned: bool = False
    issues: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "docker_available": self.docker_available,
            "image": self.image,
            "image_present": self.image_present,
            "image_digest_pinned": self.image_digest_pinned,
            "issues": list(self.issues),
            "details": dict(self.details),
        }


def resolve_docker_image(image_ref: str) -> str:
    """将 tag 解析为 digest（若可用）。"""
    if not SANDBOX_PIN_IMAGE_DIGEST or "@sha256:" in image_ref:
        return image_ref
    try:
        import docker
    except ModuleNotFoundError:
        return image_ref

    client = docker.from_env()
    try:
        image = client.images.get(image_ref)
    except Exception:
        repo, _, tag = image_ref.partition(":")
        tag = tag or "latest"
        client.images.pull(repo, tag=tag)
        image = client.images.get(image_ref)

    digests = image.attrs.get("RepoDigests") or []
    if digests:
        return digests[0]
    image_id = image.id or ""
    if image_id.startswith("sha256:"):
        repo = image_ref.split(":")[0] if ":" in image_ref else image_ref
        return f"{repo}@{image_id}"
    return image_ref


def check_sandbox_health(*, pull_if_missing: bool = False) -> SandboxHealthReport:
    report = SandboxHealthReport(
        ok=False,
        docker_available=is_docker_available(),
        image=SANDBOX_DOCKER_IMAGE,
    )

    if not report.docker_available:
        report.issues.append("Docker daemon 不可用，请启动 Docker Desktop。")
        return report

    try:
        import docker
    except ModuleNotFoundError:
        report.issues.append('缺少 Python docker 包，请执行: pip install "openai-agents[docker]" docker')
        return report

    client = docker.from_env()
    try:
        image = client.images.get(SANDBOX_DOCKER_IMAGE)
        report.image_present = True
        report.details["image_id"] = image.id
        report.details["repo_tags"] = image.attrs.get("RepoTags", [])
    except Exception:
        if pull_if_missing:
            repo, _, tag = SANDBOX_DOCKER_IMAGE.partition(":")
            tag = tag or "latest"
            client.images.pull(repo, tag=tag)
            image = client.images.get(SANDBOX_DOCKER_IMAGE)
            report.image_present = True
            report.details["image_id"] = image.id
        else:
            report.issues.append(f"本地未找到镜像 {SANDBOX_DOCKER_IMAGE}，请执行 docker pull。")
            return report

    resolved = resolve_docker_image(SANDBOX_DOCKER_IMAGE)
    report.image_digest_pinned = "@sha256:" in resolved
    report.details["resolved_image"] = resolved
    if SANDBOX_PIN_IMAGE_DIGEST and not report.image_digest_pinned:
        report.issues.append(
            "无法解析 Docker 镜像 digest；为避免使用可变标签，已拒绝该镜像。"
        )

    workspace_data = (
        Path(__file__).resolve().parent / "workspace" / "data" / "orders.json"
    )
    workspace_repo = (
        Path(__file__).resolve().parent / "workspace" / "repo" / "task.md"
    )
    if not workspace_data.exists():
        report.issues.append("sandbox/workspace/data/orders.json 不存在，请运行 sandbox/sync_workspace.py")
    if not workspace_repo.exists():
        report.issues.append("sandbox/workspace/repo/task.md 不存在，请运行 sandbox/sync_workspace.py")

    report.ok = not report.issues
    return report
