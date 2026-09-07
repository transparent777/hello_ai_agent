"""RAG 检索：返回带引用来源的文本片段。"""

from __future__ import annotations

from functools import lru_cache

from llama_index.core import VectorStoreIndex

from rag.config import DEFAULT_TOP_K
from rag.indexer import load_index


@lru_cache(maxsize=1)
def _get_index() -> VectorStoreIndex:
    return load_index()


def format_retrieval_results(nodes_with_scores: list, top_k: int) -> str:
    if not nodes_with_scores:
        return "未检索到相关内容。请尝试换关键词，或确认知识库已索引。"

    lines = [f"检索到 {min(len(nodes_with_scores), top_k)} 条相关片段：", ""]
    for rank, item in enumerate(nodes_with_scores[:top_k], start=1):
        node = item.node
        score = item.score
        source = node.metadata.get("file_name") or node.metadata.get("filename") or "unknown"
        text = (node.get_content() or "").strip()
        lines.append(f"[{rank}] 来源: {source} | 相关度: {score:.4f}")
        lines.append(text)
        lines.append("")
    lines.append("请基于以上片段回答，并注明引用来源。")
    return "\n".join(lines).strip()


def retrieve_knowledge_base_impl(query: str, top_k: int = DEFAULT_TOP_K) -> str:
    query = query.strip()
    if not query:
        return "检索 query 不能为空。"

    try:
        index = _get_index()
    except FileNotFoundError as exc:
        return str(exc)

    retriever = index.as_retriever(similarity_top_k=top_k)
    nodes = retriever.retrieve(query)
    return format_retrieval_results(nodes, top_k=top_k)


def clear_index_cache() -> None:
    _get_index.cache_clear()
