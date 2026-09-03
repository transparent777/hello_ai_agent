---
name: output-defaults
description: 默认用 Markdown 回复；仅当用户明确要求格式时才导出文件
---

# 输出默认规范

- **默认**：在对话里用 Markdown 直接回答（列表、加粗、代码块均可）。
- **不要**主动生成 csv/xlsx/docx，除非用户明确说了格式或「保存到文件」。
- 用户说「导出 csv」「做成 Excel」「Word 文档」→ 转 document_specialist 或调用对应 export 工具。
- 短文案、解释、讨论：L1 router 可直接回答，无需落盘。
