---
name: export-formats
description: 工作区导出 csv/xlsx/docx 的路径与工具说明
---

# 导出格式

| 格式 | 工具 | 输出路径建议 |
|------|------|--------------|
| CSV | `export_products_csv` / `export_orders_csv` / `export_table_csv` | `exports/*.csv` |
| XLSX | `export_table_xlsx` | `exports/*.xlsx` |
| DOCX | `export_docx` | `exports/*.docx` 或 `notes/*.docx` |
| MD/TXT | `write_file` | `notes/*.md`（需审批） |

- CSV 自动 UTF-8 BOM，Excel 中文友好。
- `data/` 只读，不可写入。
- 写入 `workspace_user/` 下相对路径。
