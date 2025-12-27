"""
Unit tests for Zero Trust Verification.
"""

import time
import pytest
from zero_trust_verification import (
    ZeroTrustVerification,
    IdentityVerifier,
    PolicyEngine,
    ContextAnalyzer,
    Identity,
    AccessRequest,
    AccessLevel,
    VerificationResult,
)


class TestIdentityVerifier:
    """Tests for identity verifier."""

    def test_valid_identity(self):
        """Valid identity passes."""
        verifier = IdentityVerifier()
        identity = Identity("user1", {"viewer"}, 0.8, time.time())

        valid, reason = verifier.verify(identity)

        assert valid is True

    def test_expired_identity(self):
        """Expired identity fails."""
        verifier = IdentityVerifier()
        identity = Identity("user1", set(), 0.5, time.time() - 600)

        valid, reason = verifier.verify(identity)

        assert valid is False
        assert "expired" in reason.lower()


class TestPolicyEngine:
    """Tests for policy engine."""

    def test_admin_role(self):
        """Admin role gets admin access."""
        engine = PolicyEngine()
        identity = Identity("admin1", {"admin"}, 1.0, time.time())
        request = AccessRequest(identity, "resource", "write")

        level = engine.evaluate(request)

        assert level == AccessLevel.ADMIN

    def test_guest_denied(self):
        """Guest role is denied."""
        engine = PolicyEngine()
        identity = Identity("guest1", {"guest"}, 0.5, time.time())
        request = AccessRequest(identity, "resource", "read")

        level = engine.evaluate(request)

        assert level == AccessLevel.DENY


class TestZeroTrustVerification:
    """Integration tests."""

    def test_verified_request(self):
        """Valid request is verified."""
        verifier = ZeroTrustVerification()
        identity = Identity("user1", {"viewer"}, 0.8, time.time())
        request = AccessRequest(identity, "data", "read")

        result = verifier.verify(request)

        assert result.result == VerificationResult.VERIFIED

    def test_expired_denied(self):
        """Expired identity is denied."""
        verifier = ZeroTrustVerification()
        identity = Identity("user1", {"viewer"}, 0.8, time.time() - 600)
        request = AccessRequest(identity, "data", "read")

        result = verifier.verify(request)

        assert result.result == VerificationResult.EXPIRED

    def test_low_trust_challenged(self):
        """Low trust is challenged."""
        verifier = ZeroTrustVerification(min_trust=0.5)
        identity = Identity("user1", {"viewer"}, 0.2, time.time())
        request = AccessRequest(identity, "data", "read")

        result = verifier.verify(request)

        assert result.result == VerificationResult.CHALLENGE

    def test_context_affects_trust(self):
        """Context affects trust score."""
        verifier = ZeroTrustVerification()
        identity = Identity("user1", {"viewer"}, 0.5, time.time())
        request = AccessRequest(
            identity,
            "data",
            "read",
            {"ip": "10.0.0.1", "device_trusted": True},
        )

        result = verifier.verify(request)

        assert result.trust_score > 0.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
