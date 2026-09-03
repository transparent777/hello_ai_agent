# 文件与数据处理 Agent

基于 [OpenAI Agents SDK](https://github.com/openai/openai-agents-python) + DeepSeek 的多智能体 Demo：**阅读总结文件**、**写入工作区**、**Docker 沙箱统计分析/报表**。

**5 分钟跑起来 → 打开 Web → 发一条消息。**


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



### ④ 启动 Web

```bash
streamlit run web_app.py
```

浏览器打开 **[http://localhost:8501](http://localhost:8501)**（若端口占用可改用 `8502`）。

> 改代码后需**重启 Streamlit** 才能生效。

---




侧边栏：**＋ 新对话**、切换历史、选 Flash/Pro 模型。运维细节在「高级设置」里。

---



## 终端模式（可选）

```bash
python robot.py
```

输入 `q` 退出。写入文件在终端里用 `y/n` 确认审批。

---



## 项目结构

```
ai agent/
├── README.md              ← 你正在看的（人类快速上手）
├── CLAUDE.md              ← 给 AI / 开发者看的项目地图
├── .env                   ← 密钥（自行创建，不入库）
└── ai_chat_robot/         ← ★ 主代码
    ├── web_app.py         ← Streamlit 界面入口
    ├── robot.py           ← 终端模式入口
    │
    ├── config/            ← 配置与路径
    ├── specialists/       ← 文档专员 + 数据专员 + 前台分流
    ├── orchestrator/      ← 流式、审批恢复、MCP 生命周期
    ├── tools/file.py      ← 工作区文件操作
    ├── services/          ← 审批、UI 会话、Tracing
    ├── guardrails/        ← 输入/输出/工具护栏
    ├── data/              ← 沙箱示例 JSON（可选）
    ├── workspace_user/    ← 用户可读写工作区
    └── sandbox/           ← Docker 沙箱与分析脚本
```

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
    ├→ document_specialist   阅读/总结/写入 · Pro · workspace_user（写入要审批）
    └→ data_specialist       统计/报表 · Pro · Docker 沙箱
```





更多环境变量见 `ai_chat_robot/.env.sandbox.example`。

---



## 延伸阅读

- 模块技术说明：`ai_chat_robot/README.md`
- AI 协作上下文：`CLAUDE.md`
- [OpenAI Agents SDK 文档](https://openai.github.io/openai-agents-python/)
- [DeepSeek API](https://api-docs.deepseek.com/)

