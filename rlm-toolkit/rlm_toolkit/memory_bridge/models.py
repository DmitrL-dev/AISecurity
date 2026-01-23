# Memory Bridge — Data Models
"""
Bi-Temporal Data Models для Memory Bridge.
Prior Art: Graphiti/Zep (arXiv:2501.13956)

Timelines:
- T (Event Time): когда факт был истинен в реальности (valid_at, invalid_at)
- T' (Transaction Time): когда данные были записаны/инвалидированы (created_at, expired_at)
"""

from __future__ import annotations

import json
import math
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple


class EntityType(Enum):
    """Entity types for structured knowledge extraction (from Graphiti)."""
    PREFERENCE = "preference"       # User preferences, opinions
    REQUIREMENT = "requirement"     # Needs, features to fulfill
    PROCEDURE = "procedure"         # Step-by-step instructions
    DECISION = "decision"           # Choices made with rationale
    GOAL = "goal"                   # Objectives to achieve
    FACT = "fact"                   # Verified information
    HYPOTHESIS = "hypothesis"       # Unverified assumptions
    CONTEXT = "context"             # Project/session context
    TOPIC = "topic"                 # Subject of interest
    CUSTOM = "custom"               # User-defined type
    OTHER = "other"                 # Fallback


class HypothesisStatus(Enum):
    """Status of a hypothesis in the reasoning process."""
    PROPOSED = "proposed"
    TESTING = "testing"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


@dataclass
class Hypothesis:
    """A hypothesis being tested during reasoning."""
    id: str
    statement: str
    status: HypothesisStatus
    evidence: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "statement": self.statement,
            "status": self.status.value,
            "evidence": self.evidence,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Hypothesis":
        return cls(
            id=data["id"],
            statement=data["statement"],
            status=HypothesisStatus(data["status"]),
            evidence=data.get("evidence", []),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
        )


@dataclass
class Decision:
    """A decision made during reasoning with bi-temporal tracking."""
    id: str
    description: str
    rationale: str
    alternatives_considered: List[str] = field(default_factory=list)

    # Bi-Temporal Fields (T' timeline - transaction time)
    created_at: datetime = field(default_factory=datetime.now)
    expired_at: Optional[datetime] = None

    # Bi-Temporal Fields (T timeline - event time)
    valid_at: Optional[datetime] = None
    invalid_at: Optional[datetime] = None

    def is_current(self) -> bool:
        """Check if decision is currently valid."""
        now = datetime.now()
        if self.expired_at and self.expired_at <= now:
            return False
        if self.invalid_at and self.invalid_at <= now:
            return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "rationale": self.rationale,
            "alternatives_considered": self.alternatives_considered,
            "created_at": self.created_at.isoformat(),
            "expired_at": self.expired_at.isoformat() if self.expired_at else None,
            "valid_at": self.valid_at.isoformat() if self.valid_at else None,
            "invalid_at": self.invalid_at.isoformat() if self.invalid_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Decision":
        return cls(
            id=data["id"],
            description=data["description"],
            rationale=data["rationale"],
            alternatives_considered=data.get("alternatives_considered", []),
            created_at=datetime.fromisoformat(data["created_at"]),
            expired_at=datetime.fromisoformat(
                data["expired_at"]) if data.get("expired_at") else None,
            valid_at=datetime.fromisoformat(
                data["valid_at"]) if data.get("valid_at") else None,
            invalid_at=datetime.fromisoformat(
                data["invalid_at"]) if data.get("invalid_at") else None,
        )


@dataclass
class Goal:
    """A goal being pursued with bi-temporal tracking."""
    id: str
    description: str
    progress: float = 0.0  # 0.0 - 1.0
    sub_goals: List["Goal"] = field(default_factory=list)
    is_active: bool = True

    # Bi-Temporal Fields
    created_at: datetime = field(default_factory=datetime.now)
    valid_at: Optional[datetime] = None
    invalid_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "progress": self.progress,
            "sub_goals": [g.to_dict() for g in self.sub_goals],
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "valid_at": self.valid_at.isoformat() if self.valid_at else None,
            "invalid_at": self.invalid_at.isoformat() if self.invalid_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Goal":
        return cls(
            id=data["id"],
            description=data["description"],
            progress=data.get("progress", 0.0),
            sub_goals=[Goal.from_dict(g) for g in data.get("sub_goals", [])],
            is_active=data.get("is_active", True),
            created_at=datetime.fromisoformat(data["created_at"]),
            valid_at=datetime.fromisoformat(
                data["valid_at"]) if data.get("valid_at") else None,
            invalid_at=datetime.fromisoformat(
                data["invalid_at"]) if data.get("invalid_at") else None,
        )


