"""
Embedding-Based Retrieval for RLM-Toolkit.

Provides semantic search using sentence-transformers embeddings.
"""

import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple
import numpy as np

logger = logging.getLogger("rlm_retrieval.embeddings")

# Try to import sentence-transformers
try:
    from sentence_transformers import SentenceTransformer

    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    SentenceTransformer = None


@dataclass
class RetrievalResult:
    """Result from embedding retrieval."""

    content: str
    score: float
    index: int
    metadata: Optional[Dict[str, Any]] = None


class EmbeddingRetriever:
    """
    Semantic retrieval using sentence-transformers.

    Falls back to keyword matching if sentence-transformers not installed.

    Example:
        >>> retriever = EmbeddingRetriever()
        >>> retriever.index(["Paris is capital of France", "Berlin is in Germany"])
        >>> results = retriever.search("What is the capital of France?")
    """

    # Default model - small and fast
    DEFAULT_MODEL = "all-MiniLM-L6-v2"

    def __init__(
        self,
        model_name: str = None,
        use_embeddings: bool = True,
        cache_embeddings: bool = True,
    ):
        """
        Initialize retriever.

        Args:
            model_name: Sentence-transformer model name
            use_embeddings: Whether to use embeddings (False = keyword fallback)
            cache_embeddings: Cache computed embeddings
        """
        self.model_name = model_name or self.DEFAULT_MODEL
        self.use_embeddings = use_embeddings and SENTENCE_TRANSFORMERS_AVAILABLE
        self.cache_embeddings = cache_embeddings

        self.model = None
        self._corpus: List[str] = []
        self._corpus_embeddings: Optional[np.ndarray] = None
        self._metadata: List[Dict] = []

        if self.use_embeddings:
            self._load_model()
        else:
            logger.warning(
                "sentence-transformers not available, using keyword fallback"
            )

    def _load_model(self):
        """Lazy load the model."""
        if self.model is None and SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                logger.info(f"Loading embedding model: {self.model_name}")
                self.model = SentenceTransformer(self.model_name)
                logger.info("Embedding model loaded")
            except Exception as e:
                logger.error(f"Failed to load model: {e}")
                self.use_embeddings = False

    def embed(self, texts: List[str]) -> np.ndarray:
        """
        Generate embeddings for texts.

        Args:
            texts: List of texts to embed

        Returns:
            NumPy array of embeddings (n_texts, embedding_dim)
        """
        if not self.use_embeddings or self.model is None:
            # Fallback: simple TF-IDF-like representation
            return self._simple_embed(texts)

        return self.model.encode(texts, convert_to_numpy=True)

    def _simple_embed(self, texts: List[str]) -> np.ndarray:
        """Simple bag-of-words embedding fallback."""
        # Build vocabulary
        vocab = set()
        for text in texts:
            vocab.update(text.lower().split())
        vocab = sorted(vocab)
        word_to_idx = {w: i for i, w in enumerate(vocab)}

        # Create embeddings
        embeddings = np.zeros((len(texts), len(vocab)))
        for i, text in enumerate(texts):
            words = text.lower().split()
            for word in words:
                if word in word_to_idx:
                    embeddings[i, word_to_idx[word]] += 1
            # Normalize
            norm = np.linalg.norm(embeddings[i])
            if norm > 0:
                embeddings[i] /= norm

        return embeddings

    def index(self, corpus: List[str], metadata: Optional[List[Dict]] = None):
        """
        Index a corpus for retrieval.

        Args:
            corpus: List of documents to index
            metadata: Optional metadata for each document
        """
        self._corpus = corpus
        self._metadata = metadata or [{} for _ in corpus]

        if self.cache_embeddings:
            logger.info(f"Indexing {len(corpus)} documents...")
            self._corpus_embeddings = self.embed(corpus)
            logger.info("Indexing complete")

    def search(
        self,
        query: str,
        top_k: int = 5,
        threshold: float = 0.0,
    ) -> List[RetrievalResult]:
        """
        Search for relevant documents.

        Args:
            query: Search query
            top_k: Maximum results to return
            threshold: Minimum similarity score

        Returns:
            List of RetrievalResult sorted by score
        """
        if not self._corpus:
            return []

        if self.use_embeddings and self._corpus_embeddings is not None:
            # Use cached embeddings
            query_embedding = self.embed([query])[0]
            corpus_embeddings = self._corpus_embeddings
        else:
            # Fallback: compute embeddings together for consistent vocabulary
            all_texts = [query] + self._corpus
            all_embeddings = self._simple_embed(all_texts)
            query_embedding = all_embeddings[0]
            corpus_embeddings = all_embeddings[1:]

        # Calculate cosine similarity
        scores = self._cosine_similarity(query_embedding, corpus_embeddings)

        # Get top-k results
        indices = np.argsort(scores)[::-1][:top_k]

        results = []
        for idx in indices:
            score = float(scores[idx])
            if score >= threshold:
                results.append(
                    RetrievalResult(
                        content=self._corpus[idx],
                        score=score,
                        index=idx,
                        metadata=self._metadata[idx] if self._metadata else None,
                    )
                )

        return results

    def _cosine_similarity(self, query: np.ndarray, corpus: np.ndarray) -> np.ndarray:
        """Calculate cosine similarity between query and corpus."""
        # Normalize
        query_norm = query / (np.linalg.norm(query) + 1e-8)
        corpus_norms = corpus / (np.linalg.norm(corpus, axis=1, keepdims=True) + 1e-8)

        # Dot product
        return np.dot(corpus_norms, query_norm)

    def add(self, document: str, metadata: Optional[Dict] = None) -> int:
        """
        Add a single document to the index.

        Returns:
            Index of added document
        """
        idx = len(self._corpus)
        self._corpus.append(document)
        self._metadata.append(metadata or {})

        # Update embeddings
        if self.cache_embeddings:
            new_embedding = self.embed([document])
            if self._corpus_embeddings is not None:
                self._corpus_embeddings = np.vstack(
                    [self._corpus_embeddings, new_embedding]
                )
            else:
                self._corpus_embeddings = new_embedding

        return idx

    def clear(self):
        """Clear the index."""
        self._corpus = []
        self._metadata = []
        self._corpus_embeddings = None

    @property
    def size(self) -> int:
        """Number of indexed documents."""
        return len(self._corpus)

    def get_stats(self) -> Dict[str, Any]:
        """Get retriever statistics."""
        return {
            "corpus_size": len(self._corpus),
            "embeddings_cached": self._corpus_embeddings is not None,
            "embedding_dim": (
                self._corpus_embeddings.shape[1]
                if self._corpus_embeddings is not None
                else 0
            ),
            "model": self.model_name if self.use_embeddings else "keyword_fallback",
            "use_embeddings": self.use_embeddings,
        }


# Convenience function
def create_retriever(model: str = None) -> EmbeddingRetriever:
    """Create an embedding retriever."""
    return EmbeddingRetriever(model_name=model)
