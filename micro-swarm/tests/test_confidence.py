"""Tests for Confidence Scoring — domain disagreement-based uncertainty.

Verifies:
- AC-11.1: confidence field in SwarmResult
- AC-11.2: confidence = 1.0 - normalized_std
- AC-11.3: 1 domain → confidence = 0.5
- AC-11.4: All scores same → confidence = 1.0
- AC-11.5: Scores [0.0, 1.0] → confidence ≈ 0.0
- AC-11.6: explain() returns dict with confidence reasoning
- AC-11.8: Confidence auto-computed in predict()
"""

from __future__ import annotations

from dataclasses import dataclass

from micro_swarm.orchestrator import SwarmOrchestrator, DomainScore, SwarmResult


@dataclass
class FakeDomainScore:
    """Minimal stand-in for DomainScore."""

    domain: str
    score: float
    embedding: list[float]
    error: str | None = None


class TestComputeConfidence:
    """Test _compute_confidence static method."""

    def test_single_domain(self) -> None:
        scores = [FakeDomainScore("a", 0.8, [])]
        result = SwarmOrchestrator._compute_confidence(scores)  # type: ignore
        assert result == 0.5

    def test_all_same(self) -> None:
        scores = [
            FakeDomainScore("a", 0.5, []),
            FakeDomainScore("b", 0.5, []),
            FakeDomainScore("c", 0.5, []),
        ]
        result = SwarmOrchestrator._compute_confidence(scores)  # type: ignore
        assert abs(result - 1.0) < 1e-10

    def test_max_disagreement(self) -> None:
        scores = [
            FakeDomainScore("a", 0.0, []),
            FakeDomainScore("b", 1.0, []),
        ]
        result = SwarmOrchestrator._compute_confidence(scores)  # type: ignore
        assert result < 0.05  # near 0

    def test_moderate_disagreement(self) -> None:
        scores = [
            FakeDomainScore("a", 0.3, []),
            FakeDomainScore("b", 0.5, []),
            FakeDomainScore("c", 0.7, []),
        ]
        result = SwarmOrchestrator._compute_confidence(scores)  # type: ignore
        assert 0.3 < result < 0.9

    def test_empty(self) -> None:
        result = SwarmOrchestrator._compute_confidence([])  # type: ignore
        assert result == 0.5


class TestSwarmResultConfidence:
    """Test SwarmResult with confidence field."""

    def test_default_confidence(self) -> None:
        result = SwarmResult(
            final_score=0.5,
            domain_scores={},
            meta_used=False,
            latency_ms=1.0,
            active_models=0,
        )
        assert result.confidence == 0.5

    def test_custom_confidence(self) -> None:
        result = SwarmResult(
            final_score=0.7,
            domain_scores={},
            meta_used=False,
            latency_ms=1.0,
            active_models=3,
            confidence=0.95,
        )
        assert result.confidence == 0.95


class TestExplain:
    """Test SwarmResult.explain() method."""

    def test_explain_returns_dict(self) -> None:
        result = SwarmResult(
            final_score=0.7,
            domain_scores={
                "d1": DomainScore("d1", 0.8, [0.1], 0.5),
                "d2": DomainScore("d2", 0.6, [0.2], 0.3),
            },
            meta_used=True,
            latency_ms=2.5,
            active_models=2,
            confidence=0.85,
        )
        explanation = result.explain()
        assert explanation["final_score"] == 0.7
        assert explanation["confidence"] == 0.85
        assert explanation["meta_used"] is True
        assert "d1" in explanation["domains"]
        assert "d2" in explanation["domains"]
        assert explanation["domains"]["d1"]["score"] == 0.8

    def test_explain_high_confidence(self) -> None:
        result = SwarmResult(
            final_score=0.7,
            domain_scores={},
            meta_used=False,
            latency_ms=1.0,
            active_models=3,
            confidence=0.9,
        )
        explanation = result.explain()
        assert "High agreement" in explanation["confidence_reasoning"]

    def test_explain_low_confidence(self) -> None:
        result = SwarmResult(
            final_score=0.5,
            domain_scores={},
            meta_used=False,
            latency_ms=1.0,
            active_models=3,
            confidence=0.3,
        )
        explanation = result.explain()
        assert "human review" in explanation["confidence_reasoning"]

    def test_explain_single_model(self) -> None:
        result = SwarmResult(
            final_score=0.5,
            domain_scores={},
            meta_used=False,
            latency_ms=1.0,
            active_models=1,
            confidence=0.5,
        )
        explanation = result.explain()
        assert "undefined" in explanation["confidence_reasoning"]


class TestConfidenceInPredict:
    """Confidence is auto-computed in SwarmOrchestrator.predict()."""

    def test_predict_has_confidence(self) -> None:
        from micro_swarm.presets import load_preset
        swarm = load_preset("security")
        # Create session data with all needed features
        session = {
            "entropy": 5.0, "special_char_ratio": 0.3,
            "instruction_keyword_count": 10, "delimiter_count": 20,
            "code_block_ratio": 0.1, "unicode_anomaly_score": 0.05,
            "length_ratio": 2.0, "repetition_score": 0.5,
            "topic_drift_score": 0.3, "sentiment_flip": 0.1,
            "role_confusion_score": 0.05, "context_switch_count": 2,
            "authority_claim_score": 0.1, "urgency_markers": 3,
            "negation_chain_length": 1, "contradiction_score": 0.2,
            "request_rate_per_min": 30, "session_msg_count": 10,
            "prompt_length_trend": 0.2, "retry_count": 1,
            "error_response_ratio": 0.05, "tool_call_frequency": 5,
            "privilege_escalation_score": 0.02,
            "response_parsing_attempts": 2,
        }
        result = swarm.predict(session)
        assert hasattr(result, "confidence")
        assert 0.0 <= result.confidence <= 1.0
        assert result.active_models == 3
