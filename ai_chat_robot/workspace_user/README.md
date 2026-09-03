# workspace_user

Agent 可读写的工作区根目录（宿主机路径，默认 `ai_chat_robot/workspace_user/`）。

## 示例用法

在聊天中说：

> 列出工作区文件  
> 阅读 demo/hello.txt 并总结  
> 把要点保存到 notes/summary.md  

`notes/`、`exports/` 等子目录会在写入时自动创建。

`data/` 下的 JSON 为沙箱示例数据，只读；在对话中用 `data/orders.json` 等形式访问。
