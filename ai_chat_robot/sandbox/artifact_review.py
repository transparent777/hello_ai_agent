"""产物出沙箱前的审查（P0 安全：拦截疑似密钥与超大文件）。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from sandbox.audit import log_audit_event
from sandbox.settings import ARTIFACT_MAX_BYTES

_BLOCKED_PATTERNS = re.compile(
    r"(?:sk-[a-zA-Z0-9]{10,}|"
    r"DEEPSEEK_API_KEY\s*=|"
    r"OPENAI_API_KEY\s*=|"
    r"api[_-]?key\s*[:=]\s*['\"]?\w{8,}|"
    r"password\s*[:=]\s*['\"]?\S+)",
    re.IGNORECASE,
)


@dataclass
class ArtifactReviewResult:
    approved: list[Path]
    rejected: list[tuple[Path, str]]


def review_output_file(path: Path) -> str | None:
    """通过返回 None；拒绝返回原因字符串。"""
    if not path.is_file():
        return "不是普通文件"
    try:
        size = path.stat().st_size
    except OSError as exc:
        return str(exc)
    if size > ARTIFACT_MAX_BYTES:
        return f"文件过大（{size} > {ARTIFACT_MAX_BYTES} 字节）"

    try:
        sample = path.read_bytes()[:65536]
    except OSError as exc:
        return str(exc)

    text = sample.decode("utf-8", errors="replace")
    if _BLOCKED_PATTERNS.search(text):
        return "内容疑似包含密钥或凭证"

    return None


def review_output_dir(output_dir: Path) -> ArtifactReviewResult:
    approved: list[Path] = []
    rejected: list[tuple[Path, str]] = []

    if not output_dir.exists():
        return ArtifactReviewResult(approved=approved, rejected=rejected)

    for src in sorted(output_dir.iterdir()):
        if not src.is_file() or src.name == ".gitkeep":
            continue
        reason = review_output_file(src)
        if reason:
            rejected.append((src, reason))
            log_audit_event(
                "artifact_rejected",
                status="blocked",
                detail=reason,
                extra={"path": str(src)},
            )
        else:
            approved.append(src)

    return ArtifactReviewResult(approved=approved, rejected=rejected)
