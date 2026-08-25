# AI Agent 标准学习规范

> 本文档为 AI Agent 方向的标准学习计划,适用于具备 Python 基础的学习者。
> 目标:从底层原理到工程落地,系统掌握 AI Agent 的构建能力。

---

## 一、学习目标

通过本计划,学习者应具备以下能力:

1. 理解 Agent 的核心本质:**LLM + 工具调用 + 循环决策 + 记忆**
2. 能够不依赖框架,**手写**一个可工作的 ReAct Agent
3. 熟练使用主流框架(LangGraph 等)构建生产级 Agent
4. 掌握 RAG、多 Agent 协作、评估与部署等进阶能力
5. 具备成本控制、安全防护、可靠性设计等工程素养

---

## 二、前置要求

| 技能 | 要求 | 说明 |
|------|------|------|
| Python | 熟练 | 函数、类、异常处理、`requests`/`httpx`、异步(asyncio) |
| LLM 基础 | 了解 | token、prompt、temperature、system/user/assistant 消息结构 |
| API 使用 | 了解 | 至少会用一种 LLM API(OpenAI / Claude / 智谱 / DeepSeek 等) |
| 命令行 | 基本 | 运行脚本、管理环境、使用 git |

> 若不满足前置要求,先补 Python 与 LLM 基础,再进入正式计划。

---

## 三、学习周期总览

| 阶段 | 时间 | 主题 | 核心产出 |
|------|------|------|----------|
| 阶段 0 | 预备 | 基础补漏 | 通过前置能力自测 |
| 阶段 1 | 第 1 周 | LLM API 与工具调用 | 函数版 ChatGPT(可调用工具) |
| 阶段 2 | 第 2 周 | 手写 ReAct Agent | 手写循环决策 Agent |
| 阶段 3 | 第 3 周 | 结构化输出与记忆 | 带记忆的助手 |
| 阶段 4 | 第 4 周 | 框架入门(LangGraph) | 用框架重写 Agent |
| 阶段 5 | 第 5 周 | RAG 进阶 | 带引用的知识库问答 |
| 阶段 6 | 第 6 周 | 多 Agent 协作 | 多角色写作团队 |
| 阶段 7 | 第 7 周 | 构建与部署 | 可发布的 Agent 应用 |
| 阶段 8 | 第 8 周 | 评估/成本/安全 | 可靠的生产级 Agent |
| 阶段 9 | 第 9–10 周 | 深耕方向 | 个人 AI 助理 / 领域 Agent |

**建议投入:每天 2–3 小时,总计约 10 周。**

---

## 四、分阶段详解

### 阶段 1 · 第 1 周:LLM API 与工具调用(核心)

**目标:理解 Agent 的"手"是怎么长出来的**

学习要点:
- LLM API 基础调用与参数理解
- **Function Calling / Tool Use**(工具调用)——Agent 区别于普通聊天机器人的关键
- 工具调用完整流程:模型返回"要调哪个函数 + 参数" → 本地执行函数 → 结果回传模型 → 循环

动手项目:**函数版 ChatGPT**(查天气、算数、查信息,纯 API 手写,不引入框架)

完成标准:
- [ ] 能正确解析模型的工具调用请求
- [ ] 能执行函数并将结果回传
- [ ] 能处理"无需调用工具直接回答"的分支

---

### 阶段 2 · 第 2 周:手写 ReAct Agent

**目标:理解 Agent 的核心循环(决策 - 行动 - 观察)**

学习要点:
- ReAct 核心思想:`Thought → Action → Observation → 再 Thought`,直到 `Final Answer`
- **停止条件**、**最大步数**、**死循环防护**(否则会烧 token)

动手项目:**手写一个能搜索、计算、总结信息的 Agent**(手动实现,不用框架)

完成标准:
- [ ] 能自主决定何时调用工具、何时给出最终答案
- [ ] 有最大步数与超时保护
- [ ] 异常时能优雅降级而非崩溃

---

### 阶段 3 · 第 3 周:结构化输出 + 记忆

**目标:让 Agent 有"状态"和"记性"**

学习要点:
- 结构化输出(JSON mode / 固定格式返回)
- 短期记忆:对话历史管理、上下文窗口限制
- 长期记忆:向量数据库(embedding + 检索)、RAG 基础

动手项目:**能记住用户偏好、基于知识库回答的助手**

完成标准:
- [ ] 能稳定返回结构化 JSON
- [ ] 正确管理多轮对话上下文
- [ ] 能基于向量检索召回相关知识

---

### 阶段 4 · 第 4 周:框架入门(LangGraph)

**目标:把前几周手写的东西用框架重写一遍**

学习要点:
- LangChain Agent 抽象 或 **LangGraph**(主流,状态机思维)
- 节点、边、状态、条件路由

动手项目:**用 LangGraph 重写阶段 2 的 Agent,对比手写版**

完成标准:
- [ ] 理解状态机的建模方式
- [ ] 能说清框架与手写的异同
- [ ] 能扩展新的工具节点

