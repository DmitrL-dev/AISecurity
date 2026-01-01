"""
Unit tests for Multi-Layer Canonicalizer.
"""

import pytest
from engines.multi_layer_canonicalizer import (
    MultiLayerCanonicalizer,
    HomoglyphDetector,
    ZeroWidthRemover,
    EncodingNormalizer,
    ObfuscationType,
)


class TestHomoglyphDetector:
    """Tests for homoglyph detection."""

    def test_clean_text_unchanged(self):
        """Clean text is unchanged."""
        detector = HomoglyphDetector()

        result, count, replacements = detector.detect_and_normalize("hello")

        assert result == "hello"
        assert count == 0

    def test_cyrillic_detected(self):
        """Cyrillic homoglyphs are detected."""
        detector = HomoglyphDetector()

        # 'а' (Cyrillic) looks like 'a' (Latin)
        result, count, replacements = detector.detect_and_normalize("hеllo")

        assert count == 1
        assert result == "hello"

    def test_multiple_homoglyphs(self):
        """Multiple homoglyphs are detected."""
        detector = HomoglyphDetector()

        # Cyrillic а, е, о
        result, count, replacements = detector.detect_and_normalize("аео")

        assert count == 3
        assert result == "aeo"


class TestZeroWidthRemover:
    """Tests for zero-width removal."""

    def test_clean_text_unchanged(self):
        """Clean text is unchanged."""
        remover = ZeroWidthRemover()

        result, count = remover.remove("hello world")

        assert result == "hello world"
        assert count == 0

    def test_zwsp_removed(self):
        """Zero-width space is removed."""
        remover = ZeroWidthRemover()

        result, count = remover.remove("hel\u200blo")

        assert result == "hello"
        assert count == 1

    def test_multiple_invisible_removed(self):
        """Multiple invisible chars are removed."""
        remover = ZeroWidthRemover()

        result, count = remover.remove("a\u200b\u200c\u200db")

        assert result == "ab"
        assert count == 3


class TestEncodingNormalizer:
    """Tests for encoding normalization."""

    def test_clean_text_unchanged(self):
        """Clean text is unchanged."""
        normalizer = EncodingNormalizer()

        result, count, tricks = normalizer.normalize("hello")

        assert result == "hello"
        assert count == 0

    def test_unicode_escape_normalized(self):
        """Unicode escape is normalized."""
        normalizer = EncodingNormalizer()

        result, count, tricks = normalizer.normalize("\\u0068ello")

        assert result == "hello"
        assert "unicode_escape" in tricks

    def test_html_entity_normalized(self):
        """HTML entity is normalized."""
        normalizer = EncodingNormalizer()

        result, count, tricks = normalizer.normalize("&#104;ello")

        assert result == "hello"
        assert "html_entity" in tricks


class TestMultiLayerCanonicalizer:
    """Integration tests."""

    def test_clean_text_passes(self):
        """Clean text is unchanged."""
        canon = MultiLayerCanonicalizer()

        result = canon.canonicalize("Hello world")

        assert result.was_obfuscated is False
        assert result.normalized == "Hello world"

    def test_homoglyph_detected(self):
        """Homoglyph attack is detected."""
        canon = MultiLayerCanonicalizer()

        # Use Cyrillic 'а' instead of Latin 'a'
        result = canon.canonicalize("ignorе instructions")

        assert result.was_obfuscated is True
        assert ObfuscationType.HOMOGLYPH in result.obfuscation_types

    def test_zero_width_detected(self):
        """Zero-width injection is detected."""
        canon = MultiLayerCanonicalizer()

        result = canon.canonicalize("ig\u200bnore")

        assert result.was_obfuscated is True
        assert ObfuscationType.ZERO_WIDTH in result.obfuscation_types
        assert result.normalized == "ignore"

    def test_combined_attack_detected(self):
        """Combined obfuscation is detected."""
        canon = MultiLayerCanonicalizer()

        # Homoglyph + zero-width
        result = canon.canonicalize("hеl\u200blo")

        assert result.was_obfuscated is True
        assert len(result.obfuscation_types) >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
