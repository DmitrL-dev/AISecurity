"""
TDD Tests — Domain Models.

Tests for ScanResult, Threat, Verdict, RedactResult, HealthStatus, ShieldConfig.
These tests verify domain logic with ZERO network calls.
"""

import pytest

from sentinel_shield.models import (
    EngineResult,
    HealthStatus,
    RedactResult,
    ScanResult,
    ShieldConfig,
    Threat,
    Verdict,
)


# ============================================================
# Verdict
# ============================================================


class TestVerdict:
    def test_allow_is_safe(self) -> None:
        assert Verdict.ALLOW.safe is True

    def test_warn_is_not_safe(self) -> None:
        assert Verdict.WARN.safe is False

    def test_block_is_not_safe(self) -> None:
        assert Verdict.BLOCK.safe is False

    def test_from_string(self) -> None:
        assert Verdict("allow") == Verdict.ALLOW
        assert Verdict("warn") == Verdict.WARN
        assert Verdict("block") == Verdict.BLOCK

    def test_invalid_string_raises(self) -> None:
        with pytest.raises(ValueError):
            Verdict("invalid")

    def test_is_string_enum(self) -> None:
        assert isinstance(Verdict.ALLOW, str)
        assert Verdict.ALLOW == "allow"


# ============================================================
# Threat
# ============================================================


class TestThreat:
    def test_create_minimal(self) -> None:
        t = Threat(
            threat_type="INJECTION",
            category="injection",
            severity=0.9,
            engine="regex",
        )
        assert t.threat_type == "INJECTION"
        assert t.severity == 0.9
        assert t.description == ""
        assert t.metadata == {}

    def test_frozen(self) -> None:
        t = Threat(threat_type="X", category="x", severity=0.5, engine="test")
        with pytest.raises(AttributeError):
            t.threat_type = "Y"  # type: ignore[misc]


# ============================================================
# ScanResult
# ============================================================


class TestScanResult:
    def _make_result(self, verdict: Verdict = Verdict.ALLOW) -> ScanResult:
        return ScanResult(
            verdict=verdict,
            risk_score=0.1 if verdict == Verdict.ALLOW else 0.9,
            latency_ms=0.8,
            engines_checked=["regex", "entropy"],
            threats=(
                [
                    Threat(
                        threat_type="INJECTION",
                        category="injection",
                        severity=0.9,
                        engine="regex",
                    )
                ]
                if verdict != Verdict.ALLOW
                else []
            ),
            engine_details=[],
            text_hash="abc123",
        )

    def test_safe_property_allow(self) -> None:
        r = self._make_result(Verdict.ALLOW)
        assert r.safe is True
        assert r.blocked is False

    def test_safe_property_block(self) -> None:
        r = self._make_result(Verdict.BLOCK)
        assert r.safe is False
        assert r.blocked is True

    def test_threat_types(self) -> None:
        r = self._make_result(Verdict.BLOCK)
        assert r.threat_types == ["INJECTION"]

    def test_no_threats_safe(self) -> None:
        r = self._make_result(Verdict.ALLOW)
        assert r.threat_types == []

    def test_frozen(self) -> None:
        r = self._make_result()
        with pytest.raises(AttributeError):
            r.verdict = Verdict.BLOCK  # type: ignore[misc]


# ============================================================
# RedactResult
# ============================================================


class TestRedactResult:
    def test_create(self) -> None:
        r = RedactResult(
            redacted_text="My SSN is [REDACTED_SSN]",
            original_length=26,
            redacted_length=24,
            total_redactions=1,
            redactions=[{"type": "SSN", "start": 10, "end": 21}],
            risk_score=0.75,
            verdict=Verdict.WARN,
        )
        assert r.total_redactions == 1
        assert "[REDACTED_SSN]" in r.redacted_text


# ============================================================
# HealthStatus
# ============================================================


class TestHealthStatus:
    def test_healthy(self) -> None:
        h = HealthStatus(
            status="healthy",
            version="2.0.0",
            mode="multi-engine",
            uptime=3600.0,
            patterns=87291,
        )
        assert h.healthy is True
        assert h.patterns == 87291

    def test_unhealthy(self) -> None:
        h = HealthStatus(
            status="degraded",
            version="2.0.0",
            mode="multi-engine",
            uptime=10.0,
            patterns=0,
        )
        assert h.healthy is False


# ============================================================
# ShieldConfig
# ============================================================


class TestShieldConfig:
    def test_default_values(self) -> None:
        c = ShieldConfig()
        assert c.base_url == "https://api.sentinel.dev"
        assert c.api_key is None
        assert c.timeout == 10.0
        assert c.max_retries == 3

    def test_strips_trailing_slash(self) -> None:
        c = ShieldConfig(base_url="http://localhost:8081/")
        assert c.base_url == "http://localhost:8081"

    def test_custom_values(self) -> None:
        c = ShieldConfig(
            base_url="http://localhost:8081",
            api_key="sk-test",
            timeout=5.0,
            max_retries=1,
        )
        assert c.api_key == "sk-test"
        assert c.timeout == 5.0

    def test_invalid_timeout_raises(self) -> None:
        with pytest.raises(ValueError, match="timeout must be positive"):
            ShieldConfig(timeout=0)

    def test_invalid_retries_raises(self) -> None:
        with pytest.raises(ValueError, match="max_retries must be non-negative"):
            ShieldConfig(max_retries=-1)