---

### 阶段 5 · 第 5 周:RAG 进阶 + 检索优化

**目标:让 Agent 真正"会查资料"**

学习要点:
- 文档切分、向量化、混合检索、重排序(rerank)
- 多跳检索、查询改写
- 检索质量评估(召回率)

动手项目:**基于文档的问答 Agent,能引用原文出处**

完成标准:
- [ ] 能针对不同文档合理切分
- [ ] 检索结果带引用来源
- [ ] 能评估并优化检索质量

---

### 阶段 6 · 第 6 周:多 Agent 协作

**目标:从"一个 Agent"到"一组 Agent"**

学习要点:
- 角色分工:规划者、执行者、审查者
- 多 Agent 通信模式(顺序、并行、辩论)
- CrewAI / AutoGen / LangGraph 多智能体

动手项目:**"写作团队"——一个出草稿、一个审查、一个润色**

完成标准:
- [ ] 能设计清晰的 Agent 分工
- [ ] 掌握多 Agent 的通信与结果汇聚
- [ ] 能处理 Agent 间的依赖与失败

---

### 阶段 7 · 第 7 周:构建与部署

**目标:把 Agent 变成可用的产品**

学习要点:
- 流式输出(streaming)、前端交互
- 工具编排的错误处理、重试、超时
- 部署:FastAPI + 前端,或 Agent 平台(Coze / Dify)

动手项目:**一个完整的、能发布出去的 Agent 应用**

完成标准:
- [ ] 具备流式输出与交互界面
- [ ] 完善的错误处理与重试
- [ ] 成功部署并可被他人访问

---

### 阶段 8 · 第 8 周:评估、成本与可靠性(进阶)

**目标:让 Agent 从"能跑"到"靠谱"**

学习要点:
- 评估 Agent 表现(成功率、轨迹正确性)
- 成本控制(token 用量、缓存、模型分级)
- 安全:提示注入、权限控制、工具沙箱
- 追踪调试(LangSmith / Langfuse)

完成标准:
- [ ] 能建立可量化的评估指标
- [ ] 能有效控制单次任务成本
- [ ] 具备基本的安全防护意识

---

### 阶段 9 · 第 9–10 周:深耕方向(选一个)

| 方向 | 内容 |
|------|------|
| 多模态 Agent | 看图、听、视觉操作电脑/手机 |
| Agent + 计算机使用 | Computer Use,让 Agent 操作 GUI |
| 强化学习 / 训练 | 微调、RLHF、让模型更会"用工具" |
| 真实业务落地 | 结合领域做一个能产生价值的 Agent |

**终极项目:做一个"个人 AI 助理"或"自动化工作流 Agent",整合前面所有技能。**

---

## 五、学习原则

1. **先原理后框架**:前 3 周务必手写,理解了本质,框架只是语法糖。
2. **每个阶段都要有项目产出**:光看不练学不会 Agent。
3. **注意成本控制**:Agent 循环消耗大量 token,开发期用便宜模型(gpt-4o-mini、Claude Haiku、DeepSeek 等)。
4. **多读优秀项目源码**,推荐:
   - `smolagents`(HuggingFace,极简,适合学原理)
   - `openai-agents-sdk` / Anthropic 官方 Agent SDK
   - `LangGraph` 官方教程
   - `claude-code` / `openhands`(工业级 Agent 参考)

---

## 六、验收标准(总结)

完成全部阶段后,应能独立:

- [ ] 从零手写一个 ReAct Agent
- [ ] 用框架构建带记忆、带工具的 RAG Agent
- [ ] 构建多 Agent 协作系统
- [ ] 部署一个生产可用、可控成本、有评估的 Agent 应用
- [ ] 针对具体业务场景设计并落地 Agent 方案

---

## 附录:各阶段学习资源清单

> 用法:每阶段选 **1 个主线课程 + 官方文档**,学完立刻做项目,避免陷在教程里。

### 阶段 0 · Python 基础

| 资源 | 类型 | 说明 | 推荐度 |
|------|------|------|--------|
| 廖雪峰 Python 教程 | 文字(免费) | liaoxuefeng.com,语法清楚,适合快速过 | ⭐ 主线 |
| 菜鸟教程 Python3 | 文字(免费) | runoob.com,可当手册随时查 | 补充 |
| 黑马程序员 / 尚硅谷 Python | B站视频(免费) | 系统完整、中文讲解,适合零基础 | 主线 |
| 《Python编程:从入门到实践》 | 书籍 | 有大量练手项目 | 补充 |
| Python 官方教程 | 文字(免费) | docs.python.org,权威但偏硬 | 查漏用 |

**重点补**:`requests`/`httpx`(调 API)、`asyncio`(异步)、`json`。

### 阶段 1 · LLM API 与工具调用

