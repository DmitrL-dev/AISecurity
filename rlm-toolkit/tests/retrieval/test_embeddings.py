"""Tests for Embedding-Based Retrieval."""

import pytest
import numpy as np

from rlm_toolkit.retrieval import EmbeddingRetriever, RetrievalResult, create_retriever


class TestEmbeddingRetriever:
    """Tests for EmbeddingRetriever."""

    @pytest.fixture
    def retriever(self):
        """Create retriever with keyword fallback."""
        return EmbeddingRetriever(use_embeddings=False)

    def test_create_retriever(self):
        """Test creating retriever."""
        retriever = create_retriever()
        assert retriever is not None

    def test_index_corpus(self, retriever):
        """Test indexing a corpus."""
        corpus = [
            "Python is a programming language",
            "JavaScript is for web development",
            "Machine learning uses data",
        ]
        retriever.index(corpus)

        assert retriever.size == 3

    def test_search_basic(self, retriever):
        """Test basic search."""
        corpus = [
            "Paris is the capital of France",
            "Berlin is the capital of Germany",
            "Tokyo is the capital of Japan",
        ]
        retriever.index(corpus)

        results = retriever.search("capital of France")

        assert len(results) > 0
        assert results[0].content == "Paris is the capital of France"

    def test_search_returns_results(self, retriever):
        """Test search returns RetrievalResult objects."""
        retriever.index(["test document"])
        results = retriever.search("test")

        assert len(results) > 0
        assert isinstance(results[0], RetrievalResult)
        assert results[0].score > 0

    def test_search_top_k(self, retriever):
        """Test top_k limit."""
        corpus = [f"document {i}" for i in range(10)]
        retriever.index(corpus)

        results = retriever.search("document", top_k=3)

        assert len(results) <= 3

    def test_add_document(self, retriever):
        """Test adding document to index."""
        retriever.index(["initial document"])
        idx = retriever.add("new document")

        assert idx == 1
        assert retriever.size == 2

    def test_clear_index(self, retriever):
        """Test clearing index."""
        retriever.index(["a", "b", "c"])
        retriever.clear()

        assert retriever.size == 0

    def test_stats(self, retriever):
        """Test getting stats."""
        retriever.index(["test"])
        stats = retriever.get_stats()

        assert stats["corpus_size"] == 1
        assert "model" in stats

    def test_metadata(self, retriever):
        """Test metadata storage."""
        corpus = ["document"]
        metadata = [{"source": "test.py", "line": 10}]
        retriever.index(corpus, metadata=metadata)

        results = retriever.search("document")

        assert results[0].metadata["source"] == "test.py"

    def test_threshold(self, retriever):
        """Test similarity threshold."""
        retriever.index(["apple", "banana", "car"])

        # High threshold should filter low-scoring results
        results = retriever.search("fruit", threshold=0.5)

        # Results should be filtered by threshold
        for r in results:
            assert r.score >= 0.5

    def test_embed(self, retriever):
        """Test embedding generation."""
        embeddings = retriever.embed(["test text"])

        assert isinstance(embeddings, np.ndarray)
        assert embeddings.shape[0] == 1


class TestEmbeddingRetrieverWithSentenceTransformers:
    """Tests that require sentence-transformers (skip if not installed)."""

    @pytest.fixture
    def retriever(self):
        """Create retriever with embeddings if available."""
        r = EmbeddingRetriever()
        if not r.use_embeddings:
            pytest.skip("sentence-transformers not installed")
        return r

    def test_semantic_search(self, retriever):
        """Test semantic search with real embeddings."""
        corpus = [
            "The cat sat on the mat",
            "Dogs are loyal pets",
            "I love programming in Python",
            "Machine learning is fascinating",
        ]
        retriever.index(corpus)

        results = retriever.search("feline on a rug")

        # Semantic search should find "cat on mat" even without exact words
        assert len(results) > 0
        # First result should be about the cat
        assert "cat" in results[0].content.lower()
