"""RAG 检索与 Router 意图识别测试。"""

from __future__ import annotations

import sys
from pathlib import Path

_APP_DIR = Path(__file__).resolve().parent.parent
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

import rag  # noqa: F401 - installs narrowly scoped third-party warning filter
from llama_index.core.schema import NodeWithScore, TextNode

from rag.hybrid import reciprocal_rank_fusion
from rag.retriever import format_retrieval_results, retrieve_knowledge_base_impl
from rag.router_hints import detect_knowledge_base_intent


class _FakeNode:
    def __init__(self, text: str, metadata: dict, node_id: str):
        self._text = text
        self.metadata = metadata
        self.node_id = node_id

    def get_content(self) -> str:
        return self._text


class _FakeItem:
    def __init__(self, text: str, source: str, score: float, node_id: str):
        self.node = _FakeNode(text, {"file_name": source}, node_id)
        self.score = score


def test_format_retrieval_results_includes_source():
    items = [_FakeItem("Agent = LLM + 工具", "agent_basics.md", 0.91, "n1")]
    out = format_retrieval_results(items, top_k=3)
    assert "agent_basics.md" in out
    assert "Agent = LLM + 工具" in out
    assert "引用来源" in out
    assert "混合检索" in out or "向量检索" in out


def test_reciprocal_rank_fusion_merges_lists():
    list_a = [
        NodeWithScore(node=TextNode(text="a", id_="1"), score=0.9),
        NodeWithScore(node=TextNode(text="b", id_="2"), score=0.8),
    ]
    list_b = [
        NodeWithScore(node=TextNode(text="b", id_="2"), score=0.95),
        NodeWithScore(node=TextNode(text="c", id_="3"), score=0.7),
    ]
    fused = reciprocal_rank_fusion([list_a, list_b], top_k=2)
    ids = [item.node.node_id for item in fused]
    assert "2" in ids
    assert len(ids) == 2


def test_detect_knowledge_base_intent():
    assert detect_knowledge_base_intent("根据知识库解释什么是 ReAct")
    assert detect_knowledge_base_intent("项目文档里 Agent 是什么")
    assert not detect_knowledge_base_intent("今天天气怎么样")


def test_retrieve_without_index_returns_helpful_message():
    from unittest.mock import patch

    from rag.retriever import clear_index_cache

    with patch(
        "rag.retriever.load_index",
        side_effect=FileNotFoundError("请先运行 python scripts/index_knowledge.py 构建索引"),
    ):
        clear_index_cache()
        out = retrieve_knowledge_base_impl("什么是 ReAct")
    assert "index_knowledge" in out or "未找到" in out or "RAG" in out or "检索" in out
