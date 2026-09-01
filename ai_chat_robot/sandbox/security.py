"""沙箱安全策略：Shell 仅允许 python，禁止危险命令。"""

from __future__ import annotations

import asyncio
import re
import shlex
import time

from agents.sandbox.capabilities.tools.shell_tool import ExecCommandArgs
from agents.sandbox.capabilities.shell import ShellToolSet

from sandbox.audit import log_audit_event
from sandbox.settings import SANDBOX_EXEC_TIMEOUT_SECONDS

# 允许的命令前缀（小写比较）
_ALLOWED_PREFIXES = (
    "python ",
    "python3 ",
    "/usr/bin/python ",
    "/usr/bin/python3 ",
    "/usr/local/bin/python ",
    "/usr/local/bin/python3 ",
)

# 明确禁止（即使伪装成 python -c）
_BLOCKED_PATTERNS = re.compile(
    r"(?:^|[\s;&|])(?:rm|curl|wget|nc|bash|sh|chmod|chown|kill|pkill|sudo|apt|pip)\b",
    re.IGNORECASE,
)

SANDBOX_INSTRUCTIONS = """
你在隔离沙箱 /workspace 中工作，只能使用 exec_command 执行 Python 脚本。

启动时请阅读：
- repo/task.md — 任务规格与标准命令
- repo/AGENTS.md — 路径与读写边界
- 按需使用 Skills（订单字段、定价规则）

硬性规则：
1. 只允许执行 `python` 或 `python3`，且必须运行 scripts/ 下的脚本。
2. 禁止 rm、curl、wget、bash、pip install 等任何非 Python 启动命令。
3. 只读分析 data/ 下的 JSON；结果写入 output/，不要修改 data/、scripts/、repo/。
4. 沙箱无外网，不要尝试下载或访问 URL。
5. 一律使用工作区相对路径，例如 data/orders.json、output/report.md。
6. 若存在 memories/memory_summary.md，可参考历史分析结论，但仍需执行脚本验证。

推荐命令：
- python scripts/analyze_orders.py
- python scripts/pricing.py --category 外设 --discount 0.9
- python scripts/generate_report.py
""".strip()


def assert_python_only_command(command: str) -> None:
    """校验命令是否符合白名单；不符合则抛 ValueError。"""
    cmd = command.strip()
    if not cmd:
        raise ValueError("空命令不允许执行")

    if _BLOCKED_PATTERNS.search(cmd):
        raise ValueError(f"命令包含禁止的操作: {cmd!r}")

    lowered = cmd.lower()
    if not any(lowered.startswith(prefix) for prefix in _ALLOWED_PREFIXES):
        raise ValueError(
            "Shell 白名单仅允许 python/python3。"
            f" 被拒绝: {cmd!r}"
        )

    # 要求脚本路径在 scripts 目录（防止 python -c '...' 任意代码）
    try:
        parts = shlex.split(cmd)
    except ValueError as exc:
        raise ValueError(f"无法解析命令: {cmd!r}") from exc

    if len(parts) < 2:
        raise ValueError("必须指定要运行的脚本，例如: python scripts/analyze_orders.py")

    script = parts[1].replace("\\", "/")
    if not (
        script.startswith("scripts/")
        or script.startswith("/workspace/scripts/")
    ):
        raise ValueError(
            "只能运行 scripts/ 目录下的脚本。"
            f" 当前: {script!r}"
        )


def restrict_shell_toolset(toolset: ShellToolSet) -> None:
    """挂到 Shell(configure_tools=...)：禁用交互 stdin，并拦截非 python 命令。"""
    toolset.write_stdin = None

    exec_tool = toolset.exec_command
    original_run = exec_tool.run

    async def guarded_run(args: ExecCommandArgs) -> str:
        started = time.perf_counter()
        command = args.cmd
        try:
            assert_python_only_command(command)
        except ValueError as exc:
            log_audit_event(
                "shell_exec_blocked",
                command=command,
                status="blocked",
                detail=str(exc),
            )
            return f"BLOCKED_BY_POLICY: {exc}"

        try:
            result = await asyncio.wait_for(
                original_run(args),
                timeout=SANDBOX_EXEC_TIMEOUT_SECONDS,
            )
            duration_ms = int((time.perf_counter() - started) * 1000)
            log_audit_event(
                "shell_exec",
                command=command,
                status="ok",
                duration_ms=duration_ms,
            )
            return result
        except asyncio.TimeoutError:
            duration_ms = int((time.perf_counter() - started) * 1000)
            log_audit_event(
                "shell_exec_timeout",
                command=command,
                status="timeout",
                duration_ms=duration_ms,
                detail=f"超过 {SANDBOX_EXEC_TIMEOUT_SECONDS}s",
            )
            return (
                f"BLOCKED_BY_POLICY: 命令执行超时（>{SANDBOX_EXEC_TIMEOUT_SECONDS}s）: "
                f"{command!r}"
            )
        except Exception as exc:
            duration_ms = int((time.perf_counter() - started) * 1000)
            log_audit_event(
                "shell_exec_failed",
                command=command,
                status="error",
                duration_ms=duration_ms,
                detail=str(exc),
            )
            raise

    exec_tool.run = guarded_run  # type: ignore[method-assign]

