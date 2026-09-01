"""沙箱 Docker E2E 测试（P1）。"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sandbox.config import build_docker_client, build_docker_options, build_manifest
from sandbox.health import check_sandbox_health
from sandbox.runtime import ensure_workspace_synced, is_docker_available


async def _run_analyze_orders_in_container() -> None:
    ensure_workspace_synced()
    health = check_sandbox_health(pull_if_missing=True)
    if not health.ok:
        raise RuntimeError("; ".join(health.issues))

    client = build_docker_client()
    options = build_docker_options()
    manifest = build_manifest()
    session = await client.create(manifest=manifest, options=options)
    try:
        async with session:
            result = await session.exec(
                "python",
                "scripts/analyze_orders.py",
                shell=False,
            )
            assert result.exit_code == 0, (result.stderr or result.stdout).decode(
                "utf-8", errors="replace"
            )
            output = result.stdout.decode("utf-8", errors="replace")
            assert "order_count" in output
    finally:
        await client.delete(session)


def main() -> int:
    if not is_docker_available():
        print("SKIP: Docker 不可用")
        return 0
    asyncio.run(_run_analyze_orders_in_container())
    print("PASS: sandbox E2E analyze_orders.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
