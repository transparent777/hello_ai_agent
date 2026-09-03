# ai_chat_robot

架构地图与模块边界见 [ARCHITECTURE.md](ARCHITECTURE.md)。新功能请先按该文档确定归属，再修改实现。

主代码目录：文件与数据处理多 Agent 系统。

## 目录

| 路径 | 说明 |
|------|------|
| `web_app.py` / `robot.py` | Streamlit / 终端入口 |
| `config/` | 路径、环境变量、LLM、文件工作区配置 |
| `specialists/` | `workspace_router`、`document_specialist`、`data_specialist` |
| `orchestrator/` | 流式运行、审批恢复 |
| `tools/file.py` | 工作区 `list_files` / `read_file` / `write_file` |
| `services/` | 审批、UI 会话、Tracing |
| `guardrails/` | 输入/输出/工具护栏 |
| `workspace_user/` | 用户可读写目录 |
| `data/` | 沙箱示例 JSON（只读，对话中用 `data/` 前缀） |
| `sandbox/` | Docker 分析脚本与同步 |

## 启动

```bash
pip install -r requirements.txt
python scripts/init_workspace.py
streamlit run web_app.py
```

数据分析：`python scripts/generate_catalog.py && python sandbox/sync_workspace.py`（需 Docker）。
