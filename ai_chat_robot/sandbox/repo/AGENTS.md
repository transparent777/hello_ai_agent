# 沙箱内 Agent 约定

## 启动时请先阅读

1. `repo/task.md` — 任务规格与标准命令
2. 按需加载 Skills（订单字段、定价规则）

## 路径规则

- 一律使用**工作区相对路径**，例如 `data/orders.json`、`output/report.md`。
- 不要使用 Windows 路径或 `C:\` 形式。

## 读写边界

| 可读 | 可写 |
|------|------|
| `repo/`、`data/`、`scripts/`、`.agents/`、`memories/`（若有） | 仅 `output/` |

## 与宿主机的关系

- 沙箱结束后，`output/` 中文件可能复制到项目 `reports/` 目录归档。
- 产物移出沙箱前会经过审查，请勿在输出中写入密钥或凭证。
