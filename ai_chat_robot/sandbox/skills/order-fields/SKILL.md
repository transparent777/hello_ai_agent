---
name: order-fields
description: 演示订单 JSON 字段说明，分析前可先查阅
---

# 订单数据字段

`data/orders.json` 为数组，每条订单常见字段：

| 字段 | 含义 |
|------|------|
| `order_id` | 订单号，如 `10001` |
| `status` | 待发货 / 运输中 / 派送中 / 已签收 / 退款处理中 |
| `total` | 订单金额（元） |
| `items` | 商品明细列表 |
| `carrier` | 物流公司 |
| `tracking_no` | 运单号 |

分析脚本 `scripts/analyze_orders.py` 会统计订单数、总金额与状态分布。
