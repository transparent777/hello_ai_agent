"""数据分析工具：优先 Docker 沙箱执行，可选本机回退。"""

from __future__ import annotations

import asyncio
import subprocess
import sys
from pathlib import Path

from agents import function_tool

from sandbox.audit import log_audit_event
from sandbox.config import SCRIPTS_DIR, build_docker_client, build_docker_options, build_manifest
from sandbox.health import check_sandbox_health
from sandbox.runtime import ensure_workspace_synced, is_docker_available, publish_workspace_outputs
from sandbox.settings import SANDBOX_ALLOW_LOCAL_FALLBACK

PYTHON = sys.executable


def _fallback_disabled_message() -> str:
    return (
        "数据分析脚本无法执行：请启动 Docker Desktop，"
        "或设置 SANDBOX_ALLOW_LOCAL_FALLBACK=true 允许本机回退。"
    )


def _run_script_local(script_name: str, *args: str) -> str:
    if not SANDBOX_ALLOW_LOCAL_FALLBACK:
        log_audit_event("local_fallback_blocked", status="blocked", detail=script_name)
        return _fallback_disabled_message()

    ensure_workspace_synced()
    script = SCRIPTS_DIR / script_name
    if not script.exists():
        return f"未找到脚本 {script}，请先运行 python sandbox/sync_workspace.py"

    cmd = [PYTHON, str(script), *args]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(SCRIPTS_DIR.parent),
    )
    output = (result.stdout or "").strip()
    err = (result.stderr or "").strip()
    log_audit_event(
        "local_fallback_exec",
        command=" ".join(cmd),
        exit_code=result.returncode,
        status="ok" if result.returncode == 0 else "error",
    )
    if result.returncode != 0:
        return f"脚本执行失败（exit {result.returncode}）\n{err}\n{output}".strip()

    published = publish_workspace_outputs()
    footer = ""
    if published:
        footer = "\n\n已保存到 reports/：\n" + "\n".join(f"- {p}" for p in published)
    return (output or "执行完成，无标准输出。") + footer


async def _run_script_in_docker(script_name: str, *args: str) -> str:
    ensure_workspace_synced()
    health = check_sandbox_health(pull_if_missing=True)
    if not health.ok:
        return "沙箱不可用：" + "; ".join(health.issues)

    script = SCRIPTS_DIR / script_name
    if not script.exists():
        return f"未找到脚本 {script}，请先运行 python sandbox/sync_workspace.py"

    client = build_docker_client()
    options = build_docker_options()
    manifest = build_manifest()
    session = await client.create(manifest=manifest, options=options)
    cmd = ("python", f"scripts/{script_name}", *args)
    try:
        async with session:
            result = await session.exec(*cmd, shell=False)
    finally:
        await client.delete(session)

    stdout = (result.stdout or b"").decode("utf-8", errors="replace").strip()
    stderr = (result.stderr or b"").decode("utf-8", errors="replace").strip()
    log_audit_event(
        "docker_script_exec",
        command=" ".join(cmd),
        exit_code=result.exit_code,
        status="ok" if result.exit_code == 0 else "error",
    )
    if result.exit_code != 0:
        return f"脚本执行失败（exit {result.exit_code}）\n{stderr}\n{stdout}".strip()

    published = publish_workspace_outputs()
    footer = ""
    if published:
        footer = "\n\n已保存到 reports/：\n" + "\n".join(f"- {p}" for p in published)
    return (stdout or "执行完成，无标准输出。") + footer


def _run_script(script_name: str, *args: str) -> str:
    if is_docker_available():
        return asyncio.run(_run_script_in_docker(script_name, *args))
    return _run_script_local(script_name, *args)


@function_tool
def run_order_analysis() -> str:
    """分析 orders.json：订单数量、金额、状态分布。"""
    return _run_script("analyze_orders.py")


@function_tool
def run_pricing_simulation(category: str = "", discount: float = 0.95) -> str:
    """定价模拟。category 为空表示全部商品；discount 如 0.9 表示九折。"""
    args: list[str] = ["--discount", str(discount)]
    if category.strip():
        args.extend(["--category", category.strip()])
    return _run_script("pricing.py", *args)


@function_tool
def run_sales_report() -> str:
    """生成销售分析报表（Markdown），含订单概览与外设定价示例。"""
    return _run_script("generate_report.py")
