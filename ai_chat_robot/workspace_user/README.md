# 文件 Agent 工作区

Agent 只能在此目录内 **列出 / 读取 / 写入** 文件（路径均相对于本目录）。

示例：把 `demo/hello.txt` 交给 Agent 处理，或在聊天中说：

> 列出工作区文件  
> 读取 demo/hello.txt  
> 在 notes 目录创建 summary.md，内容是今天待办

写入操作会触发 **人工审批**（与退款审批相同流程）。
