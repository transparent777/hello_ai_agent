"""Backward-compatible facade for the canonical capability registry."""

from capabilities.registry import (
    ANALYTICS_TOOLS,
    DOCUMENT_TOOLS,
    RAG_TOOLS,
    ROUTER_TOOLS,
    WRITER_TOOLS,
)

__all__ = [
    "ANALYTICS_TOOLS",
    "DOCUMENT_TOOLS",
    "RAG_TOOLS",
    "ROUTER_TOOLS",
    "WRITER_TOOLS",
]
