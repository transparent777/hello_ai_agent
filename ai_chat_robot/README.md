# ai_chat_robot

电商多智能体 Demo 的实现目录。**安装、启动与总览请先看仓库根目录 [README.md](../README.md)。**

---

## 核心文件

| 文件 | 作用 |
|------|------|
| `web_app.py` | Streamlit Web 界面（日常使用） |
| `robot.py` | Agent 定义、流式运行、审批恢复、终端入口 |
| `ecommerce_tools.py` | 商品搜索、订单查询、退款（`needs_approval`） |
| `guardrails.py` | 输入/输出/工具护栏 |
| `approval_store.py` | 审批 `RunState` 磁盘持久化 |
| `tracing_setup.py` | Trace 调试日志 + Eval 样本采集 |
| `ui_session_store.py` | Web 聊天历史（与 Agent Session 分离） |

---

## 子系统

### Sandbox（`sandbox/`）

Docker 隔离环境，供 `analytics_specialist` 跑分析脚本。

```
/workspace/
├── repo/       只读：task.md、AGENTS.md
├── data/       只读：orders.json、products.json
├── scripts/    只读：analyze_orders.py、pricing.py、generate_report.py
├── output/     可写：分析结果、report.md
└── memories/   只读（若有）：跨运行 memory_summary.md
```

- 同步工作区：`python sandbox/sync_workspace.py`
- 产物落盘：`reports/`（经 `artifact_review` 审查）
- 会话持久化：`sandbox/persist/{session_id}/`（已在根 `.gitignore`）

### MCP（`mcp_integration/`、`mcp_servers/`）

- **本地 MCP**（默认）：`ecommerce_stdio_server.py`，工具白名单 + 可选审批
- **托管 MCP**（默认关）：需 `MCP_HOSTED_SERVER_URL`，适合 Responses 兼容 API

### 护栏与审批

1. 链首 `customer_service_router`：输入护栏（注入/离题/外泄）
2. `process_refund`：`needs_approval=True`，Web 批准后继续**同一 RunState**
3. 工具旁参数校验：`validate_order_id`、`validate_refund_request`
4. 审批持久化：`persist/.../approval_pending.json`，刷新页面可继续审批

---

## 脚本

| 命令 | 说明 |
|------|------|
| `python scripts/generate_catalog.py` | 生成 `data/*.json` |
| `python sandbox/sync_workspace.py` | 同步到沙箱 workspace |
| `python scripts/run_sandbox_e2e.py` | 沙箱冒烟测试 |
| `python scripts/run_agent_eval.py` | 读取 `eval/dataset.json` 批量评估 |

---

## 配置模板

复制并根据需要修改：

- 项目根 `.env` — API 密钥与常用开关
- `.env.sandbox.example` — 沙箱 / MCP / Tracing 完整选项

---

## 运行生命周期（开发必读）

1. 流式 `stream_events()` **结束后**再读 `final_output` / `interruptions`
2. 审批暂停用 `result.to_state()` → `approve/reject` → 恢复，**不要**新开 user turn
3. `interruptions` = 预期暂停；`MaxTurnsExceeded` = 运行失败
