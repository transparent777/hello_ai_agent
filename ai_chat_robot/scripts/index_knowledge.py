"""构建 knowledge_base 的 LlamaIndex 向量索引。"""

from __future__ import annotations

import sys
from pathlib import Path

_APP_DIR = Path(__file__).resolve().parent.parent
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

from rag.indexer import build_index
from rag.retriever import clear_index_cache


def main() -> None:
    print("正在构建知识库索引...")
    build_index()
    clear_index_cache()
    print("完成。索引已写入 rag_storage/")


if __name__ == "__main__":
    main()
