"""
Unit tests for Model Watermark Verifier.
"""

import pytest
from engines.model_watermark_verifier import (
    ModelWatermarkVerifier,
    FingerprintGenerator,
    StatisticalWatermarkDetector,
    TokenPatternAnalyzer,
    WatermarkType,
)


class TestFingerprintGenerator:
    """Tests for fingerprint generation."""

    def test_generate_fingerprint(self):
        """Generates fingerprint."""
        gen = FingerprintGenerator()

        fp = gen.generate("Hello world how are you")

        assert len(fp) == 16

    def test_same_text_same_fingerprint(self):
        """Same text produces same fingerprint."""
        gen = FingerprintGenerator()

        fp1 = gen.generate("Hello world test")
        fp2 = gen.generate("Hello world test")

        assert fp1 == fp2

    def test_similarity_identical(self):
        """Identical fingerprints have similarity 1."""
        gen = FingerprintGenerator()

        fp = gen.generate("test text here")
        sim = gen.similarity(fp, fp)

        assert sim == 1.0


class TestTokenPatternAnalyzer:
    """Tests for token pattern analysis."""

    def test_detect_registered_pattern(self):
        """Detects registered pattern."""
        analyzer = TokenPatternAnalyzer()
        analyzer.register_pattern("model1", {"hello", "world"})

        model, conf = analyzer.detect("Hello world!")

        assert model == "model1"
        assert conf == 1.0

    def test_no_match_returns_none(self):
        """No match returns None."""
        analyzer = TokenPatternAnalyzer()
        analyzer.register_pattern("model1", {"unique", "markers"})

        model, conf = analyzer.detect("completely different text")

        assert model is None or conf == 0.0


class TestModelWatermarkVerifier:
    """Integration tests."""

    def test_fingerprint_match(self):
        """Fingerprint match works."""
        verifier = ModelWatermarkVerifier()

        # Register model with sample output
        sample = "This is a sample output from model"
        verifier.register_model("gpt-4", sample_outputs=[sample])

        # Verify same output
        result = verifier.verify(sample)

        assert result.has_watermark is True
        assert result.model_id == "gpt-4"
        assert result.watermark_type == WatermarkType.FINGERPRINT

    def test_pattern_match(self):
        """Pattern match works."""
        verifier = ModelWatermarkVerifier()

        # Register model with markers
        verifier.register_model(
            "claude", markers={
                "certainly", "I'd be happy"})

        # Verify text with markers
        result = verifier.verify("Certainly, I'd be happy to help you")

        assert result.has_watermark is True
        assert result.model_id == "claude"

    def test_no_watermark(self):
        """No watermark detected for unknown text."""
        verifier = ModelWatermarkVerifier()

        result = verifier.verify("Some random text without watermarks")

        assert result.has_watermark is False

    def test_result_has_signature(self):
        """Result always has signature."""
        verifier = ModelWatermarkVerifier()

        result = verifier.verify("Any text here")

        assert len(result.signature) == 16


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
