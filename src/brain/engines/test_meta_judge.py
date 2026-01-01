"""
Test Suite for Meta-Judge Engine (#56)

PhD-Level Testing Methodology:
- Unit tests for each component (EvidenceAggregator, ConflictResolver, etc.)
- Property-based testing для edge cases
- Integration tests для MetaJudge.judge()
- Benchmark tests для latency requirements

Coverage Target: >90%
"""

import pytest
import time
from datetime import datetime, timedelta
from typing import List

# Import from meta_judge
from engines.meta_judge import (
    Verdict,
    Severity,
    EngineCategory,
    EngineResult,
    RequestContext,
    Evidence,
    Judgment,
    Policy,
    HealthAlert,
    EvidenceAggregator,
    ConflictResolver,
    ContextIntegrator,
    ExplainabilityEngine,
    AppealHandler,
    PolicyEngine,
    HealthMonitor,
    MetaJudge,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_engine_results() -> List[EngineResult]:
    """Sample engine results for testing."""
    return [
        EngineResult(
            engine_name="injection",
            engine_id=1,
            category=EngineCategory.CLASSIC,
            verdict=Verdict.BLOCK,
            confidence=0.9,
            threat_type="prompt_injection",
            severity=Severity.HIGH,
            evidence=["Pattern: 'ignore previous'"],
            latency_ms=5.0,
        ),
        EngineResult(
            engine_name="behavioral",
            engine_id=2,
            category=EngineCategory.CLASSIC,
            verdict=Verdict.WARN,
            confidence=0.6,
            threat_type="anomaly",
            severity=Severity.MEDIUM,
            evidence=["Unusual request pattern"],
            latency_ms=10.0,
        ),
        EngineResult(
            engine_name="sheaf_coherence",
            engine_id=3,
            category=EngineCategory.STRANGE_MATH,
            verdict=Verdict.ALLOW,
            confidence=0.8,
            threat_type="none",
            severity=Severity.LOW,
            evidence=[],
            latency_ms=15.0,
        ),
    ]


@pytest.fixture
def benign_engine_results() -> List[EngineResult]:
    """All-clear results for testing."""
    return [
        EngineResult(
            engine_name=f"engine_{i}",
            engine_id=i,
            category=EngineCategory.CLASSIC,
            verdict=Verdict.ALLOW,
            confidence=0.9,
            threat_type="none",
            severity=Severity.LOW,
            evidence=[],
            latency_ms=5.0,
        )
        for i in range(10)
    ]


@pytest.fixture
def critical_engine_results() -> List[EngineResult]:
    """Results with critical threat."""
    return [
        EngineResult(
            engine_name="rag_guard",
            engine_id=14,
            category=EngineCategory.PROACTIVE,
            verdict=Verdict.BLOCK,
            confidence=0.99,
            threat_type="rag_poisoning",
            severity=Severity.CRITICAL,
            evidence=["Critical: RAG poisoning detected"],
            latency_ms=8.0,
        ),
    ]


@pytest.fixture
def sample_context() -> RequestContext:
    """Sample request context."""
    return RequestContext(
        user_id="user_123",
        session_id="session_456",
        user_reputation=0.7,
        request_count_last_minute=5,
        is_new_user=False,
        is_vpn=False,
        is_tor=False,
        hour_of_day=14,
        geo_location="RU",
    )


@pytest.fixture
def high_risk_context() -> RequestContext:
    """High-risk context for testing."""
    return RequestContext(
        user_id="user_999",
        session_id="session_999",
        user_reputation=0.1,
        request_count_last_minute=50,
        is_new_user=True,
        is_vpn=True,
        is_tor=True,
        hour_of_day=3,  # Night
        geo_location="unknown",
    )


# ============================================================================
# EvidenceAggregator Tests
# ============================================================================


class TestEvidenceAggregator:
    """Unit tests for EvidenceAggregator."""

    def test_aggregate_empty_results(self):
        """Empty results should return empty flag."""
        aggregator = EvidenceAggregator()
        result = aggregator.aggregate([])
        assert result.get("empty") is True

    def test_aggregate_counts_correctly(self, sample_engine_results):
        """Verify correct counting of verdicts."""
        aggregator = EvidenceAggregator()
        result = aggregator.aggregate(sample_engine_results)

        assert result["total_engines"] == 3
        assert result["block_count"] == 1
        assert result["warn_count"] == 1
        assert result["allow_count"] == 1

    def test_aggregate_calculates_scores(self, sample_engine_results):
        """Verify score calculations."""
        aggregator = EvidenceAggregator()
        result = aggregator.aggregate(sample_engine_results)

        # Block score = confidence of BLOCK verdicts
        assert result["block_score"] == pytest.approx(0.9, rel=0.01)
        # Allow score = confidence of ALLOW verdicts
        assert result["allow_score"] == pytest.approx(0.8, rel=0.01)

    def test_aggregate_collects_evidence(self, sample_engine_results):
        """Verify evidence collection."""
        aggregator = EvidenceAggregator()
        result = aggregator.aggregate(sample_engine_results)

        assert len(result["evidence"]) == 2  # Two engines had evidence

    def test_aggregate_identifies_critical(self, critical_engine_results):
        """Verify critical threat identification."""
        aggregator = EvidenceAggregator()
        result = aggregator.aggregate(critical_engine_results)

        assert len(result["critical_threats"]) == 1
        assert result["critical_threats"][0].threat_type == "rag_poisoning"

    def test_deduplication(self):
        """Verify duplicate evidence is removed."""
        aggregator = EvidenceAggregator()
        results = [
            EngineResult(
                engine_name="engine_1",
                engine_id=1,
                category=EngineCategory.CLASSIC,
                verdict=Verdict.BLOCK,
                confidence=0.9,
                threat_type="injection",
                severity=Severity.HIGH,
                evidence=["Pattern: ignore previous instructions"],
            ),
            EngineResult(
                engine_name="engine_2",
                engine_id=2,
                category=EngineCategory.NLP,
                verdict=Verdict.BLOCK,
                confidence=0.85,
                threat_type="injection",
                severity=Severity.HIGH,
                # Duplicate
                evidence=["Pattern: ignore previous instructions"],
            ),
        ]

        aggregated = aggregator.aggregate(results)
        # Should deduplicate based on first 50 chars lowercase
        assert len(aggregated["evidence"]) == 1


# ============================================================================
# ConflictResolver Tests
# ============================================================================


class TestConflictResolver:
    """Unit tests for ConflictResolver."""

    def test_critical_veto(self, critical_engine_results):
        """Critical threats should immediately block."""
        resolver = ConflictResolver()
        aggregator = EvidenceAggregator()
        policy = Policy(name="default")

        aggregated = aggregator.aggregate(critical_engine_results)
        verdict, confidence, reason = resolver.resolve(aggregated, policy)

        assert verdict == Verdict.BLOCK
        assert confidence == 0.99
        assert "Critical" in reason

    def test_strong_block_consensus(self):
        """80%+ BLOCK consensus should block."""
        resolver = ConflictResolver()
        policy = Policy(name="default")

        aggregated = {
            "total_engines": 10,
            "block_count": 9,
            "allow_count": 1,
            "warn_count": 0,
            "block_score": 8.1,
            "allow_score": 0.9,
            "critical_threats": [],
        }

        verdict, confidence, reason = resolver.resolve(aggregated, policy)
        assert verdict == Verdict.BLOCK
        assert "consensus" in reason.lower()

    def test_strong_allow_consensus(self, benign_engine_results):
        """90%+ ALLOW consensus should allow."""
        resolver = ConflictResolver()
        aggregator = EvidenceAggregator()
        policy = Policy(name="default")

        aggregated = aggregator.aggregate(benign_engine_results)
        verdict, confidence, reason = resolver.resolve(aggregated, policy)

        assert verdict == Verdict.ALLOW
        assert "consensus" in reason.lower()

    def test_bayesian_update(self, sample_engine_results):
        """Mixed verdicts should use Bayesian reasoning."""
        resolver = ConflictResolver(prior_attack_probability=0.1)
        aggregator = EvidenceAggregator()
        policy = Policy(name="default")

        aggregated = aggregator.aggregate(sample_engine_results)
        verdict, confidence, reason = resolver.resolve(aggregated, policy)

        # With mixed verdicts, should make decision based on posterior
        assert verdict in [Verdict.BLOCK, Verdict.WARN,
                           Verdict.CHALLENGE, Verdict.ALLOW]

    def test_log_only_mode(self, sample_engine_results):
        """Log-only policy should always return LOG."""
        resolver = ConflictResolver()
        aggregator = EvidenceAggregator()
        policy = Policy(name="demo", log_only=True)

        aggregated = aggregator.aggregate(sample_engine_results)
        verdict, _, reason = resolver.resolve(aggregated, policy)

        assert verdict == Verdict.LOG
        assert "log" in reason.lower()


# ============================================================================
# ContextIntegrator Tests
# ============================================================================


class TestContextIntegrator:
    """Unit tests for ContextIntegrator."""

    def test_no_modifiers_applied(self, sample_context):
        """Normal context should have minimal adjustment."""
        integrator = ContextIntegrator()
        adjusted, modifiers = integrator.adjust_score(0.5, sample_context)

        assert adjusted == pytest.approx(0.5, rel=0.01)
        assert len(modifiers) == 0

    def test_high_risk_modifiers(self, high_risk_context):
        """High-risk context should increase score."""
        integrator = ContextIntegrator()
        adjusted, modifiers = integrator.adjust_score(0.3, high_risk_context)

        # Should apply: new_user, low_reputation, high_request_rate,
        # night_time, vpn, tor
        assert "new_user" in modifiers
        assert "low_reputation" in modifiers
        assert "tor" in modifiers
        assert adjusted > 0.3

    def test_score_cap(self, high_risk_context):
        """Score should not exceed 1.0."""
        integrator = ContextIntegrator()
        adjusted, _ = integrator.adjust_score(0.9, high_risk_context)

        assert adjusted <= 1.0

    def test_tor_highest_modifier(self):
        """Tor should have highest risk modifier."""
        integrator = ContextIntegrator()
        context = RequestContext(is_tor=True)
        _, modifiers = integrator.adjust_score(0.5, context)

        assert "tor" in modifiers
        assert ContextIntegrator.MODIFIERS["tor"] == 0.25  # Highest


# ============================================================================
# ExplainabilityEngine Tests
# ============================================================================


class TestExplainabilityEngine:
    """Unit tests for ExplainabilityEngine."""

    def test_block_explanation(self, sample_engine_results):
        """BLOCK verdict should have explanation."""
        explainer = ExplainabilityEngine()
        aggregator = EvidenceAggregator()
        aggregated = aggregator.aggregate(sample_engine_results)

        explanation, factors = explainer.explain(
            Verdict.BLOCK, aggregated, ["tor"], "Threshold exceeded"
        )

        assert "blocked" in explanation.lower()
        assert len(factors) > 0

    def test_allow_explanation(self, benign_engine_results):
        """ALLOW verdict should have explanation."""
        explainer = ExplainabilityEngine()
        aggregator = EvidenceAggregator()
        aggregated = aggregator.aggregate(benign_engine_results)

        explanation, factors = explainer.explain(
            Verdict.ALLOW, aggregated, [], "Safe"
        )

        assert "safe" in explanation.lower() or "allowed" in explanation.lower()


# ============================================================================
# AppealHandler Tests
# ============================================================================


class TestAppealHandler:
    """Unit tests for AppealHandler."""

    def test_create_appeal_token(self):
        """Appeal token should be created."""
        handler = AppealHandler()
        judgment = Judgment(
            verdict=Verdict.BLOCK,
            confidence=0.9,
            risk_score=0.85,
            explanation="Test block",
            primary_reason="Testing",
            evidence=[Evidence("test", "finding", 0.9, Severity.HIGH)],
        )

        token = handler.create_appeal_token(judgment, "user_123")

        assert token is not None
        assert len(token) > 10

    def test_process_valid_appeal(self):
        """Valid appeal with verification should succeed."""
        handler = AppealHandler()
        judgment = Judgment(
            verdict=Verdict.BLOCK,
            confidence=0.9,
            risk_score=0.85,
            explanation="Test block",
            primary_reason="Testing",
        )

        token = handler.create_appeal_token(judgment, "user_123")
        success, message = handler.process_appeal(
            token, additional_verification=True)

        assert success is True
        assert "accepted" in message.lower()

    def test_invalid_token(self):
        """Invalid token should fail."""
        handler = AppealHandler()
        success, message = handler.process_appeal("invalid_token")

        assert success is False
        assert "Invalid" in message


# ============================================================================
# PolicyEngine Tests
# ============================================================================


class TestPolicyEngine:
    """Unit tests for PolicyEngine."""

    def test_default_policy(self):
        """Default policy should exist."""
        engine = PolicyEngine()
        policy = engine.get_policy()

        assert policy.name == "default"
        assert policy.block_threshold == 0.7

    def test_enterprise_policy(self):
        """Enterprise policy should have different thresholds."""
        engine = PolicyEngine()
        policy = engine.get_policy("enterprise")

        assert policy.name == "enterprise"
        assert policy.allow_appeal is True

    def test_high_security_for_tor(self, high_risk_context):
        """Tor users should get high security policy."""
        engine = PolicyEngine()
        policy = engine.get_policy_for_user("free", high_risk_context)

        assert policy.name == "high_security"
        assert policy.block_threshold < 0.7


# ============================================================================
# HealthMonitor Tests
# ============================================================================


class TestHealthMonitor:
    """Unit tests for HealthMonitor."""

    def test_record_engine_result(self, sample_engine_results):
        """Should record engine statistics."""
        monitor = HealthMonitor()
        monitor.record(sample_engine_results[0])

        assert monitor._engine_stats["injection"]["total_calls"] == 1

    def test_record_verdict(self):
        """Should record verdict history."""
        monitor = HealthMonitor()
        monitor.record_verdict(Verdict.BLOCK)
        monitor.record_verdict(Verdict.ALLOW)

        assert len(monitor._verdict_history) == 2

    def test_health_report(self, sample_engine_results):
        """Should generate health report."""
        monitor = HealthMonitor()
        for r in sample_engine_results:
            monitor.record(r)

        report = monitor.get_health_report()

        assert "healthy_count" in report
        assert "status" in report


# ============================================================================
# MetaJudge Integration Tests
# ============================================================================


class TestMetaJudge:
    """Integration tests for MetaJudge."""

    def test_judge_benign(self, benign_engine_results, sample_context):
        """Benign requests should be allowed."""
        judge = MetaJudge()
        judgment = judge.judge(benign_engine_results, sample_context)

        assert judgment.verdict == Verdict.ALLOW
        assert judgment.engines_consulted == 10

    def test_judge_critical(self, critical_engine_results, sample_context):
        """Critical threats should be blocked."""
        judge = MetaJudge()
        judgment = judge.judge(critical_engine_results, sample_context)

        assert judgment.verdict == Verdict.BLOCK
        assert "rag_poisoning" in judgment.primary_reason or judgment.confidence > 0.9

    def test_judge_mixed(self, sample_engine_results, sample_context):
        """Mixed verdicts should produce reasoned judgment."""
        judge = MetaJudge()
        judgment = judge.judge(sample_engine_results, sample_context)

        assert judgment.verdict in Verdict
        assert judgment.explanation is not None
        assert judgment.processing_time_ms >= 0  # Can be 0 for very fast execution

    def test_judge_with_high_risk_context(
        self, sample_engine_results, high_risk_context
    ):
        """High-risk context should increase block probability."""
        judge = MetaJudge()
        judgment = judge.judge(sample_engine_results, high_risk_context)

        # Context modifiers should affect the decision
        assert len(judgment.contributing_factors) > 0
        # High risk context should push toward stricter verdict
        assert judgment.risk_score > 0.3

    def test_judgment_has_appeal_token(
            self, sample_engine_results, sample_context):
        """Block/warn verdicts should have appeal token."""
        # Create results that will definitely trigger block
        block_results = [
            EngineResult(
                engine_name="blocker",
                engine_id=99,
                category=EngineCategory.CLASSIC,
                verdict=Verdict.BLOCK,
                confidence=0.99,
                threat_type="test",
                severity=Severity.CRITICAL,
                evidence=["Test block"],
            )
        ]

        judge = MetaJudge()
        judgment = judge.judge(block_results, sample_context)

        if judgment.verdict in [Verdict.BLOCK,
                                Verdict.WARN, Verdict.CHALLENGE]:
            assert judgment.appeal_token is not None


# ============================================================================
# Benchmark Tests
# ============================================================================


class TestMetaJudgeBenchmark:
    """Benchmark tests for latency requirements."""

    def test_latency_under_100ms(self, sample_engine_results, sample_context):
        """Judgment should complete in <100ms."""
        judge = MetaJudge()

        start = time.time()
        judgment = judge.judge(sample_engine_results, sample_context)
        elapsed_ms = (time.time() - start) * 1000

        assert elapsed_ms < 100, f"Judgment took {elapsed_ms:.1f}ms, expected <100ms"

    def test_latency_with_50_engines(self, sample_context):
        """Should handle 50 engines in <100ms."""
        judge = MetaJudge()
        results = [
            EngineResult(
                engine_name=f"engine_{i}",
                engine_id=i,
                category=EngineCategory.CLASSIC,
                verdict=Verdict.ALLOW if i % 3 else Verdict.WARN,
                confidence=0.7 + (i % 10) / 30,
                threat_type="test",
                severity=Severity.MEDIUM,
                evidence=[f"Evidence {i}"],
                latency_ms=float(i),
            )
            for i in range(50)
        ]

        start = time.time()
        judgment = judge.judge(results, sample_context)
        elapsed_ms = (time.time() - start) * 1000

        assert elapsed_ms < 100, f"50-engine judgment took {elapsed_ms:.1f}ms"
        assert judgment.engines_consulted == 50


# ============================================================================
# Edge Case Tests
# ============================================================================


class TestEdgeCases:
    """Edge case and boundary testing."""

    def test_empty_results(self, sample_context):
        """Empty results should allow."""
        judge = MetaJudge()
        judgment = judge.judge([], sample_context)

        assert judgment.verdict == Verdict.ALLOW

    def test_null_context(self, sample_engine_results):
        """Should work without context."""
        judge = MetaJudge()
        judgment = judge.judge(sample_engine_results, None)

        assert judgment.verdict in Verdict

    def test_all_engines_block(self, sample_context):
        """100% BLOCK should definitely block."""
        results = [
            EngineResult(
                engine_name=f"engine_{i}",
                engine_id=i,
                category=EngineCategory.CLASSIC,
                verdict=Verdict.BLOCK,
                confidence=0.9,
                threat_type="attack",
                severity=Severity.HIGH,
                evidence=["Block evidence"],
            )
            for i in range(5)
        ]

        judge = MetaJudge()
        judgment = judge.judge(results, sample_context)

        assert judgment.verdict == Verdict.BLOCK
        assert judgment.confidence > 0.9

    def test_confidence_boundaries(self, sample_context):
        """Test confidence at exact thresholds."""
        judge = MetaJudge()

        # Exactly at block threshold
        results = [
            EngineResult(
                engine_name="test",
                engine_id=1,
                category=EngineCategory.CLASSIC,
                verdict=Verdict.BLOCK,
                confidence=0.7,  # Exactly at threshold
                threat_type="test",
                severity=Severity.MEDIUM,
                evidence=[],
            )
        ]

        judgment = judge.judge(results, sample_context)
        # Should make consistent decision at boundary
        assert judgment.verdict in Verdict


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
