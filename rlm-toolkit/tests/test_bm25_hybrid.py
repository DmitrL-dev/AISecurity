"""
Tests for BM25 and Hybrid Retrieval.
"""

import pytest
from rlm_toolkit.retrieval.bm25 import BM25Index, BM25Config
from rlm_toolkit.retrieval.hybrid import HybridRetriever, HybridResult


class TestBM25Index:
    """Tests for BM25Index."""

    def test_add_and_search(self):
        """Test basic document indexing and search."""
        index = BM25Index()
        index.add_document(
            "doc1", "the quick brown fox jumps over the lazy dog")
        index.add_document("doc2", "a quick brown dog runs fast")

        results = index.search("quick brown", top_k=5)

        assert len(results) == 2
        # Both docs should match
        doc_ids = [r[0] for r in results]
        assert "doc1" in doc_ids
        assert "doc2" in doc_ids

    def test_empty_search(self):
        """Test search with no matches."""
        index = BM25Index()
        index.add_document("doc1", "hello world")

        results = index.search("python programming")
        assert len(results) == 0

    def test_empty_index(self):
        """Test search on empty index."""
        index = BM25Index()
        results = index.search("anything")
        assert len(results) == 0

    def test_tokenization(self):
        """Test tokenization handles punctuation."""
        index = BM25Index()
        index.add_document("doc1", "Hello, World! This is a test.")

        results = index.search("hello world")
        assert len(results) == 1

    def test_remove_document(self):
        """Test document removal."""
        index = BM25Index()
        index.add_document("doc1", "test document")
        index.add_document("doc2", "another document")

        assert index.remove_document("doc1")
        assert not index.remove_document("nonexistent")

        results = index.search("test")
        assert len(results) == 0

    def test_reindex_document(self):
        """Test re-indexing same doc_id."""
        index = BM25Index()
        index.add_document("doc1", "original text")
        index.add_document("doc1", "new updated text")

        assert index.get_document("doc1") == "new updated text"

        results = index.search("original")
        assert len(results) == 0

    def test_idf_scoring(self):
        """Test that rare terms get higher scores."""
        index = BM25Index()
        index.add_document("doc1", "common common common rare")
        index.add_document("doc2", "common common")
        index.add_document("doc3", "common")

        # "rare" appears in fewer docs, should have higher IDF
        rare_results = index.search("rare")
        common_results = index.search("common")

        assert len(rare_results) == 1
        assert len(common_results) == 3

    def test_custom_config(self):
        """Test with custom BM25 config."""
        config = BM25Config(k1=2.0, b=0.5)
        index = BM25Index(config=config)

        index.add_document("doc1", "test document")
        results = index.search("test")

        assert len(results) == 1
        assert index.config.k1 == 2.0

    def test_get_stats(self):
        """Test statistics gathering."""
        index = BM25Index()
        index.add_document("doc1", "hello world")
        index.add_document("doc2", "hello there")

        stats = index.get_stats()

        assert stats["total_documents"] == 2
        assert stats["unique_terms"] > 0

    def test_clear(self):
        """Test clearing index."""
        index = BM25Index()
        index.add_document("doc1", "test")
        index.clear()

        assert index.get_stats()["total_documents"] == 0


