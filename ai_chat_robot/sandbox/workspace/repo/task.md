# 电商数据分析任务规格

## 工作区路径（均相对于 `/workspace`）

| 路径 | 权限 | 说明 |
|------|------|------|
| `repo/` | 只读 | 本文件与 `AGENTS.md` |
| `data/` | 只读 | `orders.json`、`products.json` |
| `scripts/` | 只读 | 分析脚本 |
| `output/` | 可写 | 所有结果必须写在这里 |

## 标准工作流

1. **订单分析** → `python scripts/analyze_orders.py`  
   输出：`output/analysis_summary.json`

2. **定价模拟** → `python scripts/pricing.py --category <品类> --discount <系数>`  
   输出：`output/pricing.json`  
   示例：`python scripts/pricing.py --category 外设 --discount 0.9`

3. **综合报表** → `python scripts/generate_report.py`  
   输出：`output/report.md`（会调用上述脚本）

## 输出要求

- 用中文向用户总结关键数字（订单数、金额、状态分布等）。
- 明确告知结果文件路径，例如 `output/report.md`。
- 不要修改 `data/` 源文件；不要编造未执行脚本的数据。

## 禁止事项

- 非 `scripts/` 下的 Python 命令
- 修改 `data/`、`scripts/`、`repo/`
- 访问外网或下载资源
