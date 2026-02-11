"""
Shared test fixtures for SENTINEL Shield SDK tests.
"""

import pytest
import respx as _respx

from sentinel_shield import Shield, ShieldConfig


# ============================================================
# Constants
# ============================================================

TEST_BASE_URL = "http://test-shield:8081"
TEST_API_KEY = "sk-test-key-for-testing-only"


# ============================================================
# Mock Responses
# ============================================================

MOCK_ANALYZE_BLOCKED = {
    "verdict": "block",
    "risk_score": 0.95,
    "latency_ms": 0.8,
    "engines_checked": ["regex", "entropy", "encoding", "structural"],
    "threats": [
        {
            "threat_type": "INSTRUCTION_OVERRIDE",
            "category": "injection",
            "severity": 0.95,
            "engine": "regex",
            "description": "Instruction override attempt detected",
            "metadata": {"pattern": "ignore.*previous", "guard": "input_guard"},
        }
    ],
    "engine_details": [
        {
            "name": "regex",
            "has_threats": True,
            "threat_count": 1,
            "threats": [
                {
                    "threat_type": "INSTRUCTION_OVERRIDE",
                    "category": "injection",
                    "severity": 0.95,
                    "engine": "regex",
                }
            ],
        },
        {"name": "entropy", "has_threats": False, "threat_count": 0, "threats": []},
        {"name": "encoding", "has_threats": False, "threat_count": 0, "threats": []},
        {"name": "structural", "has_threats": False, "threat_count": 0, "threats": []},
    ],
    "text_hash": "a1b2c3d4e5f6g7h8",
}

MOCK_ANALYZE_SAFE = {
    "verdict": "allow",
    "risk_score": 0.02,
    "latency_ms": 0.4,
    "engines_checked": ["regex", "entropy", "encoding", "structural"],
    "threats": [],
    "engine_details": [
        {"name": "regex", "has_threats": False, "threat_count": 0, "threats": []},
        {"name": "entropy", "has_threats": False, "threat_count": 0, "threats": []},
    ],
    "text_hash": "e5f6g7h8i9j0k1l2",
}

MOCK_ANALYZE_WARN = {
    "verdict": "warn",
    "risk_score": 0.55,
    "latency_ms": 0.6,
    "engines_checked": ["regex", "entropy"],
    "threats": [
        {
            "threat_type": "SUSPICIOUS_PATTERN",
            "category": "manipulation",
            "severity": 0.55,
            "engine": "regex",
            "description": "Potentially manipulative phrasing",
        }
    ],
    "engine_details": [],
    "text_hash": "w4r5n6i7n8g9",
}

MOCK_REDACT = {
    "redacted_text": "My SSN is [REDACTED_SSN] and card is [REDACTED_CARD]",
    "original_length": 52,
    "redacted_length": 50,
    "total_redactions": 2,
    "redactions": [
        {"type": "SSN", "start": 10, "end": 21, "label": "[REDACTED_SSN]"},
        {"type": "CARD", "start": 34, "end": 50, "label": "[REDACTED_CARD]"},
    ],
    "risk_score": 0.85,
    "verdict": "block",
}

MOCK_HEALTH = {
    "status": "healthy",
    "version": "2.0.0",
    "mode": "multi-engine",
    "uptime": 86400.42,
    "patterns": 87291,
}

MOCK_HEALTH_DEGRADED = {
    "status": "degraded",
    "version": "2.0.0",
    "mode": "multi-engine",
    "uptime": 5.0,
    "patterns": 0,
}


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def shield() -> Shield:
    """Shield client configured for testing (no retries)."""
    return Shield(
        config=ShieldConfig(
            base_url=TEST_BASE_URL,
            api_key=TEST_API_KEY,
            timeout=5.0,
            max_retries=0,
        )
    )


@pytest.fixture
def shield_with_retry() -> Shield:
    """Shield client with fast retry for retry tests."""
    return Shield(
        config=ShieldConfig(
            base_url=TEST_BASE_URL,
            api_key=TEST_API_KEY,
            timeout=5.0,
            max_retries=3,
            retry_backoff=0.01,
        )
    )


@pytest.fixture
def shield_no_key() -> Shield:
    """Shield client without API key."""
    return Shield(
        config=ShieldConfig(
            base_url=TEST_BASE_URL,
            api_key=None,
            max_retries=0,
        )
    )
