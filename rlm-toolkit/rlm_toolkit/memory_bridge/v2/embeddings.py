"""
Memory Bridge v2 — Embedding Service

Provides semantic embedding generation with lazy model loading
and keyword-based fallback.
Extracted from router.py for Single Responsibility.
"""

from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

# Try to import sentence-transformers
try:
    from sentence_transformers import SentenceTransformer

    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning(
        "sentence-transformers not installed. "
        "Semantic routing will use keyword fallback."
    )


class EmbeddingService:
    """Service for generating and caching embeddings."""

    DEFAULT_MODEL = "all-MiniLM-L6-v2"
    FALLBACK_MODEL = "paraphrase-MiniLM-L3-v2"

    def __init__(
        self,
        model_name: Optional[str] = None,
    ):
        self.model_name = model_name or self.DEFAULT_MODEL
        self._model = None
        self._dimension = None

    @property
    def model(self):
        """Lazy load the model."""
        if self._model is None:
            if not SENTENCE_TRANSFORMERS_AVAILABLE:
                raise RuntimeError("sentence-transformers not installed")
            try:
                self._model = SentenceTransformer(
                    self.model_name,
                )
                self._dimension = self._model.get_sentence_embedding_dimension()
                logger.info(
                    f"Loaded embedding model: "
                    f"{self.model_name} "
                    f"(dim={self._dimension})"
                )
            except Exception as e:
                logger.warning(
                    f"Failed to load " f"{self.model_name}, " f"trying fallback: {e}"
                )
                self._model = SentenceTransformer(
                    self.FALLBACK_MODEL,
                )
                self._dimension = self._model.get_sentence_embedding_dimension()
        return self._model

    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        if self._dimension is None:
            _ = self.model  # Trigger lazy load
        return self._dimension or 384

    def embed(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            return self._keyword_embedding(text)
        return self.model.encode(
            text,
            convert_to_numpy=True,
        ).tolist()

    def embed_batch(
        self,
        texts: List[str],
    ) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            return [self._keyword_embedding(t) for t in texts]
        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True,
        )
        return embeddings.tolist()

    def _keyword_embedding(
        self,
        text: str,
    ) -> List[float]:
        """Fallback keyword-based embedding."""
        words = text.lower().split()
        embedding = [0.0] * 128
        for i, word in enumerate(words[:128]):
            embedding[hash(word) % 128] += 1.0
        # Normalize
        norm = sum(x * x for x in embedding) ** 0.5
        if norm > 0:
            embedding = [x / norm for x in embedding]
        return embedding
