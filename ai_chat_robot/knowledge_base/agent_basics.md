# AI Agent 学习笔记（知识库示例）

## Agent 的本质

Agent = LLM + 工具调用 + 循环决策 + 记忆。

核心循环：用户提问 → 模型决定是否调用工具 → 执行工具 → 把结果回传 → 再决策，直到给出最终答案。

## ReAct

ReAct 模式：Thought（思考）→ Action（行动）→ Observation（观察）→ 重复，直到 Final Answer。

手写 Agent 时必须设置：

- 最大步数（max_turns）
- 超时保护
- 工具异常时的降级策略

## RAG 在本项目中的位置

本项目采用方案 A：不单独造 RAG 平台，而是用 LlamaIndex 做检索层，通过 `retrieve_knowledge_base` 工具供文档/写作专员调用。

流程：

1. 文档放入 `knowledge_base/`
2. `python scripts/index_knowledge.py` 构建索引
3. 用户提问时 Agent 检索相关片段并带引用回答

## 多 Agent 分工

- workspace_router（L1）：判断、派发、验收、终稿
- document_specialist：读文件、知识库检索、导出
- writer_specialist：长文写作
- data_specialist：数据分析与报表

## 安全与审批

工具可配置 `needs_approval`；审批暂停后应从 RunState 恢复，而不是开启新的用户轮次。
