# Memory Bridge — Manager Layer
"""
High-level API for managing cognitive state.
Includes hybrid search and fact communities (from Graphiti).
"""

from __future__ import annotations

import math
import uuid
import warnings
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

import numpy as np

from .models import (
    EntityType,
    HypothesisStatus,
    Hypothesis,
    Decision,
    Goal,
    Fact,
    FactCommunity,
    CognitiveStateVector,
)
from .storage import StateStorage


class MemoryBridgeManager:
    """High-level API for Memory Bridge operations."""

    def __init__(
        self,
        storage: Optional[StateStorage] = None,
        auto_save: bool = True,
        auto_save_interval: int = 300,  # seconds
    ):
        """
        Initialize manager.

        Args:
            storage: StateStorage instance (creates default if None)
            auto_save: Enable periodic auto-save
            auto_save_interval: Seconds between auto-saves
        """
        self.storage = storage or StateStorage()
        self.auto_save = auto_save
        self.auto_save_interval = auto_save_interval

        self._current_state: Optional[CognitiveStateVector] = None
        self._last_save: Optional[datetime] = None

    # ===== Session Management =====

    def start_session(
        self,
        session_id: Optional[str] = None,
        restore: bool = True,
    ) -> CognitiveStateVector:
        """
        Start or restore a session.

        Args:
            session_id: Session ID (generates new if None)
            restore: Try to restore existing session

        Returns:
            Current state (new or restored).
        """
        session_id = session_id or str(uuid.uuid4())

        if restore:
            state = self.storage.load_state(session_id)
            if state:
                # Bump version for new session
                state.version += 1
                state.timestamp = datetime.now()
                self._current_state = state
                return state

        # Create new state
        self._current_state = CognitiveStateVector.new(session_id)
        return self._current_state

    def get_state(self) -> Optional[CognitiveStateVector]:
        """Get current state."""
        return self._current_state

    def get_state_for_injection(self, max_tokens: int = 500) -> str:
        """Get compact state string for context injection."""
        if not self._current_state:
            return ""
        return self._current_state.to_compact_string(max_tokens)

    def sync_state(self) -> int:
        """Save current state to storage."""
        if not self._current_state:
            raise ValueError("No active session")

        version = self.storage.save_state(self._current_state)
        self._last_save = datetime.now()

        # Increment version for next save
        self._current_state.version += 1
        self._current_state.timestamp = datetime.now()

        return version

    # ===== Goal Operations =====

    def set_goal(self, description: str, goal_id: Optional[str] = None) -> Goal:
        """Set primary goal."""
        if not self._current_state:
            raise ValueError("No active session")

        goal = Goal(
            id=goal_id or str(uuid.uuid4()),
            description=description,
            valid_at=datetime.now(),
        )
        self._current_state.primary_goal = goal
        return goal

    def update_goal_progress(self, progress: float) -> None:
        """Update primary goal progress (0.0 - 1.0)."""
        if not self._current_state or not self._current_state.primary_goal:
            raise ValueError("No active goal")

        self._current_state.primary_goal.progress = max(
            0.0, min(1.0, progress))

    # ===== Hypothesis Operations =====

    def add_hypothesis(
        self,
        statement: str,
        hypothesis_id: Optional[str] = None,
    ) -> Hypothesis:
        """Add a new hypothesis."""
        if not self._current_state:
            raise ValueError("No active session")

        hypothesis = Hypothesis(
            id=hypothesis_id or str(uuid.uuid4()),
            statement=statement,
            status=HypothesisStatus.PROPOSED,
        )
        self._current_state.hypotheses.append(hypothesis)
        return hypothesis

    def update_hypothesis(
        self,
        hypothesis_id: str,
        status: HypothesisStatus,
        evidence: Optional[List[str]] = None,
    ) -> Optional[Hypothesis]:
        """Update hypothesis status."""
        if not self._current_state:
            raise ValueError("No active session")

        for h in self._current_state.hypotheses:
            if h.id == hypothesis_id:
                h.status = status
                h.updated_at = datetime.now()
                if evidence:
                    h.evidence.extend(evidence)
                return h
        return None

    # ===== Decision Operations =====

    def record_decision(
        self,
        description: str,
        rationale: str,
        alternatives: Optional[List[str]] = None,
        decision_id: Optional[str] = None,
    ) -> Decision:
        """Record a decision."""
        if not self._current_state:
            raise ValueError("No active session")

        decision = Decision(
            id=decision_id or str(uuid.uuid4()),
            description=description,
            rationale=rationale,
            alternatives_considered=alternatives or [],
            valid_at=datetime.now(),
        )
        self._current_state.decisions.append(decision)
        return decision

    # ===== Fact Operations (Bi-Temporal) =====

    def add_key_fact(self, fact: str) -> None:
        """Add a key fact (DEPRECATED in v1.2 — use add_fact instead)."""
        warnings.warn(
            "add_key_fact is deprecated, use add_fact() instead",
            DeprecationWarning,
            stacklevel=2,
        )
        if not self._current_state:
            raise ValueError("No active session")
        self._current_state.key_facts.append(fact)

    def add_fact(
        self,
        content: str,
        entity_type: EntityType = EntityType.FACT,
        confidence: float = 1.0,
        fact_id: Optional[str] = None,
        custom_type_name: Optional[str] = None,
        valid_at: Optional[datetime] = None,
    ) -> Fact:
        """Add a fact with bi-temporal tracking."""
        if not self._current_state:
            raise ValueError("No active session")

        fact = Fact(
            id=fact_id or str(uuid.uuid4()),
            entity_type=entity_type,
            content=content,
            confidence=confidence,
            custom_type_name=custom_type_name,
            valid_at=valid_at or datetime.now(),
        )

        # Check for contradictions and invalidate old facts
        invalidated = self._invalidate_contradicting_facts(fact)

        self._current_state.facts.append(fact)
        return fact

    def get_current_facts(
        self,
        entity_type: Optional[EntityType] = None,
    ) -> List[Fact]:
        """Get currently valid facts."""
        if not self._current_state:
            return []
        return self._current_state.get_current_facts(entity_type)

    def _invalidate_contradicting_facts(
        self,
        new_fact: Fact,
        similarity_threshold: float = 0.85,
    ) -> List[str]:
        """Invalidate facts that contradict new_fact using semantic similarity."""
        if not self._current_state:
            return []

        invalidated_ids = []
        now = datetime.now()

        # Get embedding for new fact
        if not new_fact.embedding_vector:
            new_fact.embedding_vector = self._get_embedding(new_fact.content)

        for fact in self._current_state.facts:
            if not fact.is_current():
                continue

            # Same entity_type = potential contradiction
            if fact.entity_type != new_fact.entity_type:
                continue

            # Get or compute embedding
            if not fact.embedding_vector:
                fact.embedding_vector = self._get_embedding(fact.content)

            # High similarity + same type = contradiction (newer wins)
            if new_fact.embedding_vector and fact.embedding_vector:
                similarity = self._cosine_similarity(
                    new_fact.embedding_vector, fact.embedding_vector
                )
                if similarity >= similarity_threshold:
                    fact.invalid_at = new_fact.valid_at or now
                    fact.expired_at = now
                    invalidated_ids.append(fact.id)

        return invalidated_ids

    def _get_embedding(self, text: str) -> Optional[List[float]]:
        """Get embedding via local Ollama (nomic-embed-text)."""
        try:
            import ollama
            response = ollama.embeddings(model='nomic-embed-text', prompt=text)
            return response['embedding']
        except Exception:
            # Ollama not available or model not found
            return None

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        a_arr, b_arr = np.array(a), np.array(b)
        norm_a, norm_b = np.linalg.norm(a_arr), np.linalg.norm(b_arr)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a_arr, b_arr) / (norm_a * norm_b))

    # ===== Hybrid Search (ADR-007) =====

    def hybrid_search(
        self,
        query: str,
        top_k: int = 10,
        semantic_weight: float = 0.5,
        keyword_weight: float = 0.3,
        recency_weight: float = 0.2,
    ) -> List[Tuple[Fact, float]]:
        """Search facts using hybrid scoring (semantic + keyword + recency)."""
        if not self._current_state:
            return []

        query_embedding = self._get_embedding(query)
        query_tokens = set(query.lower().split())
        now = datetime.now()

        scored = []
        for fact in self._current_state.facts:
            if not fact.is_current():
                continue

            # Semantic score (cosine similarity)
            if query_embedding and fact.embedding_vector:
                semantic = self._cosine_similarity(
                    query_embedding, fact.embedding_vector)
            else:
                semantic = 0.0

            # Keyword score (Jaccard similarity)
            fact_tokens = set(fact.content.lower().split())
            union_size = len(query_tokens | fact_tokens)
            keyword = len(query_tokens & fact_tokens) / max(union_size, 1)

            # Recency score (exponential decay, 7-day half-life)
            age_hours = (now - fact.created_at).total_seconds() / 3600
            recency = math.exp(-age_hours / 168)  # 7 days = 168 hours

            # Weighted combination
            score = (
                semantic_weight * semantic +
                keyword_weight * keyword +
                recency_weight * recency
            )
            scored.append((fact, score))

        return sorted(scored, key=lambda x: -x[1])[:top_k]

    # ===== Fact Communities (ADR-008) =====

    def build_communities(self, min_cluster_size: int = 3) -> List[FactCommunity]:
        """Cluster facts into communities using DBSCAN."""
        if not self._current_state:
            return []

        current_facts = self.get_current_facts()

        # Filter facts with embeddings
        facts_with_embeddings = [
            f for f in current_facts if f.embedding_vector
        ]

        if len(facts_with_embeddings) < min_cluster_size:
            return []

        try:
            from sklearn.cluster import DBSCAN

            embeddings = np.array(
                [f.embedding_vector for f in facts_with_embeddings])

            # DBSCAN clustering with cosine distance
            clustering = DBSCAN(
                eps=0.3, min_samples=min_cluster_size, metric='cosine')
            labels = clustering.fit_predict(embeddings)

            # Group facts by cluster
            communities = []
            unique_labels = set(labels)

            for label in unique_labels:
                if label == -1:  # noise
                    continue

                cluster_facts = [
                    f for f, l in zip(facts_with_embeddings, labels) if l == label
                ]

                community = FactCommunity(
                    id=f"community_{label}_{uuid.uuid4().hex[:8]}",
                    name=self._generate_community_name(cluster_facts),
                    description=f"Cluster of {len(cluster_facts)} related facts",
                    fact_ids=[f.id for f in cluster_facts],
                )
                communities.append(community)

            self._current_state.communities = communities
            return communities

        except ImportError:
            # sklearn not available — warn user
            warnings.warn(
                "scikit-learn is required for build_communities(). "
                "Install with: pip install scikit-learn",
                UserWarning,
                stacklevel=2,
            )
            return []

    def _generate_community_name(self, facts: List[Fact]) -> str:
        """Generate a name for a community based on common entity types."""
        type_counts: Dict[EntityType, int] = {}
        for f in facts:
            type_counts[f.entity_type] = type_counts.get(f.entity_type, 0) + 1

        if type_counts:
            most_common = max(type_counts.items(), key=lambda x: x[1])
            return f"{most_common[0].value.title()} Cluster"
        return "Mixed Cluster"

    # ===== Open Questions =====

    def add_open_question(self, question: str) -> None:
        """Add an open question."""
        if not self._current_state:
            raise ValueError("No active session")
        self._current_state.open_questions.append(question)

    def resolve_question(self, question: str) -> bool:
        """Mark a question as resolved."""
        if not self._current_state:
            return False

        if question in self._current_state.open_questions:
            self._current_state.open_questions.remove(question)
            return True
        return False

    # ===== Confidence =====

    def set_confidence(self, key: str, value: float) -> None:
        """Set confidence for a key."""
        if not self._current_state:
            raise ValueError("No active session")
        self._current_state.confidence_map[key] = max(0.0, min(1.0, value))
