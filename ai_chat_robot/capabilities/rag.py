"""RAG 能力：供 Agent 调用的知识库检索工具。"""

from __future__ import annotations

from agents import function_tool

from config.settings import RAG_ENABLED, RAG_TOP_K
from rag.retriever import retrieve_knowledge_base_impl


@function_tool
def retrieve_knowledge_base(query: str, top_k: int = RAG_TOP_K) -> str:
    """从已索引的知识库中检索与 query 相关的文档片段（含来源路径）。

    适用于：项目说明、学习笔记、政策/手册类问答。
    检索失败时提示用户先运行 scripts/index_knowledge.py 构建索引。
    """
    if not RAG_ENABLED:
        return "RAG 已关闭（RAG_ENABLED=false）。"
    safe_top_k = max(1, min(int(top_k), 8))
    return retrieve_knowledge_base_impl(query=query, top_k=safe_top_k)


__all__ = ["retrieve_knowledge_base"]
