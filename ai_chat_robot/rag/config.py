"""RAG 路径与默认参数。"""

from __future__ import annotations

from config.paths import PACKAGE_ROOT

KNOWLEDGE_DIR = PACKAGE_ROOT / "knowledge_base"
STORAGE_DIR = PACKAGE_ROOT / "rag_storage"

DEFAULT_TOP_K = 3
DEFAULT_EMBED_MODEL = "BAAI/bge-small-zh-v1.5"
SUPPORTED_EXTENSIONS = (".md", ".txt", ".json", ".pdf")
