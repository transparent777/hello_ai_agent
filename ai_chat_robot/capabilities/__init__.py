"""Application capabilities exposed to Agent compositions.

This package is the stable boundary for tools. Implementations can continue to
live in the legacy ``tools`` and ``sandbox`` packages during migration.
"""

from capabilities.registry import (
    ANALYTICS_TOOLS,
    DOCUMENT_TOOLS,
    ROUTER_TOOLS,
    WRITER_TOOLS,
)

__all__ = [
    "ANALYTICS_TOOLS",
    "DOCUMENT_TOOLS",
    "ROUTER_TOOLS",
    "WRITER_TOOLS",
]
