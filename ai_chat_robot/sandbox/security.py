"""沙箱安全策略：Shell 仅允许 python，禁止危险命令。"""

from __future__ import annotations

import re
import shlex

from agents.sandbox.capabilities.tools.shell_tool import ExecCommandArgs
from agents.sandbox.capabilities.shell import ShellToolSet

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

硬性规则：
1. 只允许执行 `python` 或 `python3` 命令，且必须运行 /workspace/scripts/ 下的脚本。
2. 禁止 rm、curl、wget、bash、pip install 等任何非 Python 启动命令。
3. 只读分析 data/ 下的 JSON；结果写入 output/，不要修改 data/ 源文件。
4. 沙箱无外网，不要尝试下载或访问 URL。

推荐命令示例：
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
        try:
            assert_python_only_command(args.cmd)
        except ValueError as exc:
            return f"BLOCKED_BY_POLICY: {exc}"
        return await original_run(args)

    exec_tool.run = guarded_run  # type: ignore[method-assign]
