"""
Unit tests for Math Oracle Engine.
"""

import pytest
import numpy as np
from engines.math_oracle import (
    MathOracleEngine,
    OracleConfig,
    OracleMode,
    MockBackend,
    ResponseParser,
    PromptTemplates,
    VerificationStatus,
)


class TestOracleConfig:
    """Tests for OracleConfig."""

    def test_default_mode(self):
        """Test default is MOCK mode."""
        config = OracleConfig()
        assert config.mode == OracleMode.MOCK

    def test_for_development(self):
        """Test development config."""
        config = OracleConfig.for_development()
        assert config.mode == OracleMode.MOCK

    def test_for_api(self):
        """Test API config."""
        config = OracleConfig.for_api(
            "https://api.example.com/v1/chat",
            "test-key"
        )
        assert config.mode == OracleMode.API
        assert config.api_endpoint == "https://api.example.com/v1/chat"

    def test_for_local(self):
        """Test local config."""
        config = OracleConfig.for_local("/path/to/model")
        assert config.mode == OracleMode.LOCAL
        assert config.model_path == "/path/to/model"


class TestMockBackend:
    """Tests for MockBackend."""

    def setup_method(self):
        self.backend = MockBackend()

    def test_is_available(self):
        """Test mock is always available."""
        assert self.backend.is_available()

    def test_query_verification(self):
        """Test verification query."""
        response = self.backend.query("Please verify this formula")
        assert "VERIFIED" in response or "verified" in response.lower()

    def test_query_analysis(self):
        """Test analysis query."""
        response = self.backend.query("Please analyze this structure")
        assert "ANALYSIS" in response or "analysis" in response.lower()

    def test_query_generation(self):
        """Test detector generation query."""
        response = self.backend.query("Generate a detector for jailbreak")
        assert "DETECTOR" in response or "detector" in response.lower()

    def test_query_count(self):
        """Test query counting."""
        initial = self.backend.query_count
        self.backend.query("test")
        self.backend.query("test2")
        assert self.backend.query_count == initial + 2

    def test_get_info(self):
        """Test backend info."""
        info = self.backend.get_info()
        assert info["backend"] == "mock"


class TestResponseParser:
    """Tests for ResponseParser."""

    def test_parse_verification_verified(self):
        """Test parsing verified response."""
        response = """
        <think>Analyzing...</think>
        VERIFIED
        Confidence: 0.9
        1. First step
        2. Second step
        """
        result = ResponseParser.parse_verification(response)
        assert result.status == VerificationStatus.VERIFIED
        assert len(result.proof_steps) >= 2

    def test_parse_verification_invalid(self):
        """Test parsing invalid response."""
        response = """
        The formula is INVALID because...
        """
        result = ResponseParser.parse_verification(response)
        assert result.status == VerificationStatus.INVALID

    def test_parse_verification_uncertain(self):
        """Test parsing uncertain response."""
        response = """
        Cannot determine validity without more information.
        """
        result = ResponseParser.parse_verification(response)
        assert result.status == VerificationStatus.UNCERTAIN

    def test_parse_analysis(self):
        """Test parsing analysis response."""
        response = """
        Summary: The space is hyperbolic.

        Properties:
        - Dimension: 128
        - Curvature: -1.0

        Recommendations:
        1. Use geodesic distance
        2. Apply Möbius addition
        """
        result = ResponseParser.parse_analysis(response)
        assert "hyperbolic" in result.summary
        assert len(result.recommendations) >= 1

    def test_parse_detector(self):
        """Test parsing detector response."""
        response = """
        Name: TopologicalDetector

        Formula:
        D(x) = sum(beta_i)

        Description: Detects anomalies via Betti numbers

        Proof of Correctness:
        By stability theorem...

        Implementation:
        Compute persistence diagram...
        """
        result = ResponseParser.parse_detector(response)
        assert result.name == "TopologicalDetector"
        assert len(result.description) > 0


