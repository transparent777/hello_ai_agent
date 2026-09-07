"""知识库意图识别：供 Router 自动派发 document_specialist。"""

from __future__ import annotations

import re

_KB_PATTERNS = (
    r"知识库",
    r"(?:根据|查阅|检索|搜索).*(?:文档|资料|手册|笔记|知识库)",
    r"(?:文档|资料|手册|笔记).*(?:里|中|提到|说明|写了)",
    r"(?:什么是|解释一下|介绍一下).*(?:ReAct|RAG|Agent|智能体)",
    r"项目.*(?:说明|文档|介绍|架构)",
    r"学习笔记",
    r"retrieve_knowledge",
    r"带引用.*回答",
)

_KB_HINT = (
    "[系统-勿复述] 知识库/RAG 问答：用户需要基于已索引文档作答。"
    "信息足够时请 handoff 给 document_specialist，由其调用 retrieve_knowledge_base "
    "（混合检索 BM25+向量）检索后回答，并注明引用来源。禁止 L1 直接编造知识库内容。\n\n"
)


def detect_knowledge_base_intent(text: str) -> bool:
    lowered = text.lower()
    return any(re.search(pattern, lowered, flags=re.IGNORECASE) for pattern in _KB_PATTERNS)


def build_knowledge_base_router_hint() -> str:
    return _KB_HINT
