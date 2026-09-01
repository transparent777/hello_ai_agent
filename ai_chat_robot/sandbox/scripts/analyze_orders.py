#!/usr/bin/env python3
"""分析 orders.json：订单数量、金额、状态分布。"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import data_dir, output_dir  # noqa: E402


def main() -> None:
    orders_path = data_dir() / "orders.json"
    if not orders_path.exists():
        raise SystemExit(f"未找到 {orders_path}")

    orders = json.loads(orders_path.read_text(encoding="utf-8"))
    status_counts = Counter(o["status"] for o in orders)
    total_amount = sum(o.get("total", 0) for o in orders)

    summary = {
        "order_count": len(orders),
        "total_amount": total_amount,
        "status_distribution": dict(status_counts),
        "sample_order_ids": [o["order_id"] for o in orders[:5]],
    }

    text = json.dumps(summary, ensure_ascii=False, indent=2)
    print(text)

    out = output_dir() / "analysis_summary.json"
    out.write_text(text, encoding="utf-8")
    print(f"\n已写入 {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
