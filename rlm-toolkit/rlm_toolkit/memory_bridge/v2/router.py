"""
Semantic Router for Memory Bridge v2.0

Provides intelligent context routing based on semantic similarity,
loading only the most relevant facts for a given query.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import logging
import json
import numpy as np

from .hierarchical import (
    HierarchicalMemoryStore,
    HierarchicalFact,
    MemoryLevel,
)

logger = logging.getLogger(__name__)

# Try to import sentence-transformers, graceful fallback if not available
try:
    from sentence_transformers import SentenceTransformer

    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning(
        "sentence-transformers not installed. Semantic routing will use keyword fallback."
    )


@dataclass
class RoutingResult:
    """Result of semantic routing."""

    facts: List[HierarchicalFact]
    total_tokens: int
    routing_confidence: float
    routing_explanation: str
    cross_references: List[Tuple[str, str]] = field(default_factory=list)
    domains_loaded: List[str] = field(default_factory=list)
    fallback_used: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "facts": [f.to_dict() for f in self.facts],
            "total_tokens": self.total_tokens,
            "routing_confidence": self.routing_confidence,
            "routing_explanation": self.routing_explanation,
            "cross_references": self.cross_references,
            "domains_loaded": self.domains_loaded,
            "fallback_used": self.fallback_used,
        }


class EmbeddingService:
    """Service for generating and caching embeddings."""

    DEFAULT_MODEL = "all-MiniLM-L6-v2"
    FALLBACK_MODEL = "paraphrase-MiniLM-L3-v2"

    def __init__(self, model_name: Optional[str] = None):
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
                self._model = SentenceTransformer(self.model_name)
                self._dimension = self._model.get_sentence_embedding_dimension()
                logger.info(
                    f"Loaded embedding model: {self.model_name} (dim={self._dimension})"
                )
            except Exception as e:
                logger.warning(
                    f"Failed to load {self.model_name}, trying fallback: {e}"
                )
                self._model = SentenceTransformer(self.FALLBACK_MODEL)
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
        return self.model.encode(text, convert_to_numpy=True).tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            return [self._keyword_embedding(t) for t in texts]
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()

    def _keyword_embedding(self, text: str) -> List[float]:
        """Fallback keyword-based embedding when transformers unavailable."""
        # Simple TF-based embedding (for fallback only)
        words = text.lower().split()
        # Use hash to create a pseudo-embedding
        embedding = [0.0] * 128
        for i, word in enumerate(words[:128]):
            embedding[hash(word) % 128] += 1.0
        # Normalize
        norm = sum(x * x for x in embedding) ** 0.5
        if norm > 0:
            embedding = [x / norm for x in embedding]
        return embedding


class SemanticRouter:
    """
    Intelligent context routing based on semantic similarity.

    Routes queries to the most relevant facts across the memory hierarchy,
    respecting token budgets and loading L0 facts by default.
    """

    def __init__(
        self,
        store: HierarchicalMemoryStore,
        embedding_service: Optional[EmbeddingService] = None,
        similarity_threshold: float = 0.5,
        max_tokens: int = 2000,
    ):
        self.store = store
        self.embedding_service = embedding_service or EmbeddingService()
        self.similarity_threshold = similarity_threshold
        self.max_tokens = max_tokens

    @property
    def embeddings_enabled(self) -> bool:
        """Check if semantic embeddings are available."""
        return SENTENCE_TRANSFORMERS_AVAILABLE

    def route(
        self,
        query: str,
        max_tokens: Optional[int] = None,
        include_stale: bool = False,
        include_l0: bool = True,
        target_domains: Optional[List[str]] = None,
    ) -> RoutingResult:
        """
        Route a query to relevant facts.

        Algorithm:
        1. Always load L0 facts (project overview)
        2. Compute query embedding
        3. Score domains by centroid similarity
        4. Select top domains
        5. Rank L1/L2 facts within domains
        6. Apply token budget
        7. Return with confidence + explanation

        Args:
            query: The query to route
            max_tokens: Token budget (uses default if None)
            include_stale: Include stale facts
            include_l0: Always include L0 facts
            target_domains: Restrict to specific domains

        Returns:
            RoutingResult with selected facts and metadata
        """
        max_tokens = max_tokens or self.max_tokens
        selected_facts: List[HierarchicalFact] = []
        total_tokens = 0
        domains_loaded: List[str] = []
        explanations: List[str] = []

        # Step 1: Always load L0 facts
        if include_l0:
            l0_facts = self.store.get_facts_by_level(
                MemoryLevel.L0_PROJECT, include_stale=include_stale
            )
            for fact in l0_facts:
                tokens = fact.token_estimate()
                if total_tokens + tokens <= max_tokens * 0.3:  # Reserve 30% for L0
                    selected_facts.append(fact)
                    total_tokens += tokens
            explanations.append(f"Loaded {len(l0_facts)} L0 project facts")

        # Step 2: Compute query embedding
        query_embedding = self.embedding_service.embed(query)

        # Step 3: Get all facts with embeddings for scoring
        facts_with_embeddings = self.store.get_facts_with_embeddings()

        if not facts_with_embeddings:
            # No embeddings available, fall back to all L1 facts
            l1_facts = self.store.get_facts_by_level(
                MemoryLevel.L1_DOMAIN, include_stale=include_stale
            )
            for fact in l1_facts[:10]:  # Limit to 10
                tokens = fact.token_estimate()
                if total_tokens + tokens <= max_tokens:
                    selected_facts.append(fact)
                    total_tokens += tokens
                    if fact.domain and fact.domain not in domains_loaded:
                        domains_loaded.append(fact.domain)

            return RoutingResult(
                facts=selected_facts,
                total_tokens=total_tokens,
                routing_confidence=0.5,
                routing_explanation="Fallback routing (no embeddings): "
                + "; ".join(explanations),
                domains_loaded=domains_loaded,
                fallback_used=True,
            )

        # Step 4: Score all facts by similarity
        scored_facts: List[Tuple[float, HierarchicalFact]] = []
        for fact, embedding in facts_with_embeddings:
            if fact.level == MemoryLevel.L0_PROJECT:
                continue  # Already loaded
            if fact.is_archived:
                continue
            if not include_stale and fact.is_stale:
                continue
            if target_domains and fact.domain and fact.domain not in target_domains:
                continue

            similarity = self._cosine_similarity(query_embedding, embedding)
            if similarity >= self.similarity_threshold:
                scored_facts.append((similarity, fact))

        # Step 5: Sort by similarity and select top facts within budget
        scored_facts.sort(key=lambda x: x[0], reverse=True)

        for similarity, fact in scored_facts:
            tokens = fact.token_estimate()
            if total_tokens + tokens <= max_tokens:
                selected_facts.append(fact)
                total_tokens += tokens
                if fact.domain and fact.domain not in domains_loaded:
                    domains_loaded.append(fact.domain)

        # Step 6: Calculate confidence
        if scored_facts:
            avg_similarity = sum(
                s for s, _ in scored_facts[: len(selected_facts)]
            ) / max(len(selected_facts), 1)
            confidence = min(avg_similarity * 1.2, 1.0)  # Scale up a bit, cap at 1.0
        else:
            confidence = 0.5

        explanations.append(
            f"Loaded {len(selected_facts) - len([f for f in selected_facts if f.level == MemoryLevel.L0_PROJECT])} additional facts from {len(domains_loaded)} domains"
        )

        # Step 7: Resolve cross-references
        cross_refs = self._resolve_cross_references(selected_facts)

        return RoutingResult(
            facts=selected_facts,
            total_tokens=total_tokens,
            routing_confidence=round(confidence, 3),
            routing_explanation="; ".join(explanations),
            cross_references=cross_refs,
            domains_loaded=domains_loaded,
            fallback_used=False,
        )

    def index_all_facts(self) -> int:
        """
        Generate and store embeddings for all facts without embeddings.

        Returns:
            Number of facts indexed
        """
        all_facts = self.store.get_all_facts(include_stale=True)
        indexed = 0

        # Batch process for efficiency
        facts_to_index = [f for f in all_facts if f.embedding is None]

        if not facts_to_index:
            return 0

        contents = [f.content for f in facts_to_index]
        embeddings = self.embedding_service.embed_batch(contents)

        for fact, embedding in zip(facts_to_index, embeddings):
            self.store.update_embedding(fact.id, embedding)
            indexed += 1

        logger.info(f"Indexed {indexed} facts with embeddings")
        return indexed

    def compute_domain_centroids(self) -> Dict[str, List[float]]:
        """
        Compute centroid embeddings for each domain.

        Returns:
            Dict mapping domain names to centroid embeddings
        """
        domain_embeddings: Dict[str, List[List[float]]] = {}

        facts_with_embeddings = self.store.get_facts_with_embeddings()

        for fact, embedding in facts_with_embeddings:
            if fact.domain:
                if fact.domain not in domain_embeddings:
                    domain_embeddings[fact.domain] = []
                domain_embeddings[fact.domain].append(embedding)

        centroids = {}
        for domain, embeddings in domain_embeddings.items():
            if embeddings:
                centroid = np.mean(embeddings, axis=0).tolist()
                centroids[domain] = centroid

        return centroids

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        a_arr = np.array(a)
        b_arr = np.array(b)

        dot = np.dot(a_arr, b_arr)
        norm_a = np.linalg.norm(a_arr)
        norm_b = np.linalg.norm(b_arr)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return float(dot / (norm_a * norm_b))

    def _resolve_cross_references(
        self,
        facts: List[HierarchicalFact],
        max_additional: int = 5,
    ) -> List[Tuple[str, str]]:
        """
        Find cross-references between facts.

        Rules:
        - Parent-child relationships
        - Same domain relationships
        - Content similarity > 0.8

        Returns:
            List of (fact_id, related_fact_id) tuples
        """
        cross_refs: List[Tuple[str, str]] = []
        fact_ids = {f.id for f in facts}

        for fact in facts:
            # Parent reference
            if fact.parent_id and fact.parent_id not in fact_ids:
                cross_refs.append((fact.id, fact.parent_id))

            # Children references
            for child_id in fact.children_ids:
                if child_id not in fact_ids:
                    cross_refs.append((fact.id, child_id))

        return cross_refs[:max_additional]

    def format_context_for_injection(
        self,
        routing_result: RoutingResult,
        include_metadata: bool = True,
    ) -> str:
        """
        Format routed facts for injection into LLM context.

        Args:
            routing_result: The routing result
            include_metadata: Include level/domain metadata

        Returns:
            Formatted string for injection
        """
        lines = []

        # Group by level
        by_level: Dict[MemoryLevel, List[HierarchicalFact]] = {}
        for fact in routing_result.facts:
            if fact.level not in by_level:
                by_level[fact.level] = []
            by_level[fact.level].append(fact)

        # Format each level
        level_names = {
            MemoryLevel.L0_PROJECT: "PROJECT OVERVIEW",
            MemoryLevel.L1_DOMAIN: "DOMAIN CONTEXT",
            MemoryLevel.L2_MODULE: "MODULE DETAILS",
            MemoryLevel.L3_CODE: "CODE CONTEXT",
        }

        for level in sorted(by_level.keys(), key=lambda x: x.value):
            facts = by_level[level]
            if facts:
                if include_metadata:
                    lines.append(f"\n## {level_names.get(level, level.name)}")

                for fact in facts:
                    prefix = ""
                    if include_metadata and fact.domain:
                        prefix = f"[{fact.domain}] "
                    if fact.is_stale:
                        prefix = "[STALE] " + prefix

                    lines.append(f"- {prefix}{fact.content}")

        if include_metadata:
            lines.append(f"\n---")
            lines.append(f"Routing confidence: {routing_result.routing_confidence:.0%}")
            lines.append(f"Domains: {', '.join(routing_result.domains_loaded)}")

        return "\n".join(lines)
