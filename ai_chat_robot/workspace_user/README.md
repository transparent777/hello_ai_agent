# 文件 Agent 工作区

Agent 只能在此目录内 **列出 / 读取 / 写入** 文件（路径均相对于本目录）。

示例：把 `demo/hello.txt` 交给 Agent 处理，或在聊天中说：

> 导出商品清单为 CSV  
> 导出订单清单到 exports/orders.csv  
> 读取 data/products.json 统计品类

**CSV 说明**：导出文件使用 **UTF-8 BOM** 编码，Excel 双击应能正常显示中文。若仍乱码，在 Excel 用「数据 → 从文本/CSV」并选择 UTF-8。

写入操作会触发 **人工审批**（与退款审批相同流程）。
