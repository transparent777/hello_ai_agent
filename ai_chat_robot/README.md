# ai_chat_robot

主代码目录，按职责分层（参考 multi-agent-ecommerce-system 的组织方式）。

- **人类快速上手** → [../README.md](../README.md)
- **AI / 开发者协作** → [../CLAUDE.md](../CLAUDE.md)

## 目录一览

| 目录 | 职责 |
|------|------|
| `config/` | 路径、环境变量、LLM 配置 |
| `specialists/` | 各业务 Agent（商品/订单/分析/文件/前台） |
| `orchestrator/` | 运行循环、流式、审批恢复 |
| `tools/` | function_tool 工具实现 |
| `services/` | 审批持久化、UI 会话、Tracing |
| `guardrails/` | 安全护栏 |
| `data/` | 演示 JSON 数据 |
| `sandbox/` | Docker 沙箱子系统 |
| `mcp_integration/` / `mcp_servers/` | MCP |

## 一键启动

```bash
pip install -r requirements.txt
python scripts/generate_catalog.py
python sandbox/sync_workspace.py
streamlit run web_app.py
```

（需先在项目根 `../.env` 配置 `DEEPSEEK_API_KEY`）