| 资源 | 类型 | 说明 |
|------|------|------|
| 吴恩达《ChatGPT Prompt Engineering for Developers》 | 课程(DeepLearning.AI,有中文) | 免费,先搞懂 prompt 与 API 基础 |
| 吴恩达《Building Systems with the ChatGPT API》 | 课程(DeepLearning.AI,有中文) | 手把手教调 API、工具调用 |
| OpenAI 官方文档 · Function Calling | 文档 | platform.openai.com/docs |
| Anthropic 官方文档 · Tool Use | 文档 | docs.claude.com |

> ⭐ 本阶段关键词是 **Function Calling / Tool Use**,把官方文档此章节吃透。

### 阶段 2 · 手写 ReAct Agent

| 资源 | 类型 | 说明 |
|------|------|------|
| Anthropic《Building Effective Agents》 | 博客(免费) | **必读**,讲清 workflow 与 agent 的区别 |
| Lilian Weng《LLM Powered Autonomous Agents》 | 博客(免费) | 经典长文,系统梳理 Agent 架构 |
| ReAct 论文(Yao et al. 2022) | 论文 | 只看核心思想即可 |
| OpenAI《A Practical Guide to Building Agents》 | 视频/讲义(免费) | 官方讲如何从简到繁构建 Agent |

### 阶段 3 · 结构化输出 + 记忆

| 资源 | 类型 | 说明 |
|------|------|------|
| OpenAI/Anthropic 文档 · Structured Outputs / JSON mode | 文档 | 结构化输出官方用法 |
| 吴恩达《Vector Databases: from Embeddings to Applications》 | 课程(有中文) | embedding 与向量数据库,RAG 入门必备 |
| Pinecone Learn / Weaviate 教程 | 文字(免费) | 向量检索实操 |
| LangChain 官方 RAG 入门教程 | 文档 | 第一篇 RAG 教程 |

### 阶段 4 · LangGraph 框架

| 资源 | 类型 | 说明 |
|------|------|------|
| LangGraph 官方文档 + 教程 | 文档(免费) | langchain-ai.github.io/langgraph,先看 Quick Start |
| 吴恩达《AI Agents in LangGraph》 | 课程(DeepLearning.AI) | 系统讲 LangGraph 构建 Agent,推荐 |
| 吴恩达《Functions, Tools and Agents with LangChain》 | 课程 | 框架内工具调用,可作补充 |

### 阶段 5 · RAG 进阶

| 资源 | 类型 | 说明 |
|------|------|------|
| 吴恩达《Building and Evaluating Advanced RAG》 | 课程(DeepLearning.AI) | 进阶 RAG 含评估,很实战 |
| 吴恩达 Advanced RAG 相关课程 | 课程 | 查询改写、多跳、rerank 等 |
| LangChain / LlamaIndex 文档 RAG 章节 | 文档 | 两套主流 RAG 方案 |
| 各家 rerank 服务文档(Cohere 等) | 文档 | 重排序实操 |

### 阶段 6 · 多 Agent 协作

| 资源 | 类型 | 说明 |
|------|------|------|
| 吴恩达《Multi AI Agent Systems with crewAI》 | 课程(DeepLearning.AI) | 多 Agent 入门首选 |
| AutoGen(Microsoft)官方文档 | 文档 | 多 Agent 对话模式 |
| OpenAI Agents SDK 文档 | 文档 | 官方 Agent SDK,handoff、多 Agent 编排 |

### 阶段 7 · 部署

| 资源 | 类型 | 说明 |
|------|------|------|
| FastAPI 官方教程 | 文档(免费) | 后端服务首选 |
| Streamlit / Gradio | 文档(免费) | 快速搭前端界面,先出 demo |
| Dify / Coze 文档 | 文档 | 低代码 Agent 平台,快速验证想法 |

### 阶段 8 · 评估、成本与安全

| 资源 | 类型 | 说明 |
|------|------|------|
| LangSmith 文档 | 文档 | Agent 追踪与评估 |
| Langfuse 文档 | 文档 | 开源替代,含追踪与成本 |
| OWASP Top 10 for LLM Applications | 文档(免费) | llmtop10.com,LLM 应用安全清单,必读 |
| Anthropic 文档 · 安全/系统提示 | 文档 | 提示注入、权限控制 |

### 阶段 9 · 深耕方向(选做)

| 方向 | 推荐资源 |
|------|----------|
| 多模态 / Computer Use | Anthropic / OpenAI 官方 Computer Use 文档与示例 |
| 训练 / 微调 | 李沐《动手学深度学习》(d2l.ai,有中文,免费);Hugging Face 课程 |
| 通用学习 | 李沐 B站「跟李沐学AI」——深入理解底层原理的宝藏频道 |

### 资源使用原则

1. 优先 **吴恩达 DeepLearning.AI 系列**——免费、有中文字幕、实战导向,性价比最高。
2. **官方文档永远是权威**,框架/API 更新快,以文档为准。
3. 中文资料补基础,Agent 核心内容建议配合英文原文。

---

*文档创建日期:2026-08-14*
*建议按周推进,每阶段完成勾选对应完成标准后再进入下一阶段。*
