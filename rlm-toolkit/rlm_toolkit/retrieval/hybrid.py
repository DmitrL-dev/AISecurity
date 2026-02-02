"""
Hybrid Retrieval: Vector + BM25 Search Fusion.

Combines semantic (vector) search with keyword (BM25) search for 
superior retrieval quality. Inspired by OpenClaw's mergeHybridResults.

Example:
    >>> hybrid = HybridRetriever(vector_weight=0.7, bm25_weight=0.3)
    >>> hybrid.index_document("doc1", "machine learning fundamentals")
    >>> results = hybrid.search("ML basics", vector_results=[("doc1", 0.85)])
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any
from .bm25 import BM25Index, BM25Config


@dataclass
class HybridResult:
    """A search result with hybrid scoring.

    Attributes:
        doc_id: Document identifier
        combined_score: Weighted combination of vector and BM25 scores
        vector_score: Original vector similarity score (0-1)
        bm25_score: Normalized BM25 score (0-1)
        text: Document text (if available)
        metadata: Additional document metadata
    """
    doc_id: str
    combined_score: float
    vector_score: float
    bm25_score: float
    text: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict:
        """Serialize result."""
        return {
            "doc_id": self.doc_id,
            "combined_score": round(self.combined_score, 4),
            "vector_score": round(self.vector_score, 4),
            "bm25_score": round(self.bm25_score, 4),
            "text": self.text[:200] + "..." if self.text and len(self.text) > 200 else self.text,
        }


class HybridRetriever:
    """Hybrid retrieval combining vector and BM25 search.

    Uses Reciprocal Rank Fusion (RRF) or weighted combination to merge
    results from semantic and keyword searches.

    Example:
        >>> retriever = HybridRetriever()
        >>> retriever.index_document("doc1", "Python programming tutorial")
        >>> retriever.index_document("doc2", "Machine learning with Python")
        >>> 
        >>> # Assume you have vector search results
        >>> vector_results = [("doc2", 0.9), ("doc1", 0.7)]
        >>> 
        >>> results = retriever.search("Python ML", vector_results)
        >>> for r in results:
        ...     print(f"{r.doc_id}: {r.combined_score:.3f}")
    """

    def __init__(
        self,
        vector_weight: float = 0.7,
        bm25_weight: float = 0.3,
        bm25_config: Optional[BM25Config] = None,
        normalize_scores: bool = True,
        rrf_k: int = 60,
        fusion_method: str = "weighted",  # "weighted" or "rrf"
    ):
        """Initialize hybrid retriever.

        Args:
            vector_weight: Weight for vector similarity scores
            bm25_weight: Weight for BM25 scores
            bm25_config: Configuration for BM25 index
            normalize_scores: Whether to normalize scores to 0-1 range
            rrf_k: RRF constant (only used if fusion_method="rrf")
            fusion_method: "weighted" for linear combination, "rrf" for Reciprocal Rank Fusion
        """
        if vector_weight + bm25_weight != 1.0:
            # Normalize weights
            total = vector_weight + bm25_weight
            vector_weight = vector_weight / total
            bm25_weight = bm25_weight / total

        self.vector_weight = vector_weight
        self.bm25_weight = bm25_weight
        self.normalize_scores = normalize_scores
        self.rrf_k = rrf_k
        self.fusion_method = fusion_method

        self.bm25_index = BM25Index(config=bm25_config)
        self._metadata: Dict[str, Dict[str, Any]] = {}

    def index_document(
        self,
        doc_id: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Index a document for BM25 search.

        Note: Vector indexing should be done separately with your vector store.

        Args:
            doc_id: Unique document identifier
            text: Document text content
            metadata: Optional document metadata
        """
        self.bm25_index.add_document(doc_id, text)
        if metadata:
            self._metadata[doc_id] = metadata

    def remove_document(self, doc_id: str) -> bool:
        """Remove a document from the index.

        Args:
            doc_id: Document ID to remove

        Returns:
            True if removed
        """
        self._metadata.pop(doc_id, None)
        return self.bm25_index.remove_document(doc_id)

    def _normalize_bm25_scores(
        self,
        scores: List[Tuple[str, float]]
    ) -> Dict[str, float]:
        """Normalize BM25 scores to 0-1 range.

        Args:
            scores: List of (doc_id, score) from BM25

        Returns:
            Dict mapping doc_id to normalized score
        """
        if not scores:
            return {}

        max_score = max(s for _, s in scores)
        if max_score == 0:
            return {doc_id: 0.0 for doc_id, _ in scores}

        return {doc_id: score / max_score for doc_id, score in scores}

    def _weighted_fusion(
        self,
        query: str,
        vector_results: List[Tuple[str, float]],
        top_k: int,
    ) -> List[HybridResult]:
        """Combine results using weighted linear fusion.

        Args:
            query: Search query
            vector_results: (doc_id, score) from vector search
            top_k: Maximum results

        Returns:
            Merged HybridResult list
        """
        # Get BM25 results
        bm25_results = self.bm25_index.search(query, top_k=top_k * 2)

        # Normalize BM25 scores
        bm25_scores = self._normalize_bm25_scores(bm25_results)

        # Build vector score lookup
        vector_scores = {doc_id: score for doc_id, score in vector_results}

        # Collect all candidate doc IDs
        all_doc_ids = set(vector_scores.keys()) | set(bm25_scores.keys())

        # Calculate combined scores
        results: List[HybridResult] = []
        for doc_id in all_doc_ids:
            v_score = vector_scores.get(doc_id, 0.0)
            b_score = bm25_scores.get(doc_id, 0.0)

            combined = (self.vector_weight * v_score) + \
                (self.bm25_weight * b_score)

            results.append(HybridResult(
                doc_id=doc_id,
                combined_score=combined,
                vector_score=v_score,
                bm25_score=b_score,
                text=self.bm25_index.get_document(doc_id),
                metadata=self._metadata.get(doc_id),
            ))

        # Sort by combined score
        results.sort(key=lambda r: r.combined_score, reverse=True)

        return results[:top_k]

    def _rrf_fusion(
        self,
        query: str,
        vector_results: List[Tuple[str, float]],
        top_k: int,
    ) -> List[HybridResult]:
        """Combine results using Reciprocal Rank Fusion.

        RRF score = sum(1 / (k + rank)) across all rankings

        Args:
            query: Search query
            vector_results: (doc_id, score) from vector search
            top_k: Maximum results

        Returns:
            Merged HybridResult list
        """
        bm25_results = self.bm25_index.search(query, top_k=top_k * 2)

        # Build rank lookups (1-indexed)
        vector_ranks = {doc_id: i + 1 for i,
                        (doc_id, _) in enumerate(vector_results)}
        bm25_ranks = {doc_id: i + 1 for i,
                      (doc_id, _) in enumerate(bm25_results)}

        # Score lookups for output
        vector_scores = {doc_id: score for doc_id, score in vector_results}
        bm25_scores = self._normalize_bm25_scores(bm25_results)

        # All candidates
        all_doc_ids = set(vector_ranks.keys()) | set(bm25_ranks.keys())

        # Calculate RRF scores
        results: List[HybridResult] = []
        k = self.rrf_k

        for doc_id in all_doc_ids:
            rrf_score = 0.0

            if doc_id in vector_ranks:
                rrf_score += self.vector_weight / (k + vector_ranks[doc_id])
            if doc_id in bm25_ranks:
                rrf_score += self.bm25_weight / (k + bm25_ranks[doc_id])

            results.append(HybridResult(
                doc_id=doc_id,
                combined_score=rrf_score,
                vector_score=vector_scores.get(doc_id, 0.0),
                bm25_score=bm25_scores.get(doc_id, 0.0),
                text=self.bm25_index.get_document(doc_id),
                metadata=self._metadata.get(doc_id),
            ))

        # Sort by RRF score
        results.sort(key=lambda r: r.combined_score, reverse=True)

        return results[:top_k]

    def search(
        self,
        query: str,
        vector_results: List[Tuple[str, float]],
        top_k: int = 10,
    ) -> List[HybridResult]:
        """Perform hybrid search combining vector and BM25 results.

        Args:
            query: Search query string
            vector_results: Results from vector search as (doc_id, score) pairs
            top_k: Maximum number of results

        Returns:
            List of HybridResult with combined scores
        """
        if self.fusion_method == "rrf":
            return self._rrf_fusion(query, vector_results, top_k)
        else:
            return self._weighted_fusion(query, vector_results, top_k)

    def search_bm25_only(
        self,
        query: str,
        top_k: int = 10
    ) -> List[HybridResult]:
        """Search using BM25 only (no vector results required).

        Useful for testing or when vector search is unavailable.

        Args:
            query: Search query
            top_k: Maximum results

        Returns:
            List of HybridResult with bm25_score only
        """
        bm25_results = self.bm25_index.search(query, top_k)
        bm25_scores = self._normalize_bm25_scores(bm25_results)

        results = []
        for doc_id, raw_score in bm25_results:
            results.append(HybridResult(
                doc_id=doc_id,
                combined_score=bm25_scores[doc_id],
                vector_score=0.0,
                bm25_score=bm25_scores[doc_id],
                text=self.bm25_index.get_document(doc_id),
                metadata=self._metadata.get(doc_id),
            ))

        return results

    def get_stats(self) -> Dict:
        """Get retriever statistics."""
        return {
            "fusion_method": self.fusion_method,
            "vector_weight": self.vector_weight,
            "bm25_weight": self.bm25_weight,
            "bm25_index": self.bm25_index.get_stats(),
        }

    def clear(self) -> None:
        """Clear all indexed documents."""
        self.bm25_index.clear()
        self._metadata.clear()
