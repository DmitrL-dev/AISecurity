"""Tests for Freshness and Actuality Detection."""

import time
import pytest
from pathlib import Path

from rlm_toolkit.freshness import (
    FreshnessMetadata,
    ObsolescenceDetector,
    ObsoleteMarker,
    ActualityScorer,
    ActualityReviewQueue,
    KnowledgeType,
)


class TestFreshnessMetadata:
    """Tests for FreshnessMetadata."""

    def test_creation(self):
        """Test creating freshness metadata."""
        fm = FreshnessMetadata(
            indexed_at=time.time(),
            source_mtime=time.time(),
            source_hash="abc123",
        )

        assert fm.age_hours < 1
        assert not fm.is_stale

    def test_stale_detection(self):
        """Test staleness detection."""
        old_time = time.time() - (25 * 3600)  # 25 hours ago
        fm = FreshnessMetadata(
            indexed_at=old_time,
            source_mtime=old_time,
            source_hash="abc123",
            ttl_hours=24,
        )

        assert fm.is_stale
        assert fm.age_hours > 24

    def test_needs_revalidation(self):
        """Test revalidation check."""
        week_ago = time.time() - (8 * 24 * 3600)  # 8 days ago
        fm = FreshnessMetadata(
            indexed_at=week_ago,
            source_mtime=week_ago,
            source_hash="abc123",
        )

        assert fm.needs_revalidation

    def test_validate(self):
        """Test validation."""
        old = time.time() - (48 * 3600)
        fm = FreshnessMetadata(
            indexed_at=old,
            source_mtime=old,
            source_hash="abc123",
        )

        fm.validate()

        assert fm.last_validated is not None
        assert not fm.needs_revalidation

    def test_human_confirm(self):
        """Test human confirmation."""
        fm = FreshnessMetadata(
            indexed_at=time.time(),
            source_mtime=time.time(),
            source_hash="abc123",
        )

        fm.confirm()

        assert fm.human_confirmed
        assert fm.last_validated is not None


class TestObsolescenceDetector:
    """Tests for ObsolescenceDetector."""

    @pytest.fixture
    def detector(self):
        return ObsolescenceDetector()

    def test_detect_deprecated(self, detector):
        """Test detecting @deprecated."""
        content = """
        @deprecated
        def old_function():
            pass
        """

        markers = detector.scan(content)

        assert len(markers) > 0
        assert any("deprecated" in m.context.lower() for m in markers)

    def test_detect_todo(self, detector):
        """Test detecting TODO comments."""
        content = "# TODO: fix this later"

        markers = detector.scan(content)

        assert len(markers) == 1
        assert markers[0].severity == "low"

    def test_detect_fixme(self, detector):
        """Test detecting FIXME."""
        content = "# FIXME: urgent bug"

        markers = detector.scan(content)

        assert len(markers) == 1
        assert markers[0].severity == "medium"

    def test_detect_legacy(self, detector):
        """Test detecting LEGACY markers."""
        content = "# LEGACY: old code"

        markers = detector.scan(content)

        assert len(markers) == 1
        assert markers[0].severity == "high"

    def test_has_obsolescence(self, detector):
        """Test quick check."""
        assert detector.has_obsolescence("# TODO: fix")
        assert not detector.has_obsolescence("def clean_code(): pass")

    def test_line_numbers(self, detector):
        """Test line number detection."""
        content = """line 1
line 2
# FIXME: here
line 4"""

        markers = detector.scan(content)

        assert markers[0].line == 3


class TestActualityScorer:
    """Tests for ActualityScorer."""

    @pytest.fixture
    def scorer(self):
        return ActualityScorer()

    def test_fresh_content(self, scorer):
        """Test fresh content gets high score."""
        fm = FreshnessMetadata(
            indexed_at=time.time(),
            source_mtime=time.time(),
            source_hash="abc",
        )

        score = scorer.calculate("def clean(): pass", fm)

        assert score > 0.9

    def test_old_content(self, scorer):
        """Test old content gets lower score."""
        old = time.time() - (180 * 24 * 3600)  # 6 months
        fm = FreshnessMetadata(
            indexed_at=old,
            source_mtime=old,
            source_hash="abc",
        )

        score = scorer.calculate("def old(): pass", fm)

        assert score < 0.8

    def test_deprecated_content(self, scorer):
        """Test deprecated content gets low score."""
        fm = FreshnessMetadata(
            indexed_at=time.time(),
            source_mtime=time.time(),
            source_hash="abc",
        )

        score = scorer.calculate("@deprecated\ndef old(): pass", fm)

        assert score < 0.6

    def test_human_confirmed_boost(self, scorer):
        """Test human confirmation boosts score."""
        old = time.time() - (90 * 24 * 3600)  # 3 months
        fm = FreshnessMetadata(
            indexed_at=old,
            source_mtime=old,
            source_hash="abc",
            human_confirmed=True,
        )

        score_confirmed = scorer.calculate("def func(): pass", fm)

        fm.human_confirmed = False
        score_not_confirmed = scorer.calculate("def func(): pass", fm)

        assert score_confirmed > score_not_confirmed

    def test_explain_score(self, scorer):
        """Test score explanation."""
        fm = FreshnessMetadata(
            indexed_at=time.time(),
            source_mtime=time.time(),
            source_hash="abc",
        )

        explanation = scorer.explain_score("# TODO: fix\ndef x(): pass", fm)

        assert "score" in explanation
        assert "reasons" in explanation
        assert "markers" in explanation
