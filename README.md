# 电商智能客服 Agent

基于 [OpenAI Agents SDK](https://github.com/openai/openai-agents-python) + DeepSeek 的多智能体 Demo：商品咨询、订单物流、退款审批、Docker 沙箱数据分析。

**5 分钟跑起来 → 打开 Web → 发一条消息。**

---

## 前置条件

| 项目 | 必需？ | 说明 |
|------|--------|------|
| Python 3.10+ | ✅ | |
| [DeepSeek API Key](https://platform.deepseek.com/api_keys) | ✅ | 写入 `.env` |
| [Docker Desktop](https://www.docker.com/products/docker-desktop/) | 数据分析需要 | 查商品/订单不需要 |

---

## 快速开始

### ① 克隆并进入项目

```bash
cd "ai agent/ai_chat_robot"
pip install -r requirements.txt
```

### ② 配置密钥

在**项目根目录**（`ai agent/`）创建 `.env`：

```env
DEEPSEEK_API_KEY=sk-你的密钥

# 可选：Web 登录密码（不设则免登录）
WEB_APP_API_KEY=随便设一个字符串
```

### ③ 生成演示数据

```bash
python scripts/generate_catalog.py
python sandbox/sync_workspace.py
```

### ④ 启动 Web

```bash
streamlit run web_app.py
```

浏览器打开 **http://localhost:8501**（若端口占用可改用 `8502`）。

> 改代码后需**重启 Streamlit** 才能生效。

---

## 试一试

在聊天框输入：

| 你说 | 会发生什么 |
|------|------------|
| 有没有适合办公的键盘？ | 转商品专员，搜索商品目录 |
| 查一下订单 10001 物流 | 转订单专员，查 JSON 订单 |
| 订单 10001 申请退款，商品有瑕疵 | 触发**人工审批**，点批准/拒绝后继续 |
| 分析一下订单数据 | 转数据分析专员，Docker 沙箱跑脚本 |
| 列出工作区文件，读取 demo/hello.txt | 转文件专员，读写 `workspace_user/` |
| 帮我做数学题 | 被**输入护栏**拦截 |

侧边栏：**＋ 新对话**、切换历史、选 Flash/Pro 模型。运维细节在「高级设置」里。

---

## 终端模式（可选）

```bash
python robot.py
```

输入 `q` 退出。退款审批在终端里用 `y/n` 确认。

---

## 项目结构

```
ai agent/
├── README.md              ← 你正在看的（人类快速上手）
├── CLAUDE.md              ← 给 AI / 开发者看的项目地图
├── .env                   ← 密钥（自行创建，不入库）
└── ai_chat_robot/         ← ★ 主代码
    ├── web_app.py         ← Streamlit 界面
    ├── robot.py           ← Agent 定义 + 运行逻辑
    ├── ecommerce_tools.py ← 商品/订单/退款工具
    ├── file_tools.py      ← 工作区文件 list/read/write
    ├── workspace_user/    ← 文件 Agent 可操作目录
    ├── guardrails.py      ← 安全护栏
    ├── sandbox/           ← Docker 沙箱与分析脚本
    └── scripts/           ← 数据生成、测试脚本
```

以下目录为**本地学习实验**，已在 `.gitignore` 中，不会提交：`openai_start/`、`prompt_develop/`、`Building Systems/`、`learn.md`。

---

## 常用命令

在 `ai_chat_robot/` 目录下执行：

```bash
# 验证沙箱（需 Docker）
python scripts/run_sandbox_e2e.py

# 批量评估 Agent
python scripts/run_agent_eval.py

# 本机单独跑分析脚本
python sandbox/scripts/analyze_orders.py
```

---

## 架构（一图流）

```
用户消息
    ↓
customer_service_router（前台，只分流不查单）
    ├→ product_specialist      商品 · Flash
    ├→ order_specialist        订单 · Pro · 退款要审批
    ├→ analytics_specialist    分析 · Pro · Docker 沙箱
    └→ file_specialist         文件 · Pro · workspace_user（写入要审批）
```

### 文件 Agent（方案 B）

- 工作区默认：`ai_chat_robot/workspace_user/`（可用 `FILE_AGENT_WORKSPACE` 改路径）
- 工具：`list_files`、`read_file`、`write_file`（写入需人工审批）
- 可把文件放进 `workspace_user/`，在聊天里让 Agent 读取或生成内容
- 关闭：`FILE_AGENT_ENABLED=false`

---

## 常见问题

| 现象 | 处理 |
|------|------|
| 页面报错 / 改了代码没变化 | 停掉旧进程，重新 `streamlit run web_app.py` |
| 数据分析没反应 | 启动 Docker Desktop，`docker version` 无报错 |
| 找不到商品/订单 | `python scripts/generate_catalog.py` |
| 没有审批按钮 | 要说「申请退款」或「写入文件」类话术 |
| 登录页要密钥 | 填 `.env` 里的 `WEB_APP_API_KEY` |

更多环境变量见 `ai_chat_robot/.env.sandbox.example`。

---

## 延伸阅读

- 模块技术说明：`ai_chat_robot/README.md`
- AI 协作上下文：`CLAUDE.md`
- [OpenAI Agents SDK 文档](https://openai.github.io/openai-agents-python/)
- [DeepSeek API](https://api-docs.deepseek.com/)
