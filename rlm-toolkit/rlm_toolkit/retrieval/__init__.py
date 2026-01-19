"""
RLM-Toolkit Retrieval Module.

Provides embedding-based and hybrid retrieval.
"""

from .embeddings import EmbeddingRetriever, RetrievalResult, create_retriever

__all__ = [
    "EmbeddingRetriever",
    "RetrievalResult",
    "create_retriever",
]

__version__ = "1.1.0"
