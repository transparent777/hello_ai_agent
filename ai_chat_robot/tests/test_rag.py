"""RAG 检索格式化单元测试（不依赖向量模型下载）。"""

from __future__ import annotations

import sys
from pathlib import Path

_APP_DIR = Path(__file__).resolve().parent.parent
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

from rag.retriever import format_retrieval_results, retrieve_knowledge_base_impl


class _FakeNode:
    def __init__(self, text: str, metadata: dict):
        self._text = text
        self.metadata = metadata

    def get_content(self) -> str:
        return self._text


class _FakeItem:
    def __init__(self, text: str, source: str, score: float):
        self.node = _FakeNode(text, {"file_name": source})
        self.score = score


def test_format_retrieval_results_includes_source():
    items = [_FakeItem("Agent = LLM + 工具", "agent_basics.md", 0.91)]
    out = format_retrieval_results(items, top_k=3)
    assert "agent_basics.md" in out
    assert "Agent = LLM + 工具" in out
    assert "引用来源" in out


def test_retrieve_without_index_returns_helpful_message():
    out = retrieve_knowledge_base_impl("什么是 ReAct")
    assert "index_knowledge" in out or "未找到" in out or "RAG" in out
