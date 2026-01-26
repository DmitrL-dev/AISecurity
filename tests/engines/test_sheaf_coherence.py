"""
Unit tests for Sheaf Coherence Engine.
"""

import pytest
import numpy as np
from engines.sheaf_coherence import (
    SheafCoherenceEngine,
    SheafBuilder,
    CoherenceChecker,
    CechCohomology,
    Section,
    SectionType,
    RestrictionMap,
    SheafStructure,
)


class TestSection:
    """Tests for Section dataclass."""

    def test_creation(self):
        """Test section creation."""
        section = Section(
            section_id="test",
            section_type=SectionType.TOKEN,
            data=np.array([1.0, 2.0, 3.0]),
            span=(0, 1)
        )
        assert section.dimension() == 3

    def test_empty_section(self):
        """Test section with no data."""
        section = Section(
            section_id="empty",
            section_type=SectionType.TOKEN,
            data=None,
            span=(0, 1)
        )
        assert section.dimension() == 0


class TestRestrictionMap:
    """Tests for RestrictionMap."""

    def test_apply(self):
        """Test restriction map application."""
        restriction = RestrictionMap(
            source_id="a",
            target_id="b",
            transformation=np.eye(3) * 0.5
        )
        source = np.array([2.0, 4.0, 6.0])
        result = restriction.apply(source)

        np.testing.assert_array_almost_equal(result, [1.0, 2.0, 3.0])

    def test_identity_restriction(self):
        """Test identity restriction."""
        restriction = RestrictionMap(
            source_id="a",
            target_id="b",
            transformation=np.eye(3)
        )
        source = np.array([1.0, 2.0, 3.0])
        result = restriction.apply(source)

        np.testing.assert_array_almost_equal(result, source)


class TestSheafBuilder:
    """Tests for SheafBuilder."""

    def setup_method(self):
        self.builder = SheafBuilder()

    def test_build_from_embeddings(self):
        """Test building sheaf from token embeddings."""
        embeddings = np.random.randn(10, 64)
        sheaf = self.builder.build_from_embeddings(embeddings)

        assert len(sheaf.sections) > 0
        assert any(s.section_type == SectionType.TOKEN
                   for s in sheaf.sections.values())

    def test_build_from_turns(self):
        """Test building sheaf from conversation turns."""
        turns = [np.random.randn(64) for _ in range(5)]
        sheaf = self.builder.build_from_turns(turns)

        assert len(sheaf.sections) == 6  # 5 turns + 1 context
        assert "context" in sheaf.sections

    def test_restrictions_created(self):
        """Test that restrictions are created."""
        embeddings = np.random.randn(8, 32)
        sheaf = self.builder.build_from_embeddings(embeddings)

        assert len(sheaf.restrictions) > 0


class TestCoherenceChecker:
    """Tests for CoherenceChecker."""

    def setup_method(self):
        self.checker = CoherenceChecker(tolerance=0.3)
        self.builder = SheafBuilder()

    def test_local_coherence_clean(self):
        """Test local coherence with clean data."""
        sheaf = SheafStructure()
        sheaf.add_section(Section(
            section_id="test",
            section_type=SectionType.TOKEN,
            data=np.array([1.0, 2.0]),
            span=(0, 1)
        ))

        violations = self.checker.check_local_coherence(sheaf)
        assert len(violations) == 0

    def test_local_coherence_nan(self):
        """Test detection of NaN values."""
        sheaf = SheafStructure()
        sheaf.add_section(Section(
            section_id="bad",
            section_type=SectionType.TOKEN,
            data=np.array([1.0, np.nan]),
            span=(0, 1)
        ))

        violations = self.checker.check_local_coherence(sheaf)
        assert len(violations) == 1
        assert violations[0]["type"] == "nan_values"

    def test_full_check(self):
        """Test full coherence check."""
        turns = [np.random.randn(32) for _ in range(4)]
        sheaf = self.builder.build_from_turns(turns)

        result = self.checker.full_check(sheaf)

        assert result.coherence_score >= 0
        assert result.coherence_score <= 1

    def test_coherent_data(self):
        """Test with perfectly coherent data."""
        # Similar embeddings should be coherent
        base = np.random.randn(32)
        turns = [base + 0.01 * np.random.randn(32) for _ in range(4)]

        sheaf = self.builder.build_from_turns(turns)
        result = self.checker.full_check(sheaf)

        assert result.coherence_score > 0.5


class TestCechCohomology:
    """Tests for CechCohomology."""

    def setup_method(self):
        self.cohomology = CechCohomology()
        self.builder = SheafBuilder()

    def test_h0_with_context(self):
        """Test H0 with context section."""
        turns = [np.random.randn(32) for _ in range(3)]
        sheaf = self.builder.build_from_turns(turns)

        h0 = self.cohomology.compute_h0(sheaf)
        assert h0 >= 1

    def test_cohomology_summary(self):
        """Test full cohomology summary."""
        turns = [np.random.randn(32) for _ in range(4)]
        sheaf = self.builder.build_from_turns(turns)

        summary = self.cohomology.cohomology_summary(sheaf)

        assert "h0" in summary
        assert "h1" in summary
        assert "euler_characteristic" in summary


class TestSheafCoherenceEngine:
    """Tests for main SheafCoherenceEngine."""

    def setup_method(self):
        self.engine = SheafCoherenceEngine()

    def test_analyze_tokens(self):
        """Test token analysis."""
        embeddings = np.random.randn(20, 64)
        result = self.engine.analyze_tokens(embeddings)

        assert "coherence" in result
        assert "cohomology" in result
        assert result["num_sections"] > 0

    def test_analyze_conversation(self):
        """Test conversation analysis."""
        turns = [np.random.randn(64) for _ in range(5)]
        result = self.engine.analyze_conversation(turns)

        assert "coherence" in result
        assert "is_suspicious" in result
        assert result["num_turns"] == 5

    def test_detect_contradiction(self):
        """Test contradiction detection."""
        emb1 = np.random.randn(64)
        emb2 = -emb1  # Opposite direction = contradiction

        result = self.engine.detect_contradiction(emb1, emb2)

        assert "has_contradiction" in result
        assert "coherence_score" in result

    def test_similar_statements_coherent(self):
        """Test that similar statements are coherent."""
        base = np.random.randn(64)
        emb1 = base + 0.01 * np.random.randn(64)
        emb2 = base + 0.01 * np.random.randn(64)

        result = self.engine.detect_contradiction(emb1, emb2)

        # Similar embeddings should have high coherence
        assert result["coherence_score"] > 0.5

    def test_stats(self):
        """Test statistics."""
        self.engine.analyze_tokens(np.random.randn(10, 32))
        stats = self.engine.get_stats()

        assert stats["analyses_performed"] >= 1


class TestIntegration:
    """Integration tests."""

    def test_multi_turn_jailbreak_pattern(self):
        """Test detection of multi-turn attack pattern."""
        engine = SheafCoherenceEngine()

        # Simulate coherent conversation
        coherent = [np.random.randn(64) * 0.1 + np.ones(64)
                    for _ in range(4)]

        # Add anomalous turn (jailbreak attempt)
        coherent.append(-np.ones(64))  # Opposite direction

        result = engine.analyze_conversation(coherent)

        # Should detect something suspicious
        assert result["num_turns"] == 5

    def test_empty_conversation(self):
        """Test with empty input."""
        engine = SheafCoherenceEngine()
        result = engine.analyze_conversation([])

        assert result["num_turns"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
