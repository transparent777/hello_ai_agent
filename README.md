# AI Agent 学习仓库

本仓库的主项目是 **`ai_chat_robot`**：基于 [OpenAI Agents SDK](https://github.com/openai/openai-agents-python) 的电商多智能体 Demo，覆盖工具调用、人工审批、Docker 沙箱、护栏、MCP 与 Tracing。

本地另有若干**学习/实验目录**（已加入 `.gitignore`，不会提交到 Git）：

| 目录/文件 | 用途 |
|-----------|------|
| `openai_start/` | SDK 入门练习 |
| `prompt_develop/` | Prompt 与原型实验 |
| `Building Systems/` | 系统工程小实验 |
| `learn.md` | 个人学习笔记 |

学习计划可参考仓库内的 `CLAUDE.md`（Cursor 工作区规范，可入库）。

---

## 快速开始

### 1. 环境

- Python 3.10+
- [DeepSeek API Key](https://platform.deepseek.com/api_keys)
- 数据分析沙箱需 [Docker Desktop](https://www.docker.com/products/docker-desktop/)

### 2. 安装

```bash
cd ai_chat_robot
pip install -r requirements.txt
```

### 3. 配置密钥

在项目根目录创建 `.env`：

```env
DEEPSEEK_API_KEY=你的密钥

# 可选：Web 访问保护
WEB_APP_API_KEY=自定义密钥
```

完整可选项见 `ai_chat_robot/.env.sandbox.example`。

### 4. 演示数据

```bash
cd ai_chat_robot
python scripts/generate_catalog.py
python sandbox/sync_workspace.py
```

### 5. 启动 Web（推荐）

```bash
cd ai_chat_robot
streamlit run web_app.py
```

浏览器打开 http://localhost:8501 ，侧边栏可新建对话、切换模型（Flash / Pro）。

### 6. 终端模式

```bash
cd ai_chat_robot
python robot.py
```

---

## 能做什么

| 场景 | 说明 |
|------|------|
| 商品咨询 | 「有没有适合办公的键盘？」→ 商品专员查目录 |
| 订单物流 | 「查订单 10001」→ 订单专员查 JSON 订单 |
| 退款审批 | 「订单 10001 申请退款」→ 暂停，Web 上批准/拒绝后继续 |
| 数据分析 | 「分析订单 / 生成报表」→ Docker 沙箱内跑 Python 脚本 |
| 安全防护 | 输入护栏拦截注入/离题；工具参数校验；输出防泄露 |

---

## 架构一览

```
用户
  ↓
customer_service_router（前台分诊）
  ├─ product_specialist   商品 · Flash · MCP/本地工具
  ├─ order_specialist       订单 · Pro · 退款需人工审批
  └─ analytics_specialist   分析 · Pro · Docker 沙箱
```

**模型分层**

| 层级 | 配置 | 作用 |
|------|------|------|
| Agent 级 | `Agent(model=...)` | 各专员固定 Flash / Pro |
| Run 级 | Web 侧边栏 / `RUN_DEFAULT_MODEL` | 前台分诊默认模型 |
| 进程级 | `DEEPSEEK_DEFAULT_MODEL` | 全局兜底 |

---

## 仓库结构（入库部分）

```
ai agent/
├── README.md                 # 本文件
├── CLAUDE.md                 # Agent 学习路线（工作区规范）
├── .env                      # 密钥（不入库，自行创建）
└── ai_chat_robot/            # ★ 主项目
    ├── web_app.py            # Streamlit 聊天界面
    ├── robot.py              # Agent 定义与终端入口
    ├── ecommerce_tools.py    # 商品/订单/退款工具
    ├── guardrails.py         # 输入/输出/工具护栏
    ├── approval_store.py     # 审批 RunState 持久化
    ├── tracing_setup.py      # Tracing 与 Eval 样本
    ├── mcp_integration/      # MCP 配置与生命周期
    ├── mcp_servers/          # 本地 stdio MCP 服务
    ├── sandbox/              # Docker 沙箱、脚本、Skills
    ├── scripts/              # 数据生成、E2E、Eval
    ├── eval/dataset.json     # 评估用例
    └── requirements.txt
```

---

## 常用命令

```bash
# 沙箱 E2E（需 Docker）
python scripts/run_sandbox_e2e.py

# Agent 批量评估
python scripts/run_agent_eval.py

# 本机验证沙箱脚本
python sandbox/scripts/analyze_orders.py
python sandbox/scripts/generate_report.py
```

---

## 环境变量速查

| 变量 | 默认 | 说明 |
|------|------|------|
| `DEEPSEEK_API_KEY` | — | **必填** |
| `WEB_APP_API_KEY` | 空 | 设置后 Web 需登录 |
| `GUARDRAILS_ENABLED` | `true` | 输入/输出护栏 |
| `APPROVAL_PERSIST_ENABLED` | `true` | 审批状态刷新可恢复 |
| `SANDBOX_PERSIST_SESSION` | `true` | 同会话内沙箱 resume |
| `MCP_LOCAL_ENABLED` | `true` | 本地 MCP 提供商品工具 |
| `TRACING_ENABLED` | `true` | 写入 `logs/agent_traces.jsonl` |

沙箱、MCP、Tracing 的完整列表见 `ai_chat_robot/.env.sandbox.example`。

---

## MCP 与 Tracing（简要）

**MCP（Model Context Protocol）**  
工具的标准化接入方式。本地 MCP 在独立进程暴露 `search_products` 等工具，支持白名单与审批；对用户聊天体验与直接 `function_tool` 相近，主要价值在架构隔离与可复用。

**Tracing**  
记录每次 Agent 运行的内部步骤（分诊、handoff、工具调用），输出到 `ai_chat_robot/logs/`，用于**调试**和**评估**，不影响聊天回复内容。

---

## 常见问题

**Web 打不开 / 代码改了没生效**  
重启 Streamlit：`streamlit run web_app.py`。

**数据分析无响应**  
确认 Docker Desktop 已启动，`docker version` 正常。

**未找到商品/订单**  
执行 `python scripts/generate_catalog.py`。

**退款没有审批按钮**  
需走订单专员；话术示例：「订单 10001 申请退款，商品有瑕疵」。

**前台报错 `Tool get_order_status not found`**  
前台不分流直接查单；新建会话或清空对话后重试。

---

## 参考

- [OpenAI Agents SDK](https://github.com/openai/openai-agents-python)
- [Sandbox Agents](https://openai.github.io/openai-agents-python/sandbox_agents/)
- [DeepSeek API](https://api-docs.deepseek.com/)
- 模块内技术细节：`ai_chat_robot/README.md`
