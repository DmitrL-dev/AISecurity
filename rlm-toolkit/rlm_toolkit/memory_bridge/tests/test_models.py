# Memory Bridge — Model Tests
"""Unit tests for data models."""

import json
import pytest
from datetime import datetime, timedelta

from rlm_toolkit.memory_bridge.models import (
    EntityType,
    HypothesisStatus,
    Hypothesis,
    Decision,
    Goal,
    Fact,
    FactCommunity,
    CognitiveStateVector,
)


class TestEntityType:
    """Tests for EntityType enum."""

    def test_all_types_present(self):
        """Verify all 11 entity types exist."""
        expected = [
            "preference", "requirement", "procedure", "decision", "goal",
            "fact", "hypothesis", "context", "topic", "custom", "other"
        ]
        actual = [e.value for e in EntityType]
        assert actual == expected

    def test_custom_type(self):
        """CUSTOM type exists for user-defined types."""
        assert EntityType.CUSTOM.value == "custom"


class TestHypothesis:
    """Tests for Hypothesis dataclass."""

    def test_creation(self):
        h = Hypothesis(
            id="h1",
            statement="Test hypothesis",
            status=HypothesisStatus.PROPOSED,
        )
        assert h.id == "h1"
        assert h.status == HypothesisStatus.PROPOSED
        assert h.evidence == []

    def test_to_dict_roundtrip(self):
        h = Hypothesis(
            id="h1",
            statement="Test",
            status=HypothesisStatus.TESTING,
            evidence=["evidence1"],
        )
        d = h.to_dict()
        h2 = Hypothesis.from_dict(d)
        assert h2.id == h.id
        assert h2.status == h.status
        assert h2.evidence == h.evidence


class TestDecision:
    """Tests for Decision dataclass with bi-temporal fields."""

    def test_creation_with_bitemporal(self):
        d = Decision(
            id="d1",
            description="Choose SQLite",
            rationale="Local-first",
            valid_at=datetime.now(),
        )
        assert d.valid_at is not None
        assert d.invalid_at is None
        assert d.is_current()

    def test_is_current_expired(self):
        d = Decision(
            id="d1",
            description="Old decision",
            rationale="Obsolete",
            expired_at=datetime.now() - timedelta(hours=1),
        )
        assert not d.is_current()

    def test_is_current_invalidated(self):
        d = Decision(
            id="d1",
            description="Invalidated",
            rationale="Wrong",
            invalid_at=datetime.now() - timedelta(hours=1),
        )
        assert not d.is_current()


class TestFact:
    """Tests for Fact dataclass with bi-temporal fields."""

    def test_creation(self):
        f = Fact(
            id="f1",
            entity_type=EntityType.PREFERENCE,
            content="User prefers dark mode",
        )
        assert f.entity_type == EntityType.PREFERENCE
        assert f.is_current()

    def test_custom_type(self):
        f = Fact(
            id="f1",
            entity_type=EntityType.CUSTOM,
            content="Custom fact",
            custom_type_name="user_setting",
        )
        assert f.custom_type_name == "user_setting"

    def test_embedding_vector(self):
        f = Fact(
            id="f1",
            entity_type=EntityType.FACT,
            content="Test",
            embedding_vector=[0.1, 0.2, 0.3],
        )
        assert f.embedding_vector == [0.1, 0.2, 0.3]

    def test_to_dict_roundtrip(self):
        f = Fact(
            id="f1",
            entity_type=EntityType.REQUIREMENT,
            content="Must support encryption",
            confidence=0.9,
            valid_at=datetime.now(),
        )
        d = f.to_dict()
        f2 = Fact.from_dict(d)
        assert f2.id == f.id
        assert f2.entity_type == f.entity_type
        assert f2.confidence == f.confidence


