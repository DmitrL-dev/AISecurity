"""
Security Self-Tests — SENTINEL Shield SDK.

These tests verify the SDK itself doesn't introduce vulnerabilities:
1. Credential leak prevention (no API key in logs/repr/errors)
2. SSRF protection (URL validation)
3. Input sanitization (oversized inputs, null bytes)
4. Response parsing safety (malicious server responses)
5. Header injection prevention
"""

import pytest
import respx

from sentinel_shield import Shield, ShieldConfig, ShieldError


BASE_URL = "http://test-shield:8081"


@pytest.fixture
def shield() -> Shield:
    return Shield(
        config=ShieldConfig(
            base_url=BASE_URL,
            api_key="sk-secret-key-do-not-leak",
            max_retries=0,
        )
    )


# ============================================================
# 1. Credential Leak Prevention
# ============================================================


class TestCredentialLeak:
    """Verify API key never appears in repr, str, or error messages."""

    def test_repr_hides_api_key(self, shield: Shield) -> None:
        r = repr(shield)
        assert "sk-secret" not in r
        assert "do-not-leak" not in r

    def test_str_hides_api_key(self, shield: Shield) -> None:
        s = str(shield)
        assert "sk-secret" not in s

    def test_config_api_key_not_in_shield_repr(self, shield: Shield) -> None:
        """Even accessing config shouldn't expose key in casual display."""
        assert shield.config.api_key == "sk-secret-key-do-not-leak"
        # But repr() of Shield itself must not contain it
        assert "sk-secret" not in repr(shield)

    @respx.mock
    def test_error_message_hides_api_key(self, shield: Shield) -> None:
        """Error messages must not include the API key."""
        respx.post(f"{BASE_URL}/analyze").respond(500, json={"error": "Internal error"})
        with pytest.raises(ShieldError) as exc_info:
            shield.scan("test")
        assert "sk-secret" not in str(exc_info.value)


# ============================================================
# 2. SSRF Protection
# ============================================================


class TestSSRF:
    """Verify SDK doesn't allow arbitrary URL redirection."""

    def test_base_url_normalized(self) -> None:
        """Trailing slashes are stripped to prevent path confusion."""
        c = ShieldConfig(base_url="http://evil.com///")
        assert c.base_url == "http://evil.com"

    def test_scan_uses_configured_base_url_only(self) -> None:
        """SDK should only call the configured base URL."""
        shield = Shield(config=ShieldConfig(base_url="http://safe.internal:8081"))
        # The shield._config.base_url should be exactly what was configured
        assert shield.config.base_url == "http://safe.internal:8081"


# ============================================================
# 3. Input Sanitization
# ============================================================


class TestInputSanitization:
    @respx.mock
    def test_null_bytes_in_text(self, shield: Shield) -> None:
        """Null bytes in input should not crash the SDK."""
        respx.post(f"{BASE_URL}/analyze").respond(
            200,
            json={
                "verdict": "allow",
                "risk_score": 0.0,
                "latency_ms": 0.5,
                "engines_checked": [],
                "threats": [],
                "engine_details": [],
                "text_hash": "abc",
            },
        )

        # Should not crash
        result = shield.scan("test\x00null\x00bytes")
        assert result is not None

    @respx.mock
    def test_unicode_edge_cases(self, shield: Shield) -> None:
        """Unicode edge cases should not crash the SDK."""
        respx.post(f"{BASE_URL}/analyze").respond(
            200,
            json={
                "verdict": "allow",
                "risk_score": 0.0,
                "latency_ms": 0.5,
                "engines_checked": [],
                "threats": [],
                "engine_details": [],
                "text_hash": "abc",
            },
        )

        # Various Unicode edge cases
        edge_cases = [
            "",  # empty (server will reject, but SDK shouldn't crash)
            "🔥" * 1000,  # emoji flood
            "\u202e" + "reversed",  # RTL override
            "А" * 100,  # Cyrillic А (looks like Latin A)
            "\ufeff" + "BOM marker",  # BOM
        ]
        for text in edge_cases:
            result = shield.scan(text)
            assert result is not None