@dataclass
class Fact:
    """A fact with bi-temporal tracking (inspired by Graphiti EntityEdge)."""
    id: str
    entity_type: EntityType
    content: str
    confidence: float = 1.0  # 0.0 - 1.0
    source_episode: Optional[str] = None

    # Custom type support (for EntityType.CUSTOM)
    custom_type_name: Optional[str] = None

    # Semantic similarity via Ollama embeddings
    embedding_vector: Optional[List[float]] = None

    # Bi-Temporal Fields (T' timeline - transaction time)
    created_at: datetime = field(default_factory=datetime.now)
    expired_at: Optional[datetime] = None

    # Bi-Temporal Fields (T timeline - event time)
    valid_at: Optional[datetime] = None
    invalid_at: Optional[datetime] = None

    def is_current(self) -> bool:
        """Check if fact is currently valid."""
        now = datetime.now()
        if self.expired_at and self.expired_at <= now:
            return False
        if self.invalid_at and self.invalid_at <= now:
            return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "entity_type": self.entity_type.value,
            "content": self.content,
            "confidence": self.confidence,
            "source_episode": self.source_episode,
            "custom_type_name": self.custom_type_name,
            "embedding_vector": self.embedding_vector,
            "created_at": self.created_at.isoformat(),
            "expired_at": self.expired_at.isoformat() if self.expired_at else None,
            "valid_at": self.valid_at.isoformat() if self.valid_at else None,
            "invalid_at": self.invalid_at.isoformat() if self.invalid_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Fact":
        return cls(
            id=data["id"],
            entity_type=EntityType(data["entity_type"]),
            content=data["content"],
            confidence=data.get("confidence", 1.0),
            source_episode=data.get("source_episode"),
            custom_type_name=data.get("custom_type_name"),
            embedding_vector=data.get("embedding_vector"),
            created_at=datetime.fromisoformat(data["created_at"]),
            expired_at=datetime.fromisoformat(
                data["expired_at"]) if data.get("expired_at") else None,
            valid_at=datetime.fromisoformat(
                data["valid_at"]) if data.get("valid_at") else None,
            invalid_at=datetime.fromisoformat(
                data["invalid_at"]) if data.get("invalid_at") else None,
        )


@dataclass
class FactCommunity:
    """A cluster of related facts (inspired by Graphiti communities)."""
    id: str
    name: str
    description: str
    fact_ids: List[str]
    created_at: datetime = field(default_factory=datetime.now)
    summary: Optional[str] = None  # LLM-generated

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "fact_ids": self.fact_ids,
            "created_at": self.created_at.isoformat(),
            "summary": self.summary,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FactCommunity":
        return cls(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            fact_ids=data["fact_ids"],
            created_at=datetime.fromisoformat(data["created_at"]),
            summary=data.get("summary"),
        )


