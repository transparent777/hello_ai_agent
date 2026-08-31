"""电商 Agent 工具：从 data/ 目录读取商品与订单。"""

from __future__ import annotations

import json
from pathlib import Path

from agents import function_tool

DATA_DIR = Path(__file__).resolve().parent / "data"
PRODUCTS_FILE = DATA_DIR / "products.json"
ORDERS_FILE = DATA_DIR / "orders.json"


def _ensure_data_files() -> None:
    if not PRODUCTS_FILE.exists() or not ORDERS_FILE.exists():
        raise FileNotFoundError(
            "未找到商品/订单数据。请先运行：python scripts/generate_catalog.py"
        )


def _load_products() -> list[dict]:
    _ensure_data_files()
    return json.loads(PRODUCTS_FILE.read_text(encoding="utf-8"))


def _load_orders() -> list[dict]:
    _ensure_data_files()
    return json.loads(ORDERS_FILE.read_text(encoding="utf-8"))


def _find_order(order_id: str) -> dict | None:
    order_id = order_id.strip().lstrip("#")
    for order in _load_orders():
        if order["order_id"] == order_id:
            return order
    return None


@function_tool
def search_products(keyword: str) -> str:
    """按关键词搜索商品目录，返回名称、价格与库存。"""
    keyword_lower = keyword.lower()
    matches = [
        item
        for item in _load_products()
        if keyword_lower in item["name"].lower()
        or keyword_lower in item["category"].lower()
        or keyword_lower in item["description"].lower()
    ]
    if not matches:
        return f"未找到与「{keyword}」相关的商品。"
    lines = [
        (
            f"- [{item['id']}] {item['name']}（{item['category']}）"
            f"：¥{item['price']}，库存 {item['stock']} 件"
        )
        for item in matches
    ]
    return "搜索结果：\n" + "\n".join(lines)


@function_tool
def get_order_status(order_id: str) -> str:
    """查询订单状态、物流与预计送达时间。"""
    order = _find_order(order_id)
    if not order:
        return f"未找到订单 {order_id}，请核对订单号。"

    item_lines = [
        f"  · {item['name']} x{item['quantity']}（¥{item['unit_price']}）"
        for item in order["items"]
    ]
    return (
        f"订单 {order['order_id']}：{order['status']}\n"
        f"用户：{order['user_id']}\n"
        f"承运商：{order['carrier']}\n"
        f"运单号：{order['tracking_no']}\n"
        f"预计送达：{order['eta']}\n"
        f"订单金额：¥{order['total']}\n"
        f"商品明细：\n" + "\n".join(item_lines)
    )


@function_tool(needs_approval=True)
def process_refund(order_id: str, reason: str) -> str:
    """为指定订单发起退款申请（敏感操作，需人工审批）。"""
    order = _find_order(order_id)
    if not order:
        return f"未找到订单 {order_id}，无法发起退款。"

    if order["status"] == "已签收":
        return (
            f"订单 {order_id} 已签收，退款申请已记录。"
            f"原因：{reason}。客服将在 1-3 个工作日内审核。"
        )
    return (
        f"订单 {order_id} 当前状态为「{order['status']}」，"
        f"退款申请已提交。原因：{reason}。"
    )
