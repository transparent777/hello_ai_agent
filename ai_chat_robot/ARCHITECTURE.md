# ai_chat_robot 架构说明

本文档是工程的架构地图。代码目前保持原有目录，以降低重构风险；新功能应按本文档的边界放置。

第一轮应用层已落地在 `application/`：`ChatTurnService`、`ApprovalService` 和 `SessionService` 被 Web/CLI 入口复用。底层 `orchestrator/`、`services/` 路径暂时保留，作为兼容适配器。

第二轮已落地 `adapters/`：`llm_provider.py` 负责 DeepSeek SDK 客户端，`agent_runtime.py` 负责 Agent `RunConfig` 与沙箱组装；`config/llm.py` 现在仅是兼容导出层。`orchestrator` 的 Runner 导出采用惰性加载，避免路由 Agent 初始化时的循环依赖。

## 1. 系统定位

`ai_chat_robot` 是一个多 Agent 工作台：

1. 接收 Web 或终端用户消息。
2. 由路由 Agent 将请求交给文档、写作或数据专员。
3. 专员调用文件、业务数据、导出和沙箱能力。
4. 敏感工具经过人工审批。
5. 对话、审批、沙箱状态和运行指标分别持久化。

## 2. 当前运行链路

```text
Web (web_app.py) / CLI (robot.py)
              |
              v
        orchestrator.runner
              |
              +--> guardrails (输入、输出、工具参数)
              +--> specialists.router
              |       +--> document_specialist --> tools.file / tools.export / tools.skill
              |       +--> writer_specialist   --> tools.file / tools.export / tools.skill
              |       +--> data_specialist     --> sandbox.analytics_tools
              |
              +--> services.approval_store / ui_session_store / tracing
              +--> sandbox.runtime / session_store / memory_sync
              +--> mcp_integration (可选本地/托管 MCP)
              +--> config.llm (DeepSeek + RunConfig)
```

## 3. 目录职责

| 目录 | 现在负责什么 | 边界规则 |
| --- | --- | --- |
| `web_app.py`, `robot.py` | 两个入口和 UI/CLI 展示 | 只做输入输出和依赖组装，不放业务规则 |
| `orchestrator/` | 一轮 Agent 执行、流式输出、handoff、审批恢复 | 只编排流程，通过接口调用基础设施 |
| `specialists/` | Agent 定义、路由和专员工具集合 | 不直接处理数据库或 Docker 细节 |
| `tools/` | 文件、导出、电商查询、Skill 工具 | 工具参数校验由 `guardrails/` 统一完成 |
| `guardrails/` | 输入、输出和工具调用前检查 | 不反向依赖具体 UI；尽量不导入工具实现 |
| `sandbox/` | Docker 会话、脚本执行、产物审查、沙箱持久化 | `sandbox/workspace/` 是运行时目录，不是源码 |
| `services/` | 会话、审批、追踪、指标等持久化/横切能力 | 不创建 Agent，不决定业务路由 |
| `config/` | 环境变量、路径和 LLM 配置 | 配置读取集中在这里，避免其他模块自行读环境变量 |
| `mcp_integration/` | MCP 客户端生命周期和工具过滤 | 作为外部适配器，不参与路由决策 |
| `scripts/` | 开发、初始化、评估和运维命令 | 不被 Agent 直接当作业务模块导入 |
| `data/`, `skills/`, `workspace_user/` | 示例数据、提示规范、用户工作区 | 明确区分只读输入、只读规范和可写输出 |

## 4. 目前最需要治理的耦合

### 4.1 `config` 不是纯配置层

`config.llm` 同时创建 Provider、检查 Docker、恢复沙箱状态并写入 session。建议逐步拆成：

- `config/`: 只解析并校验配置。
- `adapters/llm/`: 创建 DeepSeek/OpenAI 客户端。
- `adapters/sandbox/`: 创建 `RunConfig` 和 Docker 客户端。
- `application/bootstrap.py`: 在启动时组装上述依赖。

### 4.2 `orchestrator.runner` 依赖过多基础设施

Runner 同时处理流式事件、审批、发布产物、记忆刷新、指标和追踪。后续应保留一个“执行一轮”的核心流程，把副作用收敛到端口接口：

```text
ChatTurnService
  -> AgentRuntime
  -> ApprovalRepository
  -> SessionRepository
  -> ArtifactPublisher
```

### 4.3 Agent 定义与工具注册混在一起

当前 `specialists/*.py` 既写提示词又决定工具实现。建议拆成：

- `agents/definitions.py`: Agent 名称、提示词、handoff 描述。
- `capabilities/`: 文件、导出、订单、分析能力。
- `composition/agent_factory.py`: 将 Agent 和能力组装起来。

### 4.4 沙箱源码和运行时副本重复

`sandbox/scripts/` 是源码，`sandbox/workspace/scripts/` 是同步副本；后者不应手工编辑或纳入源码审查。建议：

