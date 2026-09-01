"""沙箱运维：并发限制、重试、僵尸容器清理（P0/P1）。"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Any, TypeVar

from sandbox.audit import log_audit_event
from sandbox.settings import (
    SANDBOX_MAX_CONCURRENT_SESSIONS,
    SANDBOX_RUN_MAX_RETRIES,
    SANDBOX_STALE_CONTAINER_MAX_AGE_HOURS,
)

T = TypeVar("T")

_session_semaphore: asyncio.Semaphore | None = None


def get_session_semaphore() -> asyncio.Semaphore:
    global _session_semaphore
    if _session_semaphore is None:
        limit = max(1, SANDBOX_MAX_CONCURRENT_SESSIONS)
        _session_semaphore = asyncio.Semaphore(limit)
    return _session_semaphore


async def run_with_sandbox_slot(
    coro_factory: Callable[[], Awaitable[T]],
    *,
    timeout_seconds: int,
) -> T:
    sem = get_session_semaphore()
    async with sem:
        return await asyncio.wait_for(coro_factory(), timeout=timeout_seconds)


def _container_image_matches(container: Any, image_ref: str) -> bool:
    tags = container.image.tags or []
    image_id = container.image.id or ""
    short_id = image_id.split(":")[-1][:12] if image_id else ""
    ref = image_ref.split("@")[0]
    repo, _, tag = ref.partition(":")
    tag = tag or "latest"
    candidates = {image_ref, ref, f"{repo}:{tag}", f"{repo}@sha256:{short_id}"}
    return any(t in candidates or t.startswith(repo) for t in tags) or image_ref in image_id


def cleanup_stale_sandbox_containers(image_ref: str) -> int:
    """清理已退出或超时的沙箱容器（best-effort）。"""
    try:
        import docker
    except ModuleNotFoundError:
        return 0

    client = docker.from_env()
    removed = 0
    now = datetime.now(timezone.utc)
    max_age_seconds = SANDBOX_STALE_CONTAINER_MAX_AGE_HOURS * 3600

    for container in client.containers.list(all=True):
        try:
            if not _container_image_matches(container, image_ref):
                continue
            status = (container.status or "").lower()
            if status == "exited":
                container.remove(force=True)
                removed += 1
                continue
            created_raw = container.attrs.get("Created")
            if not created_raw:
                continue
            created = datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
            age = (now - created).total_seconds()
            if age > max_age_seconds and status == "running":
                container.stop(timeout=5)
                container.remove(force=True)
                removed += 1
        except Exception as exc:
            log_audit_event(
                "container_cleanup_failed",
                status="error",
                detail=str(exc),
                extra={"container_id": getattr(container, "id", None)},
            )
    if removed:
        log_audit_event("container_cleanup", status="ok", extra={"removed": removed})
    return removed


async def run_with_retries(
    coro_factory: Callable[[], Awaitable[T]],
    *,
    max_retries: int | None = None,
    retryable: Callable[[BaseException], bool] | None = None,
) -> T:
    attempts = max(1, (max_retries if max_retries is not None else SANDBOX_RUN_MAX_RETRIES) + 1)
    last_error: BaseException | None = None
    for attempt in range(1, attempts + 1):
        try:
            return await coro_factory()
        except BaseException as exc:
            last_error = exc
            if attempt >= attempts:
                break
            if retryable is not None and not retryable(exc):
                break
            if isinstance(exc, (asyncio.TimeoutError, KeyboardInterrupt, SystemExit)):
                break
            log_audit_event(
                "sandbox_run_retry",
                status="retry",
                detail=str(exc),
                extra={"attempt": attempt, "max_attempts": attempts},
            )
            await asyncio.sleep(min(2 ** (attempt - 1), 8))
    assert last_error is not None
    raise last_error
