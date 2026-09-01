# 电商智能客服 Agent

基于 [OpenAI Agents SDK](https://github.com/openai/openai-agents-python) 的多智能体电商客服示例：商品咨询、订单查询、退款审批，支持 Web 聊天界面与终端两种使用方式。

---

## 功能概览

| 能力 | 说明 |
|------|------|
| 多 Agent 分流 | 前台分诊 → 商品顾问 / 订单客服 |
| 工具调用 | 搜索商品、查订单、发起退款（需审批） |
| 模型分层 | Flash（快/便宜）与 Pro（强推理），Agent 级 + Run 级配置 |
| Session 半托管 | `SQLiteSession` 持久化 Agent 对话上下文 |
| Web 界面 | Streamlit 流式聊天、历史会话、模型切换 |
| 演示数据 | 本地 JSON 商品/订单，可脚本生成 |

---

## 目录结构

```
ai_chat_robot/
├── robot.py              # Agent 定义、模型配置、运行生命周期（终端）
├── web_app.py            # Streamlit Web 界面（推荐日常使用）
├── ecommerce_tools.py    # 商品/订单/退款工具（读 data/）
├── ui_session_store.py   # Web 可展示聊天历史的持久化
├── scripts/
│   └── generate_catalog.py   # 生成演示商品与订单
├── data/
│   ├── products.json
│   └── orders.json
├── sessions.db           # Session + UI 历史（运行后自动生成）
└── requirements.txt
```

---

## 快速上手

### 1. 环境要求

- Python 3.10+
- DeepSeek API Key（[平台申请](https://platform.deepseek.com/api_keys)）

### 2. 安装依赖

在项目根目录或 `ai_chat_robot` 目录执行：

```bash
cd ai_chat_robot
python -m pip install -r requirements.txt
```

### 3. 配置密钥

在 **项目根目录** `ai agent/.env` 或 `ai_chat_robot/.env` 中写入：

```env
DEEPSEEK_API_KEY=你的密钥

# 可选
DEEPSEEK_DEFAULT_MODEL=deepseek-v4-flash
RUN_DEFAULT_MODEL=deepseek-v4-flash
ECOMMERCE_SESSION_ID=ecommerce_customer_session
AGENT_MAX_TURNS=12
```

### 4. 生成演示数据

```bash
python scripts/generate_catalog.py
```

会生成 `data/products.json` 与 `data/orders.json`，终端会打印示例订单号（如 `10001`）。

### 5. 启动 Web 界面（推荐）

```bash
streamlit run web_app.py
```

浏览器打开 `http://localhost:8501`。

**侧边栏：**

- **模型**：切换前台默认模型（Flash / Pro）
- **历史会话**：查看、切换过往对话
- **新建会话** / **清空当前会话记录**

**示例问题：**

- 有没有适合办公的键盘？
- 帮我查订单 10001 物流
- 帮订单 10001 申请退款，商品有瑕疵（会触发审批按钮）

### 6. 终端模式（可选）

```bash
python robot.py
```

输入 `quit` / `exit` / `q` 退出。

---

## Agent 架构

```
用户
  ↓
customer_service_router（前台，Run 默认 Flash）
  ├─ handoff → product_specialist（Flash + search_products）
  └─ handoff → order_specialist（Pro + get_order_status / process_refund）
```

### 模型配置三层

| 层级 | 配置方式 | 作用 |
|------|----------|------|
| Agent 级 | `Agent(model=...)` | 专员固定模型（商品 Flash、订单 Pro） |
| Run 级 | `RunConfig(model=...)` / Web 侧边栏 | 前台分诊默认模型 |
| 进程级 | `DEEPSEEK_DEFAULT_MODEL` | 未指定 model 时的兜底 |

---

## 运行生命周期（重要）

1. **流式输出**：必须等 `stream_events()` 消费完毕，再读 `final_output` / `interruptions`。
2. **审批暂停**：从 `RunState` 恢复，不要当作新一轮用户输入。
3. **失败 vs 暂停**：`MaxTurnsExceeded` 等为运行时失败；`interruptions` 为预期内暂停（如退款审批）。

---

## 常见问题

### `Tool get_order_status not found in agent customer_service_router`

前台没有业务工具，必须先 `handoff` 到 `order_specialist`。若 Session 历史较长，可新建会话或清空记录后重试。

### Web 上用户消息不显示 / 历史丢失

请使用当前版 `web_app.py`（两阶段提交 + `ui_session_store`）。升级前的对话不会自动迁移到 UI 历史表。

### `未找到商品/订单数据`

先运行 `python scripts/generate_catalog.py`。

---

## 下一步：Sandbox Agent（规划）

当前 Agent 在**本机进程**内调用工具（读 JSON）。若引入 **Sandbox Agent**，模型将在**隔离工作区**内操作文件、执行命令、跨多次运行保留状态。

接入前请阅读下方 **《Sandbox 接入准备清单》**，确认环境与业务边界后再开发。

---

## Sandbox 接入准备清单

> 基于 [OpenAI Agents SDK Sandbox Agents 文档](https://openai.github.io/openai-agents-python/sandbox_agents/)。  
> **注意：你在 Windows 上开发，本地沙箱需用 `DockerSandboxClient`，不能直接用 `UnixLocalSandboxClient`（仅 macOS/Linux）。**

### 一、环境与基础设施

| 序号 | 准备项 | 你需要决定/提供 |
|------|--------|-----------------|
| 1 | **Python 版本** | ≥ 3.10，与当前项目一致 |
| 2 | **沙箱后端** | Windows → Docker（`pip install "openai-agents[docker]"` + Docker Desktop）；或选用托管沙箱（Blaxel 等） |
| 3 | **Docker 资源** | 镜像、CPU/内存上限、是否允许访问外网 |
| 4 | **磁盘与路径** | 工作区根目录、挂载策略（只读 / 读写） |
| 5 | **网络策略** | 沙箱内能否访问 DeepSeek API、能否 `pip install`、能否访问内网订单系统 |

### 二、SDK 与运行配置

| 序号 | 准备项 | 你需要决定/提供 |
|------|--------|-----------------|
| 6 | **Agent 类型** | 是否改为 `SandboxAgent`（保留 `instructions` / `handoffs`，增加 `default_manifest`、`capabilities`） |
| 7 | **SandboxRunConfig** | `client`（Docker / 托管）、`manifest`、`snapshot`、`session` / `session_state` 如何注入 |
| 8 | **运行用户 `run_as`** | 沙箱内执行命令的系统用户与权限 |
| 9 | **工作目录 `cwd`** | 模型可见的默认路径（相对 workspace root） |
| 10 | **与现有 RunConfig 合并** | `model_provider`（DeepSeek）+ `sandbox=SandboxRunConfig(...)` 同时生效的方式 |

### 三、工作区内容（Manifest）

| 序号 | 准备项 | 你需要决定/提供 |
|------|--------|-----------------|
| 11 | **初始文件** | 哪些文件进沙箱：`data/products.json`、`orders.json`、业务脚本、知识库文档 |
| 12 | **Git 仓库** | 是否挂载代码仓（`GitRepo` entry）及分支/tag |
| 13 | **环境变量** | 沙箱内需要的 `DEEPSEEK_API_KEY` 等（注意安全，避免明文进镜像） |
| 14 | **目录布局** | 例如 `/workspace/data`、`/workspace/tools`、`/workspace/output` |

### 四、能力与工具边界

| 序号 | 准备项 | 你需要决定/提供 |
|------|--------|-----------------|
| 15 | **Capabilities** | 启用哪些：`filesystem`（读写补丁）、`shell`、 `skills`、`memory`、`compaction` |
| 16 | **与现有工具关系** | `ecommerce_tools.py` 保留为函数工具，还是改为沙箱内 Python 脚本 + shell 调用 |
| 17 | **Shell 白名单** | 允许哪些命令（`python`、`curl`、禁止 `rm -rf` 等） |
| 18 | **文件写权限** | 哪些路径可写、是否允许 Agent 修改订单/商品 JSON |
| 19 | **审批策略** | 退款等敏感操作：仍用 `needs_approval=True`，还是沙箱外人工复核 |

### 五、状态持久化与 Web 集成

| 序号 | 准备项 | 你需要决定/提供 |
|------|--------|-----------------|
| 20 | **Session 关系** | `SQLiteSession`（对话）与 `SandboxSessionState`（工作区快照）如何一一对应 |
| 21 | **快照策略** | 每次 run 结束是否保存 snapshot；保留多久、占用多大空间 |
| 22 | **断点恢复** | Web 刷新 / 审批暂停后：用 `RunState` 还是 `session_state` 恢复沙箱 |
| 23 | **历史展示** | 沙箱内文件变更、命令输出是否在 Web 页展示（审计日志） |

### 六、安全与合规

| 序号 | 准备项 | 你需要决定/提供 |
|------|--------|-----------------|
| 24 | **数据分级** | 真实订单/用户 PII 能否进沙箱；演示数据与生产数据隔离方案 |
| 25 | **密钥管理** | API Key 注入方式（环境变量、密钥管理服务），禁止写入沙箱内文件 |
| 26 | **资源限额** | `archive_limits`、`concurrency_limits`、单次 run 超时与 `max_turns` |
| 27 | **审计** | 谁批准退款、沙箱命令记录留存要求 |

### 七、业务与验收

| 序号 | 准备项 | 你需要决定/提供 |
|------|--------|-----------------|
| 28 | **Sandbox 要解决什么问题** | 例：在沙箱内跑数据分析脚本、批量改价模拟、生成报表文件 |
| 29 | **与现有多 Agent 分工** | 前台/专员是否仍为普通 Agent，仅某一专员进沙箱；或整体升级为 SandboxAgent |
| 30 | **验收标准** | 3～5 条可测场景（创建文件、执行命令、跨 run 恢复、审批流、失败回滚） |
| 31 | **成本预估** | Docker 资源 + DeepSeek token + 沙箱运行时长 |

### 八、你的方案（已确认）

| 决策项 | 你的选择 |
|--------|----------|
| 1. 沙箱后端 | **Docker 本地** |
| 2. 首要场景 | **分析订单 JSON、生成报表、跑定价脚本** |
| 3. 数据来源 | **继续用 `generate_catalog.py` 模拟数据** |
| 4. Shell | **见下方解释 → 建议：允许，但只允许 `python` 相关命令** |
| 5. 跨天保留工作区 | **见下方解释 → 建议：学习阶段先不要，每次新任务开新沙箱** |
| 6. Web 展示沙箱过程 | **不需要** |

#### 第 4 项「Shell」是什么意思？

**Shell = 让 Agent 在沙箱里执行命令行**，就像在终端里输入：

```bash
python scripts/pricing.py --input data/orders.json
```

| 选项 | 含义 | 适不适合你 |
|------|------|------------|
| **不允许 Shell** | Agent 只能读写文件，不能跑命令 | ❌ 你要跑定价脚本，不行 |
| **允许 Shell（推荐）** | Agent 可以执行 `python xxx.py` 来分析、出报表 | ✅ 符合你的场景 |
| **白名单** | 只允许 `python`，禁止 `curl`、`rm` 等 | ✅ 最安全，建议采用 |

**你的场景结论：需要 Shell，且建议白名单只允许 `python`（及读文件）。**

#### 第 5 项「跨天保留工作区」是什么意思？

沙箱里 Agent 可能生成文件，例如 `output/report.md`、`output/pricing_result.json`。

| 选项 | 含义 | 适不适合你 |
|------|------|------------|
| **不保留（推荐入门）** | 每次对话/任务 = 新建 Docker 沙箱，上次生成的报表不自动带上 | ✅ 简单，先这样 |
| **要保留** | 今天生成的报表，明天打开同一会话还能接着改 | 进阶再做 |

**你的场景结论：先选「不保留」；需要时再把 `output/` 复制到本机或加快照。**

---

### 九、材料准备表（按你的方案，逐项怎么准备）

> **准备状态**：做完一项可在前面打勾 `[x]`。

| # | 要准备的材料 | 是什么 | 你怎么准备（具体操作） | 你的决定 |
|---|-------------|--------|------------------------|----------|
| **A. 本机环境** |
| A1 | Docker Desktop | Windows 上跑 Linux 容器的软件 | 安装 [Docker Desktop](https://www.docker.com/products/docker-desktop/)，启动后终端执行 `docker version` 能成功 | Docker 本地 |
| A2 | Python 依赖 | SDK 的 Docker 沙箱扩展 | `pip install "openai-agents[docker]"`（在现有 requirements 上追加） | 待安装 |
| A3 | DeepSeek 密钥 | 模型 API | 项目根 `.env` 已有 `DEEPSEEK_API_KEY`，沙箱外 Runner 调用模型用 | 已有 |
| **B. 演示数据（继续脚本模拟）** |
| B1 | `data/orders.json` | 订单数据 | `python scripts/generate_catalog.py`（已有则跳过） | 脚本生成 |
| B2 | `data/products.json` | 商品数据 | 同上脚本一并生成 | 脚本生成 |
| B3 | 数据刷新规则 | 何时重新生成 | 约定：改脚本或测新场景时手动再跑一遍生成脚本 | 手动刷新 |
| **C. 沙箱内业务脚本（你要新建）** |
| C1 | `sandbox/scripts/analyze_orders.py` | 读 orders.json，输出统计（订单数、金额、状态分布） | 写一个 Python 脚本，`stdin/argv` 或读固定路径，打印 JSON 摘要 | **待创建** |
| C2 | `sandbox/scripts/pricing.py` | 定价模拟（如按品类打折、满减） | 读 `products.json`，写结果到 `output/pricing.json` | **待创建** |
| C3 | `sandbox/scripts/generate_report.py` | 汇总分析 + 定价，生成 `output/report.md` | 调用或复用 C1/C2 逻辑，输出 Markdown 报表 | **待创建** |
| C4 | 脚本自测命令 | 确保沙箱里能跑通 | 本机先测：`python sandbox/scripts/analyze_orders.py` | **待验证** |
| **D. 沙箱工作区目录（Manifest 要挂载的文件）** |
| D1 | `/workspace/data/` | 沙箱内的数据目录 | 把 `data/*.json` 复制进 Manifest（或挂载只读卷） | 从 B1/B2 复制 |
| D2 | `/workspace/scripts/` | 沙箱内的脚本目录 | 放入 C1～C3 三个 `.py` | 从 C 复制 |
| D3 | `/workspace/output/` | 报表输出目录 | 空目录即可，Agent 写入；本机可定期拷出 | 可写 |
| D4 | `sandbox/manifest.yaml` 或代码 Manifest | 告诉 SDK 沙箱启动时带哪些文件 | 开发阶段用 `Manifest(entries={...})` 列出上述路径 | **待创建** |
| **E. Docker 沙箱配置** |
| E1 | 基础镜像 | 容器里跑 Python 的环境 | 默认 SDK 镜像或 `python:3.11-slim`（开发时再定） | Docker 官方 Python 镜像 |
| E2 | `DockerSandboxClient` | 连接本机 Docker 的客户端 | 代码里 `SandboxRunConfig(client=DockerSandboxClient(...))` | 待编码 |
| E3 | CPU / 内存 | 容器资源上限 | Docker Desktop → Settings → Resources，建议 ≥ 2GB 内存 | 按本机调整 |
| E4 | 网络 | 容器能否访问外网 | 分析本地 JSON **不需要**外网；若沙箱内也要调 API 再开 | **先关闭外网**（更安全） |
| **F. Agent 与能力** |
| F1 | `SandboxAgent` 角色 | 在沙箱里干活的专员 | 新建例如 `analytics_specialist`：负责分析/报表/定价 | 待编码 |
| F2 | Capabilities | 沙箱原生能力开关 | 开启：`filesystem` + `shell`；关闭：`memory`（入门可先关） | filesystem + shell |
| F3 | Shell 白名单 | 允许执行的命令 | 仅允许 `python` / `python3` | **仅 python** |
| F4 | 与现有多 Agent 关系 | 谁进沙箱 | 建议：前台/订单/商品不变；**新增「数据分析专员」走沙箱** | 新增专员 |
| F5 | 退款审批 | 敏感操作 | 仍用现有 `process_refund` + Web 审批，不进沙箱改订单 | 保持现状 |
| **G. 运行与持久化（按你的选择简化）** |
| G1 | 对话 Session | 聊天记录 | 继续用现有 `SQLiteSession` + `ui_session_store` | 不变 |
| G2 | 沙箱快照 | 跨 run 是否保留工作区文件 | **不保留**：每次分析任务新建沙箱；报表从 `output/` 拷到本机 `reports/` | **不跨天保留** |
| G3 | 报表落盘 | 用户怎么拿到 report.md | 任务结束后脚本把 `output/report.md` 复制到 `ai_chat_robot/reports/` | 待编码 |
| G4 | Web 展示 | 是否在页面显示命令日志 | **不需要**；最多在客服回复里贴报表摘要或文件路径 | 不需要 |
| **H. 验收场景（开发完怎么测）** |
| H1 | 分析订单 | 用户说「分析一下订单数据」 | 沙箱跑 `analyze_orders.py`，返回统计摘要 | 必测 |
| H2 | 定价模拟 | 用户说「给键盘类商品打 9 折」 | 沙箱跑 `pricing.py`，生成 `pricing.json` | 必测 |
| H3 | 生成报表 | 用户说「生成今日销售报表」 | 沙箱跑 `generate_report.py`，本机 `reports/` 有 `.md` | 必测 |
| H4 | 安全 | Agent 不能乱删文件 | 尝试危险命令应被拒绝（白名单生效） | 建议测 |

---

### 十、建议执行顺序（照着做即可）

```
第 1 步  安装 Docker Desktop，docker version 通过
第 2 步  pip install "openai-agents[docker]"
第 3 步  python scripts/generate_catalog.py          # B1 B2
第 4 步  新建 sandbox/scripts/ 下三个 Python 脚本   # C1 C2 C3
第 5 步  本机逐个 python sandbox/scripts/xxx.py 跑通  # C4
第 6 步  新建 sandbox/ 目录结构与 manifest 配置      # D1～D4
第 7 步  编写 SandboxAgent + DockerSandboxClient     # E F
第 8 步  按 H1～H3 验收
```

**当前你只需先完成第 1～5 步**（环境与脚本），第 6～8 步可以交给我下一步帮你写代码。

---

### 十二、Sandbox 材料准备进度（2026-08-31 更新）

#### 已替你配置好（代码仓库内）

| 材料 | 路径 | 说明 |
|------|------|------|
| 沙箱策略 | `sandbox/security.py` | Shell **仅允许** `python/python3` + `scripts/` 下脚本；禁止 rm/curl/bash 等 |
| Docker 配置 | `sandbox/config.py` | `network_mode=none`（无外网）、`persist_session=False`（不跨天保留） |
| 业务脚本 | `sandbox/scripts/*.py` | 分析订单 / 定价 / 生成报表 |
| 工作区同步 | `sandbox/sync_workspace.py` | 把 `data/` 和 `scripts/` 复制到 `sandbox/workspace/` |
| 环境变量示例 | `.env.sandbox.example` | Docker 镜像等可选项 |
| 依赖声明 | `requirements.txt` | 已加入 `openai-agents[docker]`、`docker` |
| 报表输出目录 | `reports/`、`sandbox/workspace/output/` | 已创建 |

#### 需要你本机动手配置

| # | 你要做什么 | 命令 / 操作 | 如何确认成功 |
|---|-----------|-------------|--------------|
| **1** | 安装 Docker Desktop | [下载安装](https://www.docker.com/products/docker-desktop/)，启动后保持运行 | 终端执行 `docker version` 无报错 |
| **2** | 安装 Python 依赖 | `cd ai_chat_robot`<br>`pip install -r requirements.txt` | `python -c "import docker; import streamlit"` 无报错 |
| **3** | 配置 DeepSeek 密钥 | 项目根 `.env` 写入 `DEEPSEEK_API_KEY=...` | 现有 Web 客服能正常回复 |
| **4** | 生成并同步演示数据 | `python scripts/generate_catalog.py`<br>`python sandbox/sync_workspace.py` | 存在 `sandbox/workspace/data/orders.json` |
| **5** | 本机验证三个脚本 | `python sandbox/scripts/analyze_orders.py`<br>`python sandbox/scripts/pricing.py --category 外设 --discount 0.9`<br>`python sandbox/scripts/generate_report.py` | `sandbox/workspace/output/report.md` 有内容 |
| **6** | （可选）自定义 Docker 镜像 | 复制 `.env.sandbox.example` 到 `.env`，设置 `SANDBOX_DOCKER_IMAGE` | 默认 `python:3.11-slim` 可不改 |
| **7** | 等待下一步开发 | 将 `SandboxAgent` 接入 `robot.py` / `web_app.py` | 尚未编码，你完成 1～5 后告诉我 |

> **说明**：第 4～5 步每次更新 `data/` 或改脚本后建议重新执行 `sync_workspace.py`。

---

### 十一、原「最小决策表」（存档）

1. **沙箱后端**：Docker 本地 ✅  
2. **首要场景**：分析 JSON / 报表 / 定价脚本 ✅  
3. **数据从哪来**：脚本模拟 ✅  
4. **Shell**：允许，白名单仅 `python` ✅  
5. **跨天保留**：先不保留 ✅  
6. **Web 展示沙箱过程**：不需要 ✅  

---

## 参考链接

- [OpenAI Agents SDK](https://github.com/openai/openai-agents-python)
- [Models & Providers](https://openai.github.io/openai-agents-python/models/)
- [Sandbox Agents Quickstart](https://openai.github.io/openai-agents-python/sandbox_agents/)
- [Sandbox Concepts](https://openai.github.io/openai-agents-python/sandbox/guide/)
- [DeepSeek API 文档](https://api-docs.deepseek.com/)
