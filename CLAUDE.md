# CLAUDE.md — 项目协作指南

> 给 **Cursor / Claude 等 AI 助手** 和**新加入的开发者**用。  
> 目标：读完后能改代码、跑测试、不踩坑。人类 5 分钟上手请看 [README.md](README.md)。

---

## 项目是什么

**`ai_chat_robot/`** 是一个电商客服多 Agent 系统：

- **LLM**：DeepSeek（`deepseek-v4-flash` / `deepseek-v4-pro`），经 OpenAI 兼容 API
- **框架**：[OpenAI Agents SDK](https://github.com/openai/openai-agents-python)（`Agent`、`Runner`、`handoff`、`function_tool`）
- **界面**：Streamlit（`web_app.py`）+ 终端（`robot.py`）
- **数据**：本地 JSON（`data/products.json`、`data/orders.json`），非真实数据库

---

## 5 分钟本地跑通

```bash
cd ai_chat_robot
pip install -r requirements.txt
# 在项目根 ai agent/.env 写入 DEEPSEEK_API_KEY=...
python scripts/generate_catalog.py
python sandbox/sync_workspace.py
streamlit run web_app.py
```

数据分析额外需要 **Docker Desktop** 运行中。

---

## Agent 架构（必记）

| Agent | 模型 | 工具 / 能力 | 职责 |
|-------|------|-------------|------|
| `customer_service_router` | Run 级 Flash/Pro | 仅 `handoff` | 分诊，**禁止**直接调业务工具 |
| `product_specialist` | Flash | `search_products` 或 **本地 MCP** | 商品咨询 |
| `order_specialist` | Pro | `get_order_status`、`process_refund` | 订单/退款 |
| `analytics_specialist` | Pro | **SandboxAgent**（Docker） | 分析/定价/报表 |
| `file_specialist` | Pro | `list_files` / `read_file` / `write_file` | 宿主机 `workspace_user/` |

定义位置：`ai_chat_robot/specialists/`（各专员）+ `orchestrator/runner.py`（运行循环）。

```
用户 → router → handoff → specialist → tools / sandbox → 回复
```

---

## 关键文件地图

| 路径 | 职责 |
|------|------|
| `web_app.py` / `robot.py` | Streamlit / 终端入口 |
| `specialists/` | 各 Agent 定义（router、product、order、analytics、file） |
| `orchestrator/runner.py` | `handle_user_turn`、流式、审批恢复 |
| `config/llm.py` | DeepSeek 模型、`build_run_config` |
| `config/paths.py` | `DATA_DIR`、`SESSION_DB` 等路径常量 |
| `tools/ecommerce.py` | `@function_tool`：搜商品、查单、退款 |
| `tools/file.py` | 宿主机工作区文件工具；`write_file` 需审批 |
| `config/file_agent.py` | `FILE_AGENT_*` 环境变量与工作区路径 |
| `guardrails/rules.py` | 输入/输出/工具护栏 |
| `services/approval_store.py` | 审批 `RunState` 持久化 |
| `services/ui_session_store.py` | Web 聊天历史 |
| `services/tracing.py` | Trace → `logs/agent_traces.jsonl` |
| `mcp_integration/` | 本地 stdio MCP 构建与生命周期 |
| `mcp_servers/ecommerce_stdio_server.py` | MCP 版商品/订单查询 |
| `data/` | 演示商品与订单 JSON |
| `sandbox/` | Docker 沙箱、同步脚本、分析脚本 |

---

## 三条运行规则（改代码前必读）

1. **流式**：`stream_events()` 消费完毕后，才读 `final_output` / `interruptions`。
2. **审批**：`interruptions` → `to_state()` → `approve/reject` → **同一 RunState 恢复**，不要新开 user turn。
3. **失败 vs 暂停**：`MaxTurnsExceeded` = 失败；`interruptions` = 预期暂停（如退款）。

Web 审批：`web_app.py` → `apply_approval_decision()`。  
持久化：`services/approval_store.py`（刷新页面可继续批）。

---

## 子系统速查

### 护栏（`guardrails/`）

- **输入**：挂在 `customer_service_router`，阻塞式（注入/离题/外泄）
- **输出**：商品/订单专员
- **工具**：`validate_order_id`、`validate_refund_request` 在 `tools/ecommerce.py`
- 开关：`GUARDRAILS_ENABLED`

### 文件 Agent（宿主机，方案 B）

- 路径校验在 `tools/file.py` 的 `resolve_safe_path`
- 工具护栏：`validate_file_tool_path`（防 `..`、黑名单文件名）
- 写入：`write_file(needs_approval=True)`，走与退款相同的审批恢复流程
- 开关：`FILE_AGENT_ENABLED`；关闭后 router 不挂 `file_specialist`

### Docker 沙箱（`sandbox/`）

- 镜像默认 `python:3.11-slim`，`network_mode=none`
- 工作区同步：`python sandbox/sync_workspace.py`
- 脚本：`sandbox/scripts/` → 容器内 `/workspace/scripts/`
- 输出：`sandbox/workspace/output/` → 审查后复制到 `reports/`
- 会话 resume：`SANDBOX_PERSIST_SESSION` + `persist/{session_id}/`

### MCP

- **本地**（默认开）：`MCP_LOCAL_ENABLED`，商品专员走 MCP 工具，与原生 `search_products` 二选一
- **托管**（默认关）：`HostedMCPTool`，需 Responses 兼容 API
- 生命周期：`run_with_mcp_lifecycle()` 包在 `handle_user_turn` 外

### Tracing

- 调试：`logs/agent_traces.jsonl`（`TRACING_ENABLED`）
- Eval 样本：`logs/eval_samples.jsonl`（`TRACING_EVAL_ENABLED`）
- **不影响**用户可见回复

---

## 环境变量

根目录 `.env`（不入库）。常用项：

```env
DEEPSEEK_API_KEY=          # 必填
WEB_APP_API_KEY=           # 可选，Web 登录
GUARDRAILS_ENABLED=true
APPROVAL_PERSIST_ENABLED=true
SANDBOX_PERSIST_SESSION=true
MCP_LOCAL_ENABLED=true
TRACING_ENABLED=true
```

完整列表：`ai_chat_robot/.env.sandbox.example`。

`config/settings.py` 与 `config/llm.py` 会 `load_dotenv` 项目根和 `ai_chat_robot/` 下的 `.env`。

---

## 测试与验证

```bash
cd ai_chat_robot

# 沙箱冒烟（要 Docker）
python scripts/run_sandbox_e2e.py

# 护栏单元测试
python -c "from tests.test_guardrails import *; ..."

# 评估数据集
python scripts/run_agent_eval.py
```

改 `robot.py` / `web_app.py` / `sandbox/` 后，至少跑 E2E（若动沙箱）并手动测 Web 一条对话。

---

## 改代码时的约定

1. **最小改动**：不重构无关文件；匹配现有风格（中文注释、路径用 `Path`）。
2. **密钥**：只放 `.env`，不进 Manifest / 日志 / 代码。
3. **沙箱路径**：容器内一律相对路径 `data/`、`output/`、`repo/`。
4. **Session**：Web 新建/切换会话要 `clear_persisted_session` + 重置 `session_picker` widget（见 `web_app.py`）。
5. **Streamlit**：改 Python 后需重启进程；widget `key` 冲突会导致会话切回旧对话。
6. **Git 忽略**：`openai_start/`、`prompt_develop/`、`Building Systems/`、`learn.md`、`.env`、`logs/`、`persist/`、`sessions.db*`。

---

## 常见扩展任务

| 需求 | 改哪里 |
|------|--------|
| 新增业务工具 | `tools/ecommerce.py` + 挂到对应 `Agent(tools=...)` |
| 扩展文件能力 | `tools/file.py` + `specialists/file.py`；注意路径沙箱 |
| 新增专员 | `specialists/` 新建 Agent，加入 `router.py` 的 handoffs |
| 新分析脚本 | `sandbox/scripts/` + `sync_workspace.py` + `repo/task.md` |
| 收紧安全 | `guardrails/rules.py` 或 `sandbox/security.py` |
| 新审批操作 | `@function_tool(needs_approval=True)` + Web 已有审批流 |
| 调模型 | `config/llm.py` 里 `DEEPSEEK_FLASH` / `DEEPSEEK_PRO` 或 Web 侧边栏 Run 级模型 |

---

## 不要做的事

- 不要让 `customer_service_router` 直接调用 `get_order_status` / `search_products`
- 不要在沙箱里开外网（默认 `network_mode=none`）
- 不要把 `SANDBOX_ALLOW_LOCAL_FALLBACK=true` 当生产默认（绕过 Docker）
- 不要提交 `.env`、`sessions.db`、`logs/`、`sandbox/persist/`
- 不要未经用户要求提交 git

---

## 仓库外（本地实验，已 gitignore）

| 路径 | 说明 |
|------|------|
| `openai_start/` | SDK 入门练习 |
| `prompt_develop/` | Prompt 实验 |
| `Building Systems/` | 系统工程练习 |
| `learn.md` | 个人学习笔记 |

主项目只看 `ai_chat_robot/` 即可。

---

## 排错清单

| 错误/现象 | 方向 |
|-----------|------|
| `ImportError: SANDBOX_MEMORY_ENABLED` | 重启 Streamlit，旧进程缓存了模块 |
| `Tool get_order_status not found in router` | Session 历史或 router 未 handoff；新建会话 |
| 新建会话仍显示旧对话 | `session_picker` widget 状态；见 `_load_session_into_ui` |
| 数据分析占位回复 | Docker 未启动或 `SANDBOX_REQUIRE_DOCKER=true` |
| 审批刷新丢失 | 检查 `APPROVAL_PERSIST_ENABLED` 与 `approval_pending.json` |

---

## 参考链接

- [Agents SDK](https://github.com/openai/openai-agents-python)
- [Sandbox Agents](https://openai.github.io/openai-agents-python/sandbox_agents/)
- [DeepSeek API](https://api-docs.deepseek.com/)
