---
name: essay-docx
description: 长文/思政类作文导出 Word 的标准流程（L2 执行 + L1 验收）
---

# 作文导出 Word 流程（L2）

1. `read_skill('writing-style')`（可选）
2. 撰写 **纯文本** title + body（无 Markdown 符号）
3. **必须** `export_docx` → `exports/xxx.docx`
4. **必须** `transfer_to_workspace_router`，交接摘要示例：

   ```
   验收：已 export_docx → exports/理想信念.docx；绝对路径：...；主题：理想信念与专业报国
   ```

5. **不要**在 L2 对用户做终稿（不要贴全文+说「已生成」）；由 L1 验收后向用户输出路径与摘要。

## 注意

- `export_docx` 不需要审批。
- 文件目录：`workspace_user/exports/`
