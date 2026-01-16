"""
Episodic Memory
===============

EM-LLM-inspired episodic memory with similarity + temporal retrieval.
Based on the EM-LLM architecture for infinite context.
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from rlm_toolkit.memory.base import Memory, MemoryEntry


def _simple_similarity(query: str, content: str) -> float:
    """Simple word overlap similarity (fallback when no embeddings).
    
    Uses Jaccard similarity on word sets.
    """
    query_words = set(query.lower().split())
    content_words = set(content.lower().split())
    
    if not query_words or not content_words:
        return 0.0
    
    intersection = query_words & content_words
    union = query_words | content_words
    
    return len(intersection) / len(union)


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """Cosine similarity between vectors."""
    if len(a) != len(b):
        return 0.0
    
    dot_product = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
    
    return dot_product / (norm_a * norm_b)


class EpisodicMemory(Memory):
    """EM-LLM-inspired episodic memory system.
    
    Combines similarity-based and temporal retrieval:
    - k_similarity: Top-k by semantic similarity
    - k_contiguity: Surrounding entries for context
    
    Example:
        >>> def embed(text):
        ...     return openai.embed(text)  # Your embedding function
        >>> memory = EpisodicMemory(embed_fn=embed, k_similarity=5, k_contiguity=2)
        >>> memory.add("Paris is the capital of France")
        >>> results = memory.retrieve("What is the capital of France?")
    
    Attributes:
        k_similarity: Number of similar entries to retrieve
        k_contiguity: Surrounding context entries per match
        embed_fn: Function to generate embeddings
    """
    
    def __init__(
        self,
        embed_fn: Optional[Callable[[str], List[float]]] = None,
        k_similarity: int = 5,
        k_contiguity: int = 2,
        max_entries: int = 10000,
    ):
        """Initialize episodic memory.
        
        Args:
            embed_fn: Function to generate embeddings (optional)
            k_similarity: Number of similar entries to retrieve
            k_contiguity: Surrounding entries per match (before and after)
            max_entries: Maximum entries (oldest removed when exceeded)
        """
        self.embed_fn = embed_fn
        self.k_similarity = k_similarity
        self.k_contiguity = k_contiguity
        self.max_entries = max_entries
        
        self._entries: List[MemoryEntry] = []
    
    def add(self, content: str, metadata: Optional[Dict] = None) -> MemoryEntry:
        """Add entry with optional embedding."""
        embedding = None
        if self.embed_fn:
            try:
                embedding = self.embed_fn(content)
            except Exception:
                pass  # Fallback to text similarity
        
        entry = MemoryEntry(
            content=content,
            metadata=metadata or {},
            embedding=embedding,
        )
        
        self._entries.append(entry)
        
        # Trim if over limit
        if len(self._entries) > self.max_entries:
            self._entries = self._entries[-self.max_entries:]
        
        return entry
    
    def retrieve(self, query: str, k: Optional[int] = None) -> List[MemoryEntry]:
        """Retrieve using similarity + contiguity.
        
        1. Find k_similarity most similar entries
        2. For each, include k_contiguity surrounding entries
        3. Deduplicate and sort by score
        """
        if not self._entries:
            return []
        
        k_sim = k if k is not None else self.k_similarity
        
        # Calculate similarity scores
        query_embedding = None
        if self.embed_fn:
            try:
                query_embedding = self.embed_fn(query)
            except Exception:
                pass
        
        scored_entries: List[Tuple[int, float]] = []
        
        for i, entry in enumerate(self._entries):
            if query_embedding and entry.embedding:
                score = _cosine_similarity(query_embedding, entry.embedding)
            else:
                score = _simple_similarity(query, entry.content)
            
            scored_entries.append((i, score))
        
        # Get top k by similarity
        scored_entries.sort(key=lambda x: -x[1])
        top_indices = [idx for idx, _ in scored_entries[:k_sim]]
        
        # Expand with contiguity
        result_indices = set()
        for idx in top_indices:
            # Add surrounding entries
            start = max(0, idx - self.k_contiguity)
            end = min(len(self._entries), idx + self.k_contiguity + 1)
            for i in range(start, end):
                result_indices.add(i)
        
        # Build result with scores
        results = []
        for idx in sorted(result_indices):
            entry = self._entries[idx]
            # Copy entry with score
            result_entry = MemoryEntry(
                content=entry.content,
                metadata=entry.metadata,
                timestamp=entry.timestamp,
                embedding=entry.embedding,
                score=dict(scored_entries).get(idx, 0.0),
            )
            results.append(result_entry)
        
        # Sort by score descending
        results.sort(key=lambda e: -(e.score or 0))
        
        return results
    
    def clear(self) -> int:
        """Clear all entries."""
        count = len(self._entries)
        self._entries.clear()
        return count
    
    @property
    def size(self) -> int:
        return len(self._entries)
    
    def get_by_timerange(
        self,
        start: datetime,
        end: Optional[datetime] = None,
    ) -> List[MemoryEntry]:
        """Get entries within time range."""
        end = end or datetime.now()
        return [
            e for e in self._entries
            if start <= e.timestamp <= end
        ]
    
    def summary_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        if not self._entries:
            return {'size': 0, 'embeddings': 0}
        
        with_embeddings = sum(1 for e in self._entries if e.embedding)
        
        return {
            'size': len(self._entries),
            'embeddings': with_embeddings,
            'oldest': self._entries[0].timestamp.isoformat(),
            'newest': self._entries[-1].timestamp.isoformat(),
        }
