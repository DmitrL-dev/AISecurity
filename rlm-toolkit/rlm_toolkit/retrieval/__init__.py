"""
RLM-Toolkit Retrieval Module.

Provides embedding-based, hybrid, and attention-based retrieval.
"""

from .embeddings import EmbeddingRetriever, RetrievalResult, create_retriever

# InfiniRetri (optional, requires infini-retri package)
try:
    from .infiniretri import InfiniRetriever

    INFINIRETRI_AVAILABLE = True
except ImportError:
    InfiniRetriever = None
    INFINIRETRI_AVAILABLE = False

__all__ = [
    "EmbeddingRetriever",
    "RetrievalResult",
    "create_retriever",
    "InfiniRetriever",
    "INFINIRETRI_AVAILABLE",
]

__version__ = "2.1.0"