class TestCognitiveStateVector:
    """Tests for CognitiveStateVector."""

    def test_new_state(self):
        state = CognitiveStateVector.new()
        assert state.session_id is not None
        assert state.version == 1
        assert state.facts == []
        assert state.hypotheses == []

    def test_to_compact_string(self):
        state = CognitiveStateVector.new()
        state.primary_goal = Goal(
            id="g1",
            description="Implement Memory Bridge",
            progress=0.5,
        )
        state.facts.append(Fact(
            id="f1",
            entity_type=EntityType.FACT,
            content="SQLite is the storage backend",
        ))

        compact = state.to_compact_string(max_tokens=500)
        assert "GOAL:" in compact
        assert "Memory Bridge" in compact
        assert "50%" in compact
        assert "FACTS:" in compact

    def test_to_compact_string_truncation(self):
        state = CognitiveStateVector.new()
        # Add many facts
        for i in range(100):
            state.facts.append(Fact(
                id=f"f{i}",
                entity_type=EntityType.FACT,
                content=f"Fact number {i} with some content",
            ))

        compact = state.to_compact_string(max_tokens=100)
        assert len(compact) <= 100 * 4  # 4 chars per token

    def test_json_roundtrip(self):
        state = CognitiveStateVector.new("test-session")
        state.primary_goal = Goal(id="g1", description="Test goal")
        state.facts.append(Fact(
            id="f1",
            entity_type=EntityType.PREFERENCE,
            content="Test fact",
        ))
        state.hypotheses.append(Hypothesis(
            id="h1",
            statement="Test hypothesis",
            status=HypothesisStatus.PROPOSED,
        ))

        json_str = state.to_json()
        state2 = CognitiveStateVector.from_json(json_str)

        assert state2.session_id == state.session_id
        assert state2.primary_goal.description == state.primary_goal.description
        assert len(state2.facts) == 1
        assert len(state2.hypotheses) == 1

    def test_get_current_facts(self):
        state = CognitiveStateVector.new()

        # Add current fact
        state.facts.append(Fact(
            id="f1",
            entity_type=EntityType.FACT,
            content="Current fact",
        ))

        # Add expired fact
        state.facts.append(Fact(
            id="f2",
            entity_type=EntityType.FACT,
            content="Expired fact",
            expired_at=datetime.now() - timedelta(hours=1),
        ))

        current = state.get_current_facts()
        assert len(current) == 1
        assert current[0].id == "f1"

    def test_get_current_facts_by_type(self):
        state = CognitiveStateVector.new()
        state.facts.append(
            Fact(id="f1", entity_type=EntityType.PREFERENCE, content="A"))
        state.facts.append(
            Fact(id="f2", entity_type=EntityType.REQUIREMENT, content="B"))
        state.facts.append(
            Fact(id="f3", entity_type=EntityType.PREFERENCE, content="C"))

        prefs = state.get_current_facts(EntityType.PREFERENCE)
        assert len(prefs) == 2

        reqs = state.get_current_facts(EntityType.REQUIREMENT)
        assert len(reqs) == 1


class TestGoal:
    """Tests for Goal dataclass."""

    def test_creation(self):
        g = Goal(id="g1", description="Test goal", progress=0.25)
        assert g.progress == 0.25
        assert g.is_active

    def test_sub_goals(self):
        sub = Goal(id="s1", description="Sub goal")
        parent = Goal(id="g1", description="Parent", sub_goals=[sub])

        d = parent.to_dict()
        parent2 = Goal.from_dict(d)

        assert len(parent2.sub_goals) == 1
        assert parent2.sub_goals[0].id == "s1"


class TestFactCommunity:
    """Tests for FactCommunity dataclass."""

    def test_creation(self):
        c = FactCommunity(
            id="c1",
            name="Auth Cluster",
            description="Facts about authentication",
            fact_ids=["f1", "f2", "f3"],
        )
        assert len(c.fact_ids) == 3
        assert c.summary is None

    def test_to_dict_roundtrip(self):
        c = FactCommunity(
            id="c1",
            name="Test",
            description="Desc",
            fact_ids=["f1"],
            summary="Summary text",
        )
        d = c.to_dict()
        c2 = FactCommunity.from_dict(d)
        assert c2.summary == c.summary
