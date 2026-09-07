"""构建与加载 LlamaIndex 向量索引。"""

from __future__ import annotations

from pathlib import Path

from llama_index.core import Settings, StorageContext, VectorStoreIndex, load_index_from_storage
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.readers import SimpleDirectoryReader
from llama_index.embeddings.fastembed import FastEmbedEmbedding

from rag.config import DEFAULT_EMBED_MODEL, KNOWLEDGE_DIR, STORAGE_DIR


def _configure_settings(embed_model_name: str = DEFAULT_EMBED_MODEL) -> None:
    Settings.embed_model = FastEmbedEmbedding(model_name=embed_model_name)
    Settings.node_parser = SentenceSplitter(chunk_size=512, chunk_overlap=64)


def build_index(
    knowledge_dir: Path | None = None,
    storage_dir: Path | None = None,
    embed_model_name: str = DEFAULT_EMBED_MODEL,
) -> VectorStoreIndex:
    """从 knowledge_dir 读取文档并写入 storage_dir。"""
    knowledge_dir = knowledge_dir or KNOWLEDGE_DIR
    storage_dir = storage_dir or STORAGE_DIR

    if not knowledge_dir.is_dir():
        raise FileNotFoundError(f"知识库目录不存在: {knowledge_dir}")

    files = [
        p
        for p in knowledge_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in {".md", ".txt", ".json"}
    ]
    if not files:
        raise FileNotFoundError(
            f"知识库目录为空或无可索引文件: {knowledge_dir} "
            "(支持 .md / .txt / .json)"
        )

    _configure_settings(embed_model_name)
    documents = SimpleDirectoryReader(
        input_dir=str(knowledge_dir),
        recursive=True,
        required_exts=[".md", ".txt", ".json"],
    ).load_data()

    index = VectorStoreIndex.from_documents(documents, show_progress=True)
    storage_dir.mkdir(parents=True, exist_ok=True)
    index.storage_context.persist(persist_dir=str(storage_dir))
    return index


def load_index(
    storage_dir: Path | None = None,
    embed_model_name: str = DEFAULT_EMBED_MODEL,
) -> VectorStoreIndex:
    """加载已持久化的索引。"""
    storage_dir = storage_dir or STORAGE_DIR
    if not storage_dir.is_dir() or not any(storage_dir.iterdir()):
        raise FileNotFoundError(
            f"未找到 RAG 索引，请先运行: python scripts/index_knowledge.py ({storage_dir})"
        )

    _configure_settings(embed_model_name)
    storage_context = StorageContext.from_defaults(persist_dir=str(storage_dir))
    return load_index_from_storage(storage_context)