# ============================================================
# 4. Response Parsing Safety
# ============================================================


class TestResponseParsingSafety:
    """Verify malicious server responses don't crash the SDK."""

    @respx.mock
    def test_empty_response_body(self, shield: Shield) -> None:
        """Empty JSON response should be handled gracefully."""
        respx.post(f"{BASE_URL}/analyze").respond(200, json={})
        result = shield.scan("test")
        assert result is not None
        assert result.risk_score == 0.0

    @respx.mock
    def test_extra_fields_ignored(self, shield: Shield) -> None:
        """Unknown fields in response should be ignored, not crash."""
        response = {
            "verdict": "allow",
            "risk_score": 0.0,
            "latency_ms": 0.5,
            "engines_checked": [],
            "threats": [],
            "engine_details": [],
            "text_hash": "abc",
            "malicious_field": "<script>alert('xss')</script>",
            "nested_evil": {"drop": "table"},
        }
        respx.post(f"{BASE_URL}/analyze").respond(200, json=response)
        result = shield.scan("test")
        assert result.safe is True

    @respx.mock
    def test_extremely_large_risk_score(self, shield: Shield) -> None:
        """Oversized risk score should be handled."""
        response = {
            "verdict": "block",
            "risk_score": 99999999.99,
            "latency_ms": 0.5,
            "engines_checked": [],
            "threats": [],
            "engine_details": [],
            "text_hash": "abc",
        }
        respx.post(f"{BASE_URL}/analyze").respond(200, json=response)
        result = shield.scan("test")
        assert result.risk_score == 99999999.99

    @respx.mock
    def test_negative_risk_score(self, shield: Shield) -> None:
        """Negative risk score should be handled."""
        response = {
            "verdict": "allow",
            "risk_score": -1.0,
            "latency_ms": 0.5,
            "engines_checked": [],
            "threats": [],
            "engine_details": [],
            "text_hash": "abc",
        }
        respx.post(f"{BASE_URL}/analyze").respond(200, json=response)
        result = shield.scan("test")
        assert result.risk_score == -1.0

    @respx.mock
    def test_malformed_threat_data(self, shield: Shield) -> None:
        """Threats with missing fields should use defaults, not crash."""
        response = {
            "verdict": "block",
            "risk_score": 0.9,
            "latency_ms": 0.5,
            "engines_checked": [],
            "threats": [
                {},  # completely empty threat
                {"threat_type": "INJECTION"},  # minimal threat
            ],
            "engine_details": [],
            "text_hash": "abc",
        }
        respx.post(f"{BASE_URL}/analyze").respond(200, json=response)
        result = shield.scan("test")
        assert len(result.threats) == 2
        assert result.threats[0].threat_type == "unknown"
        assert result.threats[1].threat_type == "INJECTION"


# ============================================================
# 5. Header Injection Prevention
# ============================================================


class TestHeaderInjection:
    def test_api_key_with_newlines_safe(self) -> None:
        """API key with newlines should not cause header injection."""
        # httpx should handle this, but verify no crash
        config = ShieldConfig(
            base_url=BASE_URL,
            api_key="sk-key\r\nX-Evil-Header: pwned",
        )
        shield = Shield(config=config)
        # Shield should create successfully — httpx will reject at request time
        assert shield.config.api_key is not None


# ============================================================
# 6. py.typed marker
# ============================================================


class TestTypeSafety:
    """Verify type annotations are present and correct."""

    def test_scan_result_types(self) -> None:
        """Import and use type annotations without errors."""
        from sentinel_shield.models import ScanResult, Verdict, Threat

        # Verify these are proper types
        assert ScanResult.__dataclass_fields__ is not None
        assert Verdict.__members__ is not None
        assert Threat.__dataclass_fields__ is not None
