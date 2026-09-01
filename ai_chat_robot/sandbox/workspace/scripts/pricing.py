#!/usr/bin/env python3
"""定价模拟：按品类折扣，输出 pricing.json。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import data_dir, output_dir  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="商品定价模拟")
    parser.add_argument("--category", default="", help="按品类筛选，如：外设")
    parser.add_argument(
        "--discount",
        type=float,
        default=0.95,
        help="折扣系数，0.9 表示 9 折",
    )
    args = parser.parse_args()

    products_path = data_dir() / "products.json"
    if not products_path.exists():
        raise SystemExit(f"未找到 {products_path}")

    products = json.loads(products_path.read_text(encoding="utf-8"))
    selected = products
    if args.category:
        selected = [p for p in products if args.category in p.get("category", "")]

    results = []
    for item in selected:
        old_price = item["price"]
        new_price = round(old_price * args.discount, 2)
        results.append(
            {
                "product_id": item["id"],
                "name": item["name"],
                "category": item["category"],
                "original_price": old_price,
                "discounted_price": new_price,
                "discount": args.discount,
            }
        )

    payload = {
        "category_filter": args.category or "(全部)",
        "discount": args.discount,
        "items": results,
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    print(text)

    out = output_dir() / "pricing.json"
    out.write_text(text, encoding="utf-8")
    print(f"\n已写入 {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
