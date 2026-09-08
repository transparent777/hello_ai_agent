"""混合检索：BM25（关键词）+ 向量（语义），RRF 融合排序。"""

from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO

from llama_index.core import VectorStoreIndex
from llama_index.core.schema import NodeWithScore

# bm25s prints a Windows resource-module notice during import instead of using
# the warnings API. It has no effect on retrieval and should not reach the UI.
with redirect_stdout(StringIO()):
    from llama_index.retrievers.bm25 import BM25Retriever


def reciprocal_rank_fusion(
    result_lists: list[list[NodeWithScore]],
    *,
    top_k: int,
    rrf_k: int = 60,
) -> list[NodeWithScore]:
    """Reciprocal Rank Fusion：合并多路检索结果。"""
    scores: dict[str, float] = {}
    nodes: dict[str, NodeWithScore] = {}

    for results in result_lists:
        for rank, item in enumerate(results):
            node_id = item.node.node_id
            nodes[node_id] = item
            scores[node_id] = scores.get(node_id, 0.0) + 1.0 / (rrf_k + rank + 1)

    ranked = sorted(scores.items(), key=lambda pair: pair[1], reverse=True)[:top_k]
    fused: list[NodeWithScore] = []
    for node_id, score in ranked:
        base = nodes[node_id]
        fused.append(NodeWithScore(node=base.node, score=score))
    return fused


def hybrid_retrieve(
    index: VectorStoreIndex,
    query: str,
    *,
    top_k: int,
    fetch_k: int | None = None,
) -> list[NodeWithScore]:
    """BM25 + 向量双路检索，RRF 融合。"""
    corpus_size = len(getattr(index.docstore, "docs", {}) or {})
    fetch_k = fetch_k or max(top_k * 2, 6)
    if corpus_size > 0:
        fetch_k = min(fetch_k, corpus_size)
    else:
        fetch_k = max(fetch_k, top_k)
    fetch_k = max(1, fetch_k)

    vector_nodes = index.as_retriever(similarity_top_k=fetch_k).retrieve(query)
    bm25_nodes = BM25Retriever.from_defaults(
        docstore=index.docstore,
        similarity_top_k=fetch_k,
    ).retrieve(query)

    return reciprocal_rank_fusion(
        [vector_nodes, bm25_nodes],
        top_k=top_k,
    )
