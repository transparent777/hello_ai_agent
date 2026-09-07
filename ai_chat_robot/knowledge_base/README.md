# 知识库（RAG）

将 `.md` / `.txt` / `.json` / `.pdf` 放在此目录，然后运行：

```bash
cd ai_chat_robot
python scripts/index_knowledge.py
```

Agent 可通过 `retrieve_knowledge_base` 工具检索这里的文档。

## 建议

- 支持 PDF（通过 pypdf 解析文本层）
- 默认启用 **混合检索**：BM25 + 向量（`RAG_HYBRID_ENABLED=true`）
- 更新文档后重新执行 `index_knowledge.py`
- 索引产物在 `rag_storage/`（可删除后重建）
