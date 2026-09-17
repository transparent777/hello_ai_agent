# 文件与数据处理 Agent

基于 [OpenAI Agents SDK](https://github.com/openai/openai-agents-python) + DeepSeek 的多智能体 Demo：**阅读总结文件**、**写入工作区**、**Docker 沙箱统计分析/报表**；可选电商演示数据与本地 MCP 工具。

**5 分钟跑起来 → 进入 `ai_chat_robot/` → 打开 Web → 发一条消息。**

---

## 前置条件

| 项目 | 必需？ | 说明 |
|------|--------|------|
| Python 3.10+ | ✅ | |
| [DeepSeek API Key](https://platform.deepseek.com/api_keys) | ✅ | 写入 `ai_chat_robot/.env` |
| [Docker Desktop](https://www.docker.com/products/docker-desktop/) | 数据分析需要 | 仅读文件/总结不需要 |

---

## 快速开始

### ① 克隆并进入主代码目录

```bash
git clone https://github.com/transparent777/hello_ai_agent.git
cd hello_ai_agent/ai_chat_robot
pip install -r requirements.txt
```

### ② 配置密钥

在 `ai_chat_robot/` 目录创建 `.env`：

```env
DEEPSEEK_API_KEY=sk-你的密钥

# 可选：Web 登录密码（不设则免登录）
WEB_APP_API_KEY=随便设一个字符串
```

### ③ 初始化工作区与演示数据（可选）

```bash
python scripts/init_workspace.py
python scripts/generate_catalog.py   # 电商/订单示例 JSON，可选
python sandbox/sync_workspace.py     # 数据分析前执行（需 Docker）
```

### ④ 启动 Web

```bash
streamlit run web_app.py
```

浏览器打开 **[http://localhost:8501](http://localhost:8501)**（若端口占用可改用 `8502`）。

> 改代码后需**重启 Streamlit** 才能生效。

---

## 试一试

在聊天框输入：

| 你说 | 会发生什么 |
|------|------------|
| 列出工作区里有哪些文件 | 转文档专员，浏览 `workspace_user/` |
| 阅读并总结 demo 下的文本 | 转文档专员，`read_file` 后中文摘要 |
| 把要点写入 notes/summary.md | 触发**人工审批**后写入工作区 |
| 有没有适合办公的键盘？ | 转文档/工具链，搜索 `data/` 商品目录（需 `generate_catalog.py`） |
| 查一下订单 10001 物流 | 查询 `data/orders.json`（演示数据） |
| 分析一下 data/orders.json | 转数据专员，Docker 沙箱跑脚本 |
| 生成一份销售分析报表 | 沙箱执行 `generate_report.py` |
| 帮我做数学题 | 被**输入护栏**拦截 |

侧边栏：**＋ 新对话**、切换历史、选 Flash/Pro 模型。运维细节在「高级设置」里。

---

## 终端模式（可选）

```bash
cd ai_chat_robot
python robot.py
```

输入 `q` 退出。写入文件在终端里用 `y/n` 确认审批。

清空全部历史会话：

```bash
python scripts/reset_sessions.py
```

---

## 项目结构

```
hello_ai_agent/
├── README.md              ← 你正在看的（人类快速上手）
├── CLAUDE.md              ← 给 AI / 开发者看的项目地图
└── ai_chat_robot/         ← ★ 主代码
    ├── web_app.py         ← Streamlit 界面入口
    ├── robot.py           ← 终端模式入口
    ├── ARCHITECTURE.md    ← 模块边界与运行链路
    ├── config/            ← 配置与路径
    ├── specialists/       ← 路由 + 文档/写作/数据专员
    ├── orchestrator/      ← 流式、审批恢复、MCP 生命周期
    ├── tools/             ← 文件、电商演示、导出、Skill
    ├── services/          ← 审批、UI 会话、Tracing
    ├── guardrails/        ← 输入/输出/工具护栏
    ├── data/              ← 沙箱示例 JSON（可选）
    ├── workspace_user/    ← 用户可读写工作区
    └── sandbox/           ← Docker 沙箱与分析脚本
```

| 路径 | 是否入库 | 说明 |
|------|----------|------|
| `ai_chat_robot/` | ✅ | 文件与数据 Agent 主项目 |
| `README.md`、`CLAUDE.md` | ✅ | 上手与协作文档 |
| `openai_start/` 等 | ❌ | 本地学习目录，已 `.gitignore` |

---

## 常用命令

在 `ai_chat_robot/` 目录下执行：

```bash
python scripts/init_workspace.py
python scripts/run_sandbox_e2e.py      # 需 Docker
python scripts/run_agent_eval.py
python sandbox/scripts/analyze_orders.py
```

---

## 架构（一图流）

```
用户消息
    ↓
workspace_router（前台，只分流）
    ├→ document_specialist   阅读/总结/写入 · workspace_user（写入要审批）
    ├→ writer_specialist     写作与导出
    └→ data_specialist       统计/报表 · Docker 沙箱
```

### 工作区与数据

- 默认：`ai_chat_robot/workspace_user/`（可用 `FILE_AGENT_WORKSPACE` 改路径）
- 工具：`list_files`、`read_file`、`write_file`（写入需人工审批）
- 只读示例数据：对话中用 `data/` 前缀访问 `data/*.json`
- 关闭文件能力：`FILE_AGENT_ENABLED=false`

---

## 常见问题

| 现象 | 处理 |
|------|------|
| 页面报错 / 改了代码没变化 | 停掉旧进程，重新 `streamlit run web_app.py` |
| 数据分析没反应 | 启动 Docker Desktop，`docker version` 无报错 |
| 沙箱无数据 | `python scripts/generate_catalog.py` 后 `python sandbox/sync_workspace.py` |
| 找不到商品/订单 | 先运行 `python scripts/generate_catalog.py` |
| 没有审批按钮 | 要说「写入文件」「保存到 notes/」或「申请退款」类话术 |
| 登录页要密钥 | 填 `.env` 里的 `WEB_APP_API_KEY` |

更多环境变量见 `ai_chat_robot/.env.sandbox.example`。

---

## 延伸阅读

- 模块技术说明：`ai_chat_robot/README.md`
- 架构地图：`ai_chat_robot/ARCHITECTURE.md`
- AI 协作上下文：`CLAUDE.md`
- [OpenAI Agents SDK 文档](https://openai.github.io/openai-agents-python/)
- [DeepSeek API](https://api-docs.deepseek.com/)