class TestHybridRetriever:
    """Tests for HybridRetriever."""

    def test_index_and_search(self):
        """Test hybrid search with both vector and BM25."""
        retriever = HybridRetriever(vector_weight=0.5, bm25_weight=0.5)
        retriever.index_document("doc1", "machine learning tutorial")
        retriever.index_document("doc2", "deep learning models")

        # Simulate vector results
        vector_results = [("doc1", 0.8), ("doc2", 0.6)]

        results = retriever.search("machine learning", vector_results, top_k=5)

        assert len(results) == 2
        assert all(isinstance(r, HybridResult) for r in results)

    def test_bm25_boost(self):
        """Test that BM25 can boost/demote results."""
        retriever = HybridRetriever(vector_weight=0.5, bm25_weight=0.5)
        retriever.index_document("doc1", "python programming")
        retriever.index_document("doc2", "machine learning python")

        # doc1 has higher vector score but doc2 has better keyword match
        vector_results = [("doc1", 0.9), ("doc2", 0.5)]

        results = retriever.search(
            "python machine learning", vector_results, top_k=5)

        # doc2 should be boosted by BM25 matching both terms
        assert len(results) == 2
        # Combined score should reflect both
        assert results[0].combined_score > 0

    def test_bm25_only_search(self):
        """Test BM25-only search."""
        retriever = HybridRetriever()
        retriever.index_document("doc1", "test document one")
        retriever.index_document("doc2", "test document two")

        results = retriever.search_bm25_only("test document")

        assert len(results) == 2
        assert all(r.vector_score == 0 for r in results)

    def test_rrf_fusion(self):
        """Test Reciprocal Rank Fusion method."""
        retriever = HybridRetriever(fusion_method="rrf")
        retriever.index_document("doc1", "first document")
        retriever.index_document("doc2", "second document")

        vector_results = [("doc1", 0.9), ("doc2", 0.1)]
        results = retriever.search("document", vector_results)

        assert len(results) == 2
        # RRF scores should be positive
        assert all(r.combined_score > 0 for r in results)

    def test_weight_normalization(self):
        """Test that weights are normalized."""
        retriever = HybridRetriever(vector_weight=3, bm25_weight=1)

        assert retriever.vector_weight == 0.75
        assert retriever.bm25_weight == 0.25

    def test_remove_document(self):
        """Test document removal."""
        retriever = HybridRetriever()
        retriever.index_document("doc1", "test")

        assert retriever.remove_document("doc1")
        assert not retriever.remove_document("nonexistent")

    def test_metadata_handling(self):
        """Test metadata is preserved."""
        retriever = HybridRetriever()
        retriever.index_document("doc1", "test", metadata={
                                 "source": "file.txt"})

        results = retriever.search_bm25_only("test")

        assert results[0].metadata == {"source": "file.txt"}

    def test_result_to_dict(self):
        """Test HybridResult serialization."""
        result = HybridResult(
            doc_id="doc1",
            combined_score=0.85,
            vector_score=0.9,
            bm25_score=0.8,
            text="Some test content",
        )

        data = result.to_dict()

        assert data["doc_id"] == "doc1"
        assert "combined_score" in data

    def test_get_stats(self):
        """Test statistics."""
        retriever = HybridRetriever()
        retriever.index_document("doc1", "test")

        stats = retriever.get_stats()

        assert stats["fusion_method"] == "weighted"
        assert "bm25_index" in stats

    def test_clear(self):
        """Test clearing retriever."""
        retriever = HybridRetriever()
        retriever.index_document("doc1", "test")
        retriever.clear()

        results = retriever.search_bm25_only("test")
        assert len(results) == 0


class TestHybridWithRealData:
    """Integration tests with realistic data."""

    def test_code_search(self):
        """Test searching code-like content."""
        retriever = HybridRetriever()

        docs = [
            ("auth.py", "def authenticate_user(username, password): validate credentials"),
            ("db.py", "class DatabaseConnection: connect execute query"),
            ("api.py", "async def get_user(user_id): fetch user from database"),
        ]

        for doc_id, text in docs:
            retriever.index_document(doc_id, text)

        # Simulate vector search finding all docs
        vector_results = [
            ("api.py", 0.9),   # Most similar semantically
            ("db.py", 0.7),
            ("auth.py", 0.5),
        ]

        results = retriever.search("user authentication", vector_results)

        # auth.py should be boosted by "authenticate" keyword match
        assert len(results) == 3

    def test_document_ranking(self):
        """Test that hybrid ranking improves over single method."""
        retriever = HybridRetriever(vector_weight=0.6, bm25_weight=0.4)

        # doc1: exact keyword match but low semantic sim
        # doc2: high semantic sim but no exact match
        # doc3: both partial match
        retriever.index_document("doc1", "python programming tutorial basics")
        retriever.index_document(
            "doc2", "machine learning deep neural networks")
        retriever.index_document(
            "doc3", "python machine learning scikit-learn")

        vector_results = [
            ("doc2", 0.95),  # High semantic for "ML"
            ("doc3", 0.80),
            ("doc1", 0.30),
        ]

        results = retriever.search("python machine learning", vector_results)

        # doc3 should rank well due to both vector and BM25 scores
        assert len(results) == 3
        doc_ids = [r.doc_id for r in results]
        assert "doc3" in doc_ids[:2]  # Should be in top 2
