"""
Unit tests for Shadow AI Detector.
"""

import pytest
from shadow_ai_detector import (
    ShadowAIDetector,
    DomainDetector,
    APIKeyDetector,
    PolicyEngine,
    TrafficAnalyzer,
    AIProvider,
    ViolationType,
)


class TestDomainDetector:
    """Tests for domain detection."""

    def test_openai_detected(self):
        """OpenAI domain is detected."""
        detector = DomainDetector()

        detected, provider = detector.detect("https://api.openai.com/v1/chat")

        assert detected is True
        assert provider == AIProvider.OPENAI

    def test_anthropic_detected(self):
        """Anthropic domain is detected."""
        detector = DomainDetector()

        detected, provider = detector.detect(
            "https://api.anthropic.com/v1/messages")

        assert detected is True
        assert provider == AIProvider.ANTHROPIC

    def test_google_detected(self):
        """Google AI domain is detected."""
        detector = DomainDetector()

        detected, provider = detector.detect(
            "https://generativelanguage.googleapis.com/v1/models"
        )

        assert detected is True
        assert provider == AIProvider.GOOGLE

    def test_non_ai_domain_passes(self):
        """Non-AI domain passes."""
        detector = DomainDetector()

        detected, provider = detector.detect("https://example.com/api")

        assert detected is False


class TestAPIKeyDetector:
    """Tests for API key detection."""

    def test_openai_key_detected(self):
        """OpenAI key is detected."""
        detector = APIKeyDetector()

        # Use proper OpenAI key format (sk- followed by 48 chars)
        text = "My key is sk-aBcDeFgHiJkLmNoPqRsTuVwXyZ0123456789AbCdEfGhIjKl"
        detected, provider, masked = detector.detect(text)

        assert detected is True
        assert "sk-" in masked  # Just verify it's detected and masked

    def test_huggingface_key_detected(self):
        """HuggingFace key is detected."""
        detector = APIKeyDetector()

        text = "Token: hf_abcdefghijklmnopqrstuvwxyz0123456789"
        detected, provider, masked = detector.detect(text)

        assert detected is True
        assert provider == AIProvider.HUGGINGFACE

    def test_no_key_in_clean_text(self):
        """Clean text has no keys."""
        detector = APIKeyDetector()

        detected, provider, masked = detector.detect("Hello world")

        assert detected is False


class TestPolicyEngine:
    """Tests for policy enforcement."""

    def test_approved_provider_allowed(self):
        """Approved provider is allowed."""
        engine = PolicyEngine()
        engine.approve_provider(AIProvider.OPENAI)

        allowed, reason = engine.check(AIProvider.OPENAI)

        assert allowed is True

    def test_blocked_provider_blocked(self):
        """Blocked provider is blocked."""
        engine = PolicyEngine()
        engine.block_provider(AIProvider.ANTHROPIC)

        allowed, reason = engine.check(AIProvider.ANTHROPIC)

        assert allowed is False

    def test_unapproved_provider_blocked(self):
        """Unapproved provider blocked by default."""
        engine = PolicyEngine()
        engine.set_require_approval(True)

        allowed, reason = engine.check(AIProvider.COHERE)

        assert allowed is False


class TestTrafficAnalyzer:
    """Tests for traffic analysis."""

    def test_usage_recorded(self):
        """Usage is recorded."""
        analyzer = TrafficAnalyzer()

        analyzer.record("user1", AIProvider.OPENAI)
        analyzer.record("user1", AIProvider.OPENAI)
        analyzer.record("user1", AIProvider.ANTHROPIC)

        usage = analyzer.get_usage("user1")

        assert usage[AIProvider.OPENAI] == 2
        assert usage[AIProvider.ANTHROPIC] == 1

    def test_top_users(self):
        """Top users are ranked."""
        analyzer = TrafficAnalyzer()

        for _ in range(5):
            analyzer.record("user1", AIProvider.OPENAI)
        for _ in range(10):
            analyzer.record("user2", AIProvider.OPENAI)

        top = analyzer.get_top_users(2)

        assert top[0][0] == "user2"
        assert top[0][1] == 10


class TestShadowAIDetector:
    """Integration tests."""

    def test_unapproved_ai_detected(self):
        """Unapproved AI usage is detected."""
        detector = ShadowAIDetector()
        # Default: require approval, none approved

        result = detector.analyze_request(
            url="https://api.openai.com/v1/chat",
            content="Hello",
            user_id="user1",
        )

        assert result.detected is True
        assert result.violation_type == ViolationType.UNAPPROVED_PROVIDER

    def test_approved_ai_allowed(self):
        """Approved AI usage is allowed."""
        detector = ShadowAIDetector()
        detector.policy_engine.approve_provider(AIProvider.OPENAI)

        result = detector.analyze_request(
            url="https://api.openai.com/v1/chat",
            content="Hello",
            user_id="user1",
        )

        assert result.detected is False

    def test_api_key_leak_detected(self):
        """API key leak is detected."""
        detector = ShadowAIDetector()

        result = detector.analyze_request(
            url="https://example.com",
            content="sk-abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGHIJ",
            user_id="user1",
        )

        assert result.detected is True
        assert result.violation_type == ViolationType.LEAKED_API_KEY


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
