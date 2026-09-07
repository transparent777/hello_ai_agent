"""RAG 路径与默认参数。"""

from __future__ import annotations

from config.paths import PACKAGE_ROOT

# 待入库的原始文档目录（txt/md/json 等）
KNOWLEDGE_DIR = PACKAGE_ROOT / "knowledge_base"
# LlamaIndex 持久化索引目录
STORAGE_DIR = PACKAGE_ROOT / "rag_storage"

DEFAULT_TOP_K = 3
DEFAULT_EMBED_MODEL = "BAAI/bge-small-zh-v1.5"
