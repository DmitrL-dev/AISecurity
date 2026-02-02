"""
BM25 (Okapi BM25) Ranking for Keyword Search.

Implements the BM25 ranking algorithm for keyword-based document retrieval.
Complements vector search for hybrid retrieval.

Reference: Robertson et al., "The Probabilistic Relevance Framework: BM25 and Beyond"

Example:
    >>> index = BM25Index()
    >>> index.add_document("doc1", "the quick brown fox jumps")
    >>> index.add_document("doc2", "lazy dog sleeps")
    >>> results = index.search("quick fox", top_k=5)
    >>> print(results[0])  # (doc_id, score)
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict


@dataclass
class BM25Config:
    """Configuration for BM25 ranking.

    Attributes:
        k1: Term saturation parameter (1.2-2.0 typical)
        b: Length normalization (0 = no normalization, 1 = full)
        epsilon: Floor value for IDF to prevent negative scores
    """
    k1: float = 1.5
    b: float = 0.75
    epsilon: float = 0.25


class BM25Index:
    """Okapi BM25 ranking index for keyword search.

    Supports:
    - Document indexing with term frequency tracking
    - IDF (Inverse Document Frequency) calculation
    - Configurable k1 and b parameters
    - Incremental document addition

    Example:
        >>> index = BM25Index()
        >>> index.add_document("doc1", "machine learning is great")
        >>> index.add_document("doc2", "deep learning models")
        >>> results = index.search("learning models", top_k=2)
        >>> for doc_id, score in results:
        ...     print(f"{doc_id}: {score:.4f}")
    """

    def __init__(self, config: Optional[BM25Config] = None):
        """Initialize BM25 index.

        Args:
            config: BM25 configuration parameters
        """
        self.config = config or BM25Config()

        # Document storage
        self._documents: Dict[str, str] = {}  # doc_id -> original text
        self._doc_lengths: Dict[str, int] = {}  # doc_id -> token count

        # Inverted index: term -> {doc_id -> term_frequency}
        self._term_freqs: Dict[str, Dict[str, int]] = defaultdict(dict)

        # Document frequency: term -> number of docs containing term
        self._doc_freqs: Dict[str, int] = defaultdict(int)

        # Statistics
        self._total_docs: int = 0
        self._avg_doc_len: float = 0.0
        self._total_tokens: int = 0

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into lowercase words.

        Simple whitespace + punctuation tokenizer.
        Override for language-specific tokenization.

        Args:
            text: Input text

        Returns:
            List of lowercase tokens
        """
        # Remove punctuation and lowercase
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        # Split on whitespace and filter empty
        tokens = [t.strip() for t in text.split() if t.strip()]
        return tokens

    def add_document(self, doc_id: str, text: str) -> None:
        """Index a document.

        Args:
            doc_id: Unique document identifier
            text: Document text content
        """
        # Handle re-indexing
        if doc_id in self._documents:
            self.remove_document(doc_id)

        tokens = self._tokenize(text)
        doc_len = len(tokens)

        # Store document
        self._documents[doc_id] = text
        self._doc_lengths[doc_id] = doc_len

        # Count term frequencies for this document
        term_counts: Dict[str, int] = defaultdict(int)
        for token in tokens:
            term_counts[token] += 1

        # Update inverted index and document frequencies
        for term, count in term_counts.items():
            self._term_freqs[term][doc_id] = count
            self._doc_freqs[term] += 1

        # Update statistics
        self._total_docs += 1
        self._total_tokens += doc_len
        self._avg_doc_len = self._total_tokens / \
            self._total_docs if self._total_docs > 0 else 0.0

    def remove_document(self, doc_id: str) -> bool:
        """Remove a document from the index.

        Args:
            doc_id: Document ID to remove

        Returns:
            True if removed, False if not found
        """
        if doc_id not in self._documents:
            return False

        doc_len = self._doc_lengths[doc_id]

        # Remove from inverted index
        terms_to_clean = []
        for term, doc_freqs in self._term_freqs.items():
            if doc_id in doc_freqs:
                del doc_freqs[doc_id]
                self._doc_freqs[term] -= 1
                if self._doc_freqs[term] <= 0:
                    terms_to_clean.append(term)

        # Clean up empty terms
        for term in terms_to_clean:
            del self._term_freqs[term]
            del self._doc_freqs[term]

        # Remove document
        del self._documents[doc_id]
        del self._doc_lengths[doc_id]

        # Update statistics
        self._total_docs -= 1
        self._total_tokens -= doc_len
        self._avg_doc_len = self._total_tokens / \
            self._total_docs if self._total_docs > 0 else 0.0

        return True

    def _idf(self, term: str) -> float:
        """Calculate IDF for a term.

        Uses smoothed IDF: log((N - n + 0.5) / (n + 0.5) + 1)

        Args:
            term: The term to calculate IDF for

        Returns:
            IDF score (minimum of epsilon to prevent negative)
        """
        n = self._doc_freqs.get(term, 0)
        N = self._total_docs

        if n == 0:
            return 0.0

        # Standard BM25 IDF formula
        idf = math.log((N - n + 0.5) / (n + 0.5) + 1)

        # Apply epsilon floor
        return max(idf, self.config.epsilon)

    def _score_document(self, doc_id: str, query_terms: List[str]) -> float:
        """Calculate BM25 score for a document given query terms.

        Args:
            doc_id: Document ID to score
            query_terms: Tokenized query terms

        Returns:
            BM25 score
        """
        score = 0.0
        doc_len = self._doc_lengths.get(doc_id, 0)

        if doc_len == 0:
            return 0.0

        # Length normalization factor
        k1 = self.config.k1
        b = self.config.b
        avgdl = self._avg_doc_len

        for term in query_terms:
            if term not in self._term_freqs:
                continue

            tf = self._term_freqs[term].get(doc_id, 0)
            if tf == 0:
                continue

            idf = self._idf(term)

            # BM25 term score formula
            # score = IDF * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * dl/avgdl))
            numerator = tf * (k1 + 1)
            denominator = tf + k1 * \
                (1 - b + b * (doc_len / avgdl if avgdl > 0 else 1))

            score += idf * (numerator / denominator)

        return score

    def search(self, query: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """Search for documents matching query.

        Args:
            query: Search query string
            top_k: Maximum number of results

        Returns:
            List of (doc_id, score) tuples, sorted by score descending
        """
        if self._total_docs == 0:
            return []

        query_terms = self._tokenize(query)
        if not query_terms:
            return []

        # Find candidate documents (contain at least one query term)
        candidates: Set[str] = set()
        for term in query_terms:
            if term in self._term_freqs:
                candidates.update(self._term_freqs[term].keys())

        if not candidates:
            return []

        # Score all candidates
        scores: List[Tuple[str, float]] = []
        for doc_id in candidates:
            score = self._score_document(doc_id, query_terms)
            if score > 0:
                scores.append((doc_id, score))

        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)

        return scores[:top_k]

    def get_document(self, doc_id: str) -> Optional[str]:
        """Get original document text.

        Args:
            doc_id: Document ID

        Returns:
            Document text or None if not found
        """
        return self._documents.get(doc_id)

    def get_stats(self) -> Dict:
        """Get index statistics.

        Returns:
            Dictionary with index stats
        """
        return {
            "total_documents": self._total_docs,
            "total_tokens": self._total_tokens,
            "avg_doc_length": round(self._avg_doc_len, 2),
            "unique_terms": len(self._term_freqs),
            "config": {
                "k1": self.config.k1,
                "b": self.config.b,
                "epsilon": self.config.epsilon,
            }
        }

    def clear(self) -> None:
        """Clear the entire index."""
        self._documents.clear()
        self._doc_lengths.clear()
        self._term_freqs.clear()
        self._doc_freqs.clear()
        self._total_docs = 0
        self._avg_doc_len = 0.0
        self._total_tokens = 0