- 仅保留 `sandbox/scripts/` 作为唯一源。
- 启动/运行前由 `sync_workspace` 生成 `sandbox/workspace/`。
- 将整个 `sandbox/workspace/` 标记为运行时产物并从版本库移除。

### 4.5 两个入口缺少共享应用服务

`web_app.py` 和 `robot.py` 都处理 turn、审批和会话。入口应只负责适配：

```text
WebAdapter / CliAdapter
          -> ApplicationService
          -> AgentRuntime
```

这样可以避免修复只落在其中一个入口。

## 5. 推荐目标目录

这是逐步迁移目标，不要求一次性移动所有文件：

```text
ai_chat_robot/
  app/
    web.py                 # Streamlit 入口
    cli.py                 # 终端入口
    bootstrap.py           # 依赖组装
  application/
    chat_turn.py           # 一轮对话用例
    approvals.py           # 审批用例
    sessions.py            # 会话用例
  domain/
    agents/                # Agent 定义和路由策略
    policies/               # handoff、输出和安全策略
    models/                 # 会话、审批、产物 DTO
  capabilities/
    files.py
    exports.py
    ecommerce.py
    analytics.py
  adapters/
    llm/
    sandbox/
    mcp/
    persistence/
    telemetry/
  config/
  scripts/
  data/
  skills/
  tests/
```

## 6. 依赖方向

允许的方向：

```text
app -> application -> domain
app -> adapters
application -> domain + capability interfaces
adapters -> domain/interfaces
capabilities -> domain + adapters (必要时)
config -> (无业务模块依赖)
```

禁止的新依赖：

- `domain` 导入 Streamlit、Docker、SQLite 或具体 SDK。
- `guardrails` 导入 `web_app` 或 `robot`。
- `config` 导入 `orchestrator`、`specialists` 或具体工具。
- 入口直接调用 `sandbox` 内部文件操作；必须通过 application service。

## 7. 分阶段迁移顺序

1. **先稳定边界**：补充类型和接口，保持现有导入路径兼容。
2. **抽取应用服务**：从两个入口提取 `ChatTurnService`、`ApprovalService`、`SessionService`。
3. **拆配置和适配器**：将 `config.llm` 中的客户端创建、沙箱创建移出配置层。
4. **统一能力目录**：合并 `tools/` 和 `sandbox/analytics_tools.py` 的工具注册方式。
5. **清理运行时副本**：让 `sandbox/workspace/` 完全由脚本生成，并加入发布检查。
6. **最后移动目录**：完成 `app/`、`application/`、`adapters/` 重命名后，再删除兼容导出。

每一步都应保持：`python -m compileall ai_chat_robot`、单元测试和沙箱 E2E 可运行。

## 8. 新代码放哪里

- 新的用户流程：`application/`。
- 新的 Agent 提示词或路由规则：`domain/agents/` 或 `domain/policies/`。
- 新的文件/订单/报表能力：`capabilities/`。
- 新的 Docker、MCP、LLM 或数据库实现：`adapters/`。
- 新的环境变量：`config/`，并同步 `.env.sandbox.example`。
- 新的启动/清理/评估命令：`scripts/`。
- 不要把业务逻辑继续添加到 `web_app.py`、`robot.py` 或 `config.llm`。
## 9. 第三轮落地

- `orchestrator/stream_runtime.py` 统一 Agent SDK 的新运行与状态恢复流程，集中处理 stream event、文本增量、handoff 和 React 步骤。
- `orchestrator/approval_runtime.py` 集中处理审批记录、状态恢复、审批审计、产物发布和记忆刷新。
- `orchestrator/runner.py` 只负责一轮用户请求的生命周期、重试、沙箱配额、guardrail 错误映射和最终输出整理；`run_streamed_turn`、`resume_from_state` 等旧名称仍作为兼容入口。

新的依赖方向为：

```text
entrypoints -> runner -> stream_runtime / approval_runtime
                         -> adapters + services + sandbox
```

新增运行时逻辑应优先放入上述专职模块，避免再次把 SDK 事件处理、审批持久化和业务生命周期混回一个文件。

## Third-round extraction

The third round keeps the public orchestrator imports stable while separating SDK stream handling (`orchestrator/stream_runtime.py`) from approval state and publication (`orchestrator/approval_runtime.py`). `runner.py` now coordinates one user-turn lifecycle, retries, sandbox slots, guardrail mapping, and output finalization.

## Fourth-round capability boundary

Agent definitions now consume tools through `capabilities/registry.py` instead of assembling dependencies from both `tools/` and `sandbox/`. The capability package exposes file, export, skill, and analytics operations; legacy modules remain compatibility facades while their implementations migrate incrementally.

Sandbox lifecycle calls used by entrypoints and orchestration now go through `adapters/sandbox_runtime.py`. Docker, workspace synchronization, and artifact publication remain implementation details of the sandbox adapter.
