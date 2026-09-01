#!/usr/bin/env python3
"""汇总分析与定价结果，生成 Markdown 报表。"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import output_dir, workspace_root  # noqa: E402


def _run_script(name: str, *extra: str) -> None:
    scripts = workspace_root() / "scripts"
    cmd = [sys.executable, str(scripts / name), *extra]
    subprocess.run(cmd, check=True)


def main() -> None:
    out = output_dir()
    _run_script("analyze_orders.py")
    _run_script("pricing.py", "--category", "外设", "--discount", "0.9")

    analysis = json.loads((out / "analysis_summary.json").read_text(encoding="utf-8"))
    pricing = json.loads((out / "pricing.json").read_text(encoding="utf-8"))

    lines = [
        "# 电商运营日报（模拟）",
        "",
        f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## 订单概览",
        "",
        f"- 订单总数：**{analysis['order_count']}**",
        f"- 订单总金额：**¥{analysis['total_amount']}**",
        "",
        "### 状态分布",
        "",
    ]
    for status, count in analysis["status_distribution"].items():
        lines.append(f"- {status}：{count} 单")

    lines.extend(["", "## 定价模拟（外设 9 折）", ""])
    for item in pricing.get("items", []):
        lines.append(
            f"- {item['name']}：¥{item['original_price']} → "
            f"¥{item['discounted_price']}"
        )

    report = "\n".join(lines) + "\n"
    report_path = out / "report.md"
    report_path.write_text(report, encoding="utf-8")
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    print(report)
    print(f"\n已写入 {report_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