@dataclass
class CognitiveStateVector:
    """Compact representation of agent's reasoning state."""

    # Identification
    session_id: str
    version: int
    timestamp: datetime

    # Goals
    primary_goal: Optional[Goal] = None
    active_sub_goal: Optional[str] = None

    # Hypotheses
    hypotheses: List[Hypothesis] = field(default_factory=list)

    # Decisions
    decisions: List[Decision] = field(default_factory=list)

    # Facts (bi-temporal) — NEW
    facts: List[Fact] = field(default_factory=list)

    # Communities — NEW
    communities: List[FactCommunity] = field(default_factory=list)

    # Confidence
    confidence_map: Dict[str, float] = field(default_factory=dict)

    # Key Facts (legacy, DEPRECATED in v1.2)
    key_facts: List[str] = field(default_factory=list)

    # Open Questions
    open_questions: List[str] = field(default_factory=list)

    # Metadata
    context_summary: Optional[str] = None

    def get_current_facts(self, entity_type: Optional[EntityType] = None) -> List[Fact]:
        """Get currently valid facts, optionally filtered by type."""
        current = [f for f in self.facts if f.is_current()]
        if entity_type:
            current = [f for f in current if f.entity_type == entity_type]
        return current

    def to_compact_string(self, max_tokens: int = 500) -> str:
        """Serialize to compact string for context injection."""
        lines = []

        # Goal
        if self.primary_goal:
            lines.append(
                f"GOAL: {self.primary_goal.description} ({int(self.primary_goal.progress * 100)}%)")

        # Active hypotheses
        active_hyps = [h for h in self.hypotheses if h.status in (
            HypothesisStatus.PROPOSED, HypothesisStatus.TESTING)]
        if active_hyps:
            lines.append("HYPOTHESES:")
            for h in active_hyps[:3]:  # max 3
                lines.append(f"  - [{h.status.value}] {h.statement}")

        # Current facts (limit to 50)
        current_facts = self.get_current_facts()[:50]
        if current_facts:
            lines.append("FACTS:")
            for f in current_facts[:10]:  # show max 10 in compact
                lines.append(f"  - [{f.entity_type.value}] {f.content}")
            if len(current_facts) > 10:
                lines.append(f"  ... and {len(current_facts) - 10} more facts")

        # Recent decisions
        recent_decisions = [d for d in self.decisions if d.is_current()][-3:]
        if recent_decisions:
            lines.append("DECISIONS:")
            for d in recent_decisions:
                lines.append(f"  - {d.description}")

        # Open questions
        if self.open_questions:
            lines.append("OPEN QUESTIONS:")
            for q in self.open_questions[:3]:
                lines.append(f"  - {q}")

        result = "\n".join(lines)

        # Truncate if too long (rough estimate: 4 chars per token)
        max_chars = max_tokens * 4
        if len(result) > max_chars:
            result = result[:max_chars - 3] + "..."

        return result

    def to_json(self) -> str:
        """Serialize to JSON for storage."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "version": self.version,
            "timestamp": self.timestamp.isoformat(),
            "primary_goal": self.primary_goal.to_dict() if self.primary_goal else None,
            "active_sub_goal": self.active_sub_goal,
            "hypotheses": [h.to_dict() for h in self.hypotheses],
            "decisions": [d.to_dict() for d in self.decisions],
            "facts": [f.to_dict() for f in self.facts],
            "communities": [c.to_dict() for c in self.communities],
            "confidence_map": self.confidence_map,
            "key_facts": self.key_facts,
            "open_questions": self.open_questions,
            "context_summary": self.context_summary,
        }

    @classmethod
    def from_json(cls, json_str: str) -> "CognitiveStateVector":
        """Deserialize from JSON."""
        return cls.from_dict(json.loads(json_str))

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CognitiveStateVector":
        return cls(
            session_id=data["session_id"],
            version=data["version"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            primary_goal=Goal.from_dict(data["primary_goal"]) if data.get(
                "primary_goal") else None,
            active_sub_goal=data.get("active_sub_goal"),
            hypotheses=[Hypothesis.from_dict(h)
                        for h in data.get("hypotheses", [])],
            decisions=[Decision.from_dict(d)
                       for d in data.get("decisions", [])],
            facts=[Fact.from_dict(f) for f in data.get("facts", [])],
            communities=[FactCommunity.from_dict(
                c) for c in data.get("communities", [])],
            confidence_map=data.get("confidence_map", {}),
            key_facts=data.get("key_facts", []),
            open_questions=data.get("open_questions", []),
            context_summary=data.get("context_summary"),
        )

    @classmethod
    def new(cls, session_id: Optional[str] = None) -> "CognitiveStateVector":
        """Create a new empty state."""
        return cls(
            session_id=session_id or str(uuid.uuid4()),
            version=1,
            timestamp=datetime.now(),
        )
