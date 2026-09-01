---
name: pricing-rules
description: 定价模拟参数与输出说明
---

# 定价模拟规则

脚本：`scripts/pricing.py`

| 参数 | 说明 |
|------|------|
| `--category` | 按品类筛选，空表示全部商品 |
| `--discount` | 折扣系数，`0.9` 表示九折 |

输出：`output/pricing.json`，包含原价、折后价与品类信息。

示例：

```bash
python scripts/pricing.py --category 外设 --discount 0.9
```
