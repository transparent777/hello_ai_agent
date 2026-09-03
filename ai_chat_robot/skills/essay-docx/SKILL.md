---
name: essay-docx
description: 长文/思政类作文导出 Word 的标准流程
---

# 作文导出 Word 流程

1. 用 `read_skill('writing-style')` 确认文风（可选）。
2. 在脑中完成全文后，**必须**调用 `export_docx`，不要只在对话里粘贴全文。
3. 参数：
   - `relative_path`：如 `exports/理想信念与专业报国.docx`
   - `title`：作文标题（纯文本）
   - `body`：**纯文本**，按行分段；**禁止** `**`、 `#`、`>` 等 Markdown
4. 工具返回后，把**相对路径 + 本机绝对路径**告诉用户。
5. 对话里只给 2～3 句摘要，不要把整篇作文再贴一遍（除非用户要求预览）。

## 注意

- `export_docx` **不需要审批**，调用后应立刻在磁盘生成文件。
- 文件在 `workspace_user/` 下，例如 `ai_chat_robot/workspace_user/exports/xxx.docx`。
- 不要输出「转接失败」「让我再试」等内部过程话术。
