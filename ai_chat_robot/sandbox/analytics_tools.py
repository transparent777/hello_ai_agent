"""数据分析工具（本机回退）：Docker 不可用时由普通 Agent 调用。"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from agents import function_tool

from sandbox.config import SCRIPTS_DIR
from sandbox.runtime import ensure_workspace_synced, publish_workspace_outputs

PYTHON = sys.executable


def _run_script(script_name: str, *args: str) -> str:
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
    if result.returncode != 0:
        return f"脚本执行失败（exit {result.returncode}）\n{err}\n{output}".strip()

    published = publish_workspace_outputs()
    footer = ""
    if published:
        footer = "\n\n已保存到 reports/：\n" + "\n".join(f"- {p}" for p in published)
    return (output or "执行完成，无标准输出。") + footer


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
