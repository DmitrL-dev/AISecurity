"""
RLM-Toolkit Retrieval Module.

Provides embedding-based, BM25, and hybrid retrieval.
"""

from .embeddings import EmbeddingRetriever, RetrievalResult, create_retriever
from .bm25 import BM25Index, BM25Config
from .hybrid import HybridRetriever, HybridResult

__all__ = [
    "EmbeddingRetriever",
    "RetrievalResult",
    "create_retriever",
    # BM25 (v2.5)
    "BM25Index",
    "BM25Config",
    # Hybrid (v2.5)
    "HybridRetriever",
    "HybridResult",
]

__version__ = "2.5.0"