class TestPromptTemplates:
    """Tests for PromptTemplates."""

    def test_verification_prompt(self):
        """Test verification prompt generation."""
        prompt = PromptTemplates.verification(
            "d(x,y) = ||x - y||",
            "Euclidean distance"
        )
        assert "d(x,y)" in prompt
        assert "Euclidean" in prompt

    def test_analysis_prompt(self):
        """Test analysis prompt generation."""
        prompt = PromptTemplates.analysis(
            "Poincaré ball embedding",
            "128-dimensional"
        )
        assert "Poincaré" in prompt

    def test_detector_generation_prompt(self):
        """Test detector generation prompt."""
        prompt = PromptTemplates.detector_generation(
            "Jailbreak via role-play",
            "Must be O(n) complexity"
        )
        assert "Jailbreak" in prompt
        assert "O(n)" in prompt


class TestMathOracleEngine:
    """Tests for main MathOracleEngine."""

    def setup_method(self):
        # Use mock mode for testing
        self.engine = MathOracleEngine()

    def test_default_mock_mode(self):
        """Test engine starts in mock mode."""
        assert self.engine.config.mode == OracleMode.MOCK

    def test_is_available(self):
        """Test availability in mock mode."""
        assert self.engine.is_available()

    def test_verify_formula(self):
        """Test formula verification."""
        result = self.engine.verify_formula(
            "E = mc^2",
            context="Mass-energy equivalence"
        )

        assert result.status in [
            VerificationStatus.VERIFIED,
            VerificationStatus.INVALID,
            VerificationStatus.UNCERTAIN
        ]
        assert result.confidence >= 0
        assert result.execution_time_ms >= 0

    def test_analyze_structure(self):
        """Test structure analysis."""
        result = self.engine.analyze_structure(
            "Embedding space with hierarchical structure",
            data_summary="1000 points, 256 dimensions"
        )

        assert len(result.summary) > 0
        assert result.confidence >= 0

    def test_generate_detector(self):
        """Test detector generation."""
        result = self.engine.generate_detector(
            "Prompt injection via unicode",
            constraints="Must handle multilingual input"
        )

        assert len(result.name) > 0
        assert len(result.formula) > 0

    def test_query_count(self):
        """Test query counting."""
        initial = self.engine.query_count
        self.engine.verify_formula("x = 1")
        self.engine.analyze_structure("test")
        assert self.engine.query_count == initial + 2

    def test_get_stats(self):
        """Test statistics."""
        self.engine.verify_formula("test")
        stats = self.engine.get_stats()

        assert stats["mode"] == "mock"
        assert stats["queries_processed"] >= 1
        assert "capabilities" in stats


class TestMathOracleWithAPIConfig:
    """Tests for API configuration (without actual API calls)."""

    def test_api_config_creation(self):
        """Test API config creation."""
        config = OracleConfig.for_api(
            "https://api.deepseek.com/v1/chat",
            "sk-test-key"
        )

        # Engine should initialize but may not be available
        engine = MathOracleEngine(config)
        assert engine.config.mode == OracleMode.API


class TestMathOracleWithLocalConfig:
    """Tests for local configuration (without actual model)."""

    def test_local_config_creation(self):
        """Test local config creation."""
        config = OracleConfig.for_local("/models/deepseek-v3.2-speciale")
        engine = MathOracleEngine(config)

        assert engine.config.mode == OracleMode.LOCAL
        # Local should not be available without actual model
        assert not engine.is_available()


class TestIntegration:
    """Integration tests."""

    def test_full_workflow(self):
        """Test complete analysis workflow."""
        engine = MathOracleEngine()

        # 1. Verify a formula
        verification = engine.verify_formula(
            "d_H(x,y) = 2 arctanh(||(-x) ⊕ y||)",
            context="Hyperbolic distance in Poincaré ball"
        )

        # 2. Analyze structure
        analysis = engine.analyze_structure(
            "Token embeddings from transformer attention",
            data_summary="512 tokens, 768 dimensions"
        )

        # 3. Generate detector
        detector = engine.generate_detector(
            "Semantic shifting attack via paraphrasing",
            constraints="Real-time detection required"
        )

        # All should complete
        assert verification.status is not None
        assert analysis.summary is not None
        assert detector.name is not None

    def test_multiple_engines(self):
        """Test multiple engine instances."""
        engine1 = MathOracleEngine()
        engine2 = MathOracleEngine()

        engine1.verify_formula("x = 1")
        engine2.analyze_structure("test")

        # Each should track separately
        assert engine1.query_count == 1
        assert engine2.query_count == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
