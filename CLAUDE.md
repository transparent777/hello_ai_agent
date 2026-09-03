# CLAUDE.md — 项目协作指南

> 给 **Cursor / Claude 等 AI 助手** 和**新加入的开发者**用。  
> 目标：读完后能改代码、跑测试、不踩坑。人类 5 分钟上手请看 [README.md](README.md)。

---

## 项目是什么

**`ai_chat_robot/`** 是一个**文件与数据处理**多 Agent 系统：

- **LLM**：DeepSeek（`deepseek-v4-flash` / `deepseek-v4-pro`），经 OpenAI 兼容 API
- **框架**：[OpenAI Agents SDK](https://github.com/openai/openai-agents-python)（`Agent`、`Runner`、`handoff`、`function_tool`）
- **界面**：Streamlit（`web_app.py`）+ 终端（`robot.py`）
- **数据**：`workspace_user/` 用户工作区 + `data/` 沙箱示例 JSON

---

## 5 分钟本地跑通

```bash
cd ai_chat_robot
pip install -r requirements.txt
# 在项目根 ai agent/.env 写入 DEEPSEEK_API_KEY=...
python scripts/init_workspace.py
python scripts/generate_catalog.py   # 可选，沙箱示例数据
python sandbox/sync_workspace.py   # 数据分析前
streamlit run web_app.py
```

数据分析额外需要 **Docker Desktop** 运行中。

---

## Agent 架构（必记）

| Agent | 模型 | 工具 / 能力 | 职责 |
|-------|------|-------------|------|
| `workspace_router` | Flash | 仅 `handoff` | 分诊，**禁止**直接调业务工具 |
| `document_specialist` | Pro | `list_files` / `read_file` / `write_file` | 阅读、总结、写入 `workspace_user/` |
| `data_specialist` | Pro | **SandboxAgent**（Docker）或本地回退工具 | 统计分析、报表 |

定义位置：`ai_chat_robot/specialists/` + `orchestrator/runner.py`。

```
用户 → workspace_router → handoff → specialist → tools / sandbox → 回复
```

兼容别名：`customer_service_router`、`file_specialist`、`analytics_specialist`（旧会话恢复）。

---

## 关键文件地图

| 路径 | 职责 |
|------|------|
| `web_app.py` / `robot.py` | Streamlit / 终端入口 |
| `specialists/router.py` | `workspace_router` 分流 |
| `specialists/document.py` | 文档专员 |
| `specialists/data.py` | 数据专员（沙箱） |
| `orchestrator/runner.py` | `handle_user_turn`、流式、审批恢复 |
| `tools/file.py` | 工作区文件工具；`write_file` 需审批 |
| `config/file_agent.py` | `FILE_AGENT_*` |
| `guardrails/rules.py` | 输入/输出/工具护栏 |
| `services/approval_store.py` | 审批持久化 |
| `sandbox/` | Docker 沙箱与分析脚本 |
| `tools/ecommerce.py` | 遗留示例数据工具（MCP 可选，默认未启用） |

---

## 三条运行规则（改代码前必读）

1. **流式**：`stream_events()` 消费完毕后，才读 `final_output` / `interruptions`。
2. **审批**：`interruptions` → `to_state()` → `approve/reject` → **同一 RunState 恢复**，不要新开 user turn。
3. **失败 vs 暂停**：`MaxTurnsExceeded` = 失败；`interruptions` = 预期暂停（如写入文件）。

---

## 子系统速查

### 护栏（`guardrails/`）

- **输入**：挂在 `workspace_router`（注入/离题/外泄）
- **输出**：文档专员
- **工具**：`validate_file_tool_path` 在 `tools/file.py`
- 开关：`GUARDRAILS_ENABLED`

### 工作区（宿主机）

- 路径校验：`tools/file.resolve_safe_path`
- 写入：`write_file(needs_approval=True)`
- 开关：`FILE_AGENT_ENABLED`；关闭后 router 不挂 `document_specialist`

### Docker 沙箱（`sandbox/`）

- 同步：`python sandbox/sync_workspace.py`
- 任务说明：`sandbox/repo/task.md`

### MCP

- **本地**（默认关）：`MCP_LOCAL_ENABLED=false`
- 生命周期：`run_with_mcp_lifecycle()` 包在 `handle_user_turn` 外

---

## 环境变量

```env
DEEPSEEK_API_KEY=
FILE_AGENT_SESSION_ID=file_agent_session
GUARDRAILS_ENABLED=true
MCP_LOCAL_ENABLED=false
FILE_AGENT_ENABLED=true
```

完整列表：`ai_chat_robot/.env.sandbox.example`。

---

## 常见扩展任务

| 需求 | 改哪里 |
|------|--------|
| 扩展文件能力 | `tools/file.py` + `specialists/document.py` |
| 新分析脚本 | `sandbox/scripts/` + `sync_workspace.py` + `repo/task.md` |
| 新增专员 | `specialists/` 新建 Agent，加入 `router.py` handoffs |
| 新审批操作 | `@function_tool(needs_approval=True)` |

---

## 不要做的事

- 不要让 `workspace_router` 直接调用 `read_file` / `write_file`
- 不要在沙箱里开外网（默认 `network_mode=none`）
- 不要提交 `.env`、`sessions.db`、`logs/`

---

## 参考链接

- [Agents SDK](https://github.com/openai/openai-agents-python)
- [Sandbox Agents](https://openai.github.io/openai-agents-python/sandbox_agents/)
- [DeepSeek API](https://api-docs.deepseek.com/)
