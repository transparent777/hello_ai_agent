# 数据分析任务规格

沙箱工作目录：`/workspace`（宿主机 `sandbox/workspace/`）。

## 数据

- `data/orders.json` — 示例订单数据集（只读）
- `data/products.json` — 示例商品目录（只读）
- `output/` — 脚本输出目录
- `repo/task.md` — 本说明

## 可用脚本（`scripts/`）

1. **订单分析** → `python scripts/analyze_orders.py`  
   统计订单数、总金额、状态分布，写入 `output/analysis_summary.json`
2. **定价模拟** → `python scripts/pricing.py --discount 0.9`  
   可选 `--category` 筛选品类
3. **报表生成** → `python scripts/generate_report.py`  
   生成 `output/report.md`

## 回复要求

- 用中文向用户总结关键数字（订单数、金额、状态分布等）。
- 说明产物路径（如 `output/report.md`，审查后会复制到 `reports/`）。
