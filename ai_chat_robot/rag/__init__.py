"""LlamaIndex RAG public API with lazy dependency loading."""

from importlib import import_module
import warnings

from pydantic.warnings import UnsupportedFieldAttributeWarning


# LlamaIndex 0.12 attaches validate_default to a union member. Pydantic ignores
# that metadata, so suppress only this known third-party compatibility warning.
warnings.filterwarnings(
    "ignore",
    message=r"The 'validate_default' attribute with value True was provided.*",
    category=UnsupportedFieldAttributeWarning,
)

__all__ = ["build_index", "load_index", "retrieve_knowledge_base_impl"]


def __getattr__(name: str):
    if name in {"build_index", "load_index"}:
        return getattr(import_module(".indexer", __name__), name)
    if name == "retrieve_knowledge_base_impl":
        return getattr(import_module(".retriever", __name__), name)
    raise AttributeError(name)
