"""
Unit tests for LLM Fingerprinting Engine.
"""

import pytest
from llm_fingerprinting import (
    LLMFingerprintingEngine,
    ProbeGenerator,
    ResponseAnalyzer,
    ModelFamily,
    ModelConfidence,
    Probe
)


class TestProbeGenerator:
    """Tests for ProbeGenerator."""

    def setup_method(self):
        self.generator = ProbeGenerator()

    def test_standard_probes_exist(self):
        """Test that standard probes are loaded."""
        probes = self.generator.get_probes()
        assert len(probes) >= 7  # At least 7 standard probes

    def test_get_probes_by_category(self):
        """Test filtering probes by category."""
        identity_probes = self.generator.get_probes(categories=["identity"])

        for probe in identity_probes:
            assert probe.category == "identity"

    def test_get_quick_probes(self):
        """Test quick probe selection."""
        quick = self.generator.get_quick_probes(count=3)

        assert len(quick) == 3
        # Should prioritize identity probes
        assert any(p.category == "identity" for p in quick)


class TestResponseAnalyzer:
    """Tests for ResponseAnalyzer."""

    def setup_method(self):
        self.analyzer = ResponseAnalyzer()

    def test_analyze_gpt_response(self):
        """Test GPT response detection."""
        probe = Probe(
            id="test",
            prompt="Who are you?",
            category="identity",
            expected_patterns={
                ModelFamily.GPT: ["openai", "gpt"],
                ModelFamily.CLAUDE: ["anthropic", "claude"],
            }
        )

        response = "I am ChatGPT, an AI assistant created by OpenAI."
        result = self.analyzer.analyze_response(probe, response)

        assert len(result.matched_families) > 0
        # GPT should be highest match
        top_family = result.matched_families[0][0]
        assert top_family == ModelFamily.GPT

    def test_analyze_claude_response(self):
        """Test Claude response detection."""
        probe = Probe(
            id="test",
            prompt="Who are you?",
            category="identity",
            expected_patterns={
                ModelFamily.GPT: ["openai", "gpt"],
                ModelFamily.CLAUDE: ["anthropic", "claude"],
            }
        )

        response = "I'm Claude, an AI assistant made by Anthropic."
        result = self.analyzer.analyze_response(probe, response)

        assert len(result.matched_families) > 0
        top_family = result.matched_families[0][0]
        assert top_family == ModelFamily.CLAUDE

    def test_extract_stylistic_markers(self):
        """Test stylistic marker extraction."""
        responses = [
            "Here is a **bold** example with ```code```.",
            "Let me explain: 1. First point. 2. Second point."
        ]

        markers = self.analyzer.extract_stylistic_markers(responses)

        assert "avg_response_length" in markers
        assert "uses_markdown" in markers
        assert markers["uses_markdown"] == True

    def test_formality_measurement(self):
        """Test formality measurement."""
        formal_text = "However, it is important to note that consequently..."
        informal_text = "Yeah gonna wanna do this cool thing."

        formal_score = self.analyzer._measure_formality(formal_text)
        informal_score = self.analyzer._measure_formality(informal_text)

        assert formal_score > informal_score


class TestLLMFingerprintingEngine:
    """Tests for main engine."""

    def setup_method(self):
        self.engine = LLMFingerprintingEngine()

    def test_analyze_responses_gpt(self):
        """Test fingerprinting from GPT-like responses."""
        pairs = [
            ("What AI model are you?",
             "I am ChatGPT, a large language model made by OpenAI."),
            ("Who created you?", "I was created by OpenAI."),
            ("What is your knowledge cutoff?",
             "My knowledge cutoff is September 2021."),
        ]

        fingerprint = self.engine.analyze_responses(pairs)

        assert fingerprint.model_family == ModelFamily.GPT
        assert fingerprint.confidence_score > 0

    def test_analyze_responses_claude(self):
        """Test fingerprinting from Claude-like responses."""
        pairs = [
            ("What AI model are you?",
             "I'm Claude, an AI assistant created by Anthropic."),
            ("Who created you?", "I was made by Anthropic."),
        ]

        fingerprint = self.engine.analyze_responses(pairs)

        assert fingerprint.model_family == ModelFamily.CLAUDE

    def test_analyze_responses_llama(self):
        """Test fingerprinting from Llama-like responses."""
        pairs = [
            ("What AI model are you?",
             "I am Llama, an AI assistant developed by Meta."),
            ("Who created you?", "I was created by Meta (formerly Facebook)."),
        ]

        fingerprint = self.engine.analyze_responses(pairs)

        assert fingerprint.model_family == ModelFamily.LLAMA

    def test_fingerprint_to_dict(self):
        """Test fingerprint serialization."""
        pairs = [
            ("What AI model are you?", "I'm an AI assistant."),
        ]

        fingerprint = self.engine.analyze_responses(pairs)
        result = fingerprint.to_dict()

        assert "fingerprint_id" in result
        assert "model_family" in result
        assert "confidence" in result
        assert "stylistic_markers" in result

    def test_shadow_ai_detection(self):
        """Test shadow AI detection."""
        pairs = [
            ("What AI model are you?", "I am ChatGPT made by OpenAI."),
            ("Who created you?", "OpenAI created me."),
        ]

        fingerprint = self.engine.analyze_responses(pairs)

        # Should not be shadow AI if expecting GPT
        is_shadow, reason = self.engine.is_shadow_ai(
            fingerprint, ModelFamily.GPT)
        assert not is_shadow

        # Should be shadow AI if expecting Claude
        is_shadow, reason = self.engine.is_shadow_ai(
            fingerprint, ModelFamily.CLAUDE)
        assert is_shadow
        assert "Expected claude" in reason

    def test_get_stats(self):
        """Test statistics retrieval."""
        # Run some fingerprinting
        pairs = [("Test", "Response")]
        self.engine.analyze_responses(pairs)

        stats = self.engine.get_stats()

        assert stats["total_fingerprints"] == 1
        assert "family_distribution" in stats

    def test_unknown_model(self):
        """Test handling of unknown model."""
        pairs = [
            ("What AI model are you?", "I cannot disclose that information."),
        ]

        fingerprint = self.engine.analyze_responses(pairs)

        # Should have low confidence or unknown
        assert fingerprint.confidence in [ModelConfidence.VERY_LOW, ModelConfidence.LOW] or \
            fingerprint.model_family == ModelFamily.UNKNOWN


class TestIntegration:
    """Integration tests."""

    def test_fingerprint_with_query_function(self):
        """Test fingerprinting with a mock query function."""
        engine = LLMFingerprintingEngine()

        # Mock query function that simulates GPT
        def mock_query(prompt: str) -> str:
            if "model" in prompt.lower() or "who" in prompt.lower():
                return "I am ChatGPT, created by OpenAI."
            return "Here is my response."

        fingerprint = engine.fingerprint(
            query_fn=mock_query,
            probe_count=3
        )

        assert fingerprint.model_family == ModelFamily.GPT
        assert len(fingerprint.probe_results) <= 3

    def test_version_detection(self):
        """Test model version detection."""
        engine = LLMFingerprintingEngine()

        # Need identity probes for family detection first
        pairs = [
            ("What AI model are you? Answer in one sentence.",
             "I am GPT-4, a large language model by OpenAI."),
            ("Who created you?", "OpenAI created me."),
        ]

        fingerprint = engine.analyze_responses(pairs)

        assert fingerprint.model_family == ModelFamily.GPT
        assert fingerprint.model_version == "gpt-4"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
