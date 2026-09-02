"""生成电商演示数据：商品目录与订单。运行后写入 data/ 目录。"""

from __future__ import annotations

import json
import random
from datetime import date, timedelta
from pathlib import Path

from config.paths import DATA_DIR

ROOT = DATA_DIR.parent

PRODUCT_TEMPLATES = [
    ("无线蓝牙耳机 Pro", "数码", 299, "降噪长续航，适合通勤"),
    ("机械键盘 87 键", "外设", 459, "青轴手感，办公游戏两用"),
    ("27 寸 4K 显示器", "显示器", 1899, "IPS 面板，Type-C 一线通"),
    ("人体工学办公椅", "家具", 1299, "腰托可调，久坐舒适"),
    ("轻薄笔记本电脑 14 寸", "电脑", 5299, "16G 内存，512G SSD"),
    ("智能手表 S2", "穿戴", 899, "心率血氧监测，7 天续航"),
    ("USB-C 扩展坞", "配件", 199, "HDMI + 网口 + SD 卡槽"),
    ("电竞鼠标", "外设", 329, "轻量化设计，无线低延迟"),
]

CARRIERS = ["顺丰速运", "中通快递", "圆通速递", "京东物流"]
STATUSES = ["待发货", "运输中", "派送中", "已签收", "退款处理中"]


def generate_products(count: int = 8, seed: int = 42) -> list[dict]:
    rng = random.Random(seed)
    products: list[dict] = []
    for idx, (name, category, base_price, desc) in enumerate(PRODUCT_TEMPLATES[:count], start=1):
        price = base_price + rng.randint(-30, 80)
        products.append(
            {
                "id": f"P{idx:04d}",
                "name": name,
                "category": category,
                "price": max(price, 99),
                "stock": rng.randint(5, 200),
                "description": desc,
            }
        )
    return products


def generate_orders(products: list[dict], count: int = 12, seed: int = 42) -> list[dict]:
    rng = random.Random(seed + 1)
    today = date(2026, 8, 31)
    orders: list[dict] = []

    for i in range(1, count + 1):
        item_count = rng.randint(1, 3)
        items = []
        total = 0
        for _ in range(item_count):
            product = rng.choice(products)
            qty = rng.randint(1, 2)
            line_total = product["price"] * qty
            total += line_total
            items.append(
                {
                    "product_id": product["id"],
                    "name": product["name"],
                    "quantity": qty,
                    "unit_price": product["price"],
                }
            )

        status = rng.choice(STATUSES)
        eta = (today + timedelta(days=rng.randint(1, 5))).isoformat()
        orders.append(
            {
                "order_id": f"{10000 + i}",
                "user_id": f"U{rng.randint(100, 999)}",
                "status": status,
                "carrier": rng.choice(CARRIERS),
                "tracking_no": f"SF{rng.randint(10**9, 10**10 - 1)}",
                "eta": eta,
                "items": items,
                "total": total,
            }
        )
    return orders


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    products = generate_products()
    orders = generate_orders(products)

    products_path = DATA_DIR / "products.json"
    orders_path = DATA_DIR / "orders.json"

    products_path.write_text(
        json.dumps(products, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    orders_path.write_text(
        json.dumps(orders, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"已生成 {len(products)} 个商品 -> {products_path}")
    print(f"已生成 {len(orders)} 个订单 -> {orders_path}")
    print(f"示例订单号: {orders[0]['order_id']}")


if __name__ == "__main__":
    main()
