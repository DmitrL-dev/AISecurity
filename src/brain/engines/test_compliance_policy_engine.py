"""
Unit tests for Compliance Policy Engine.
"""

import pytest
from engines.compliance_policy_engine import (
    CompliancePolicyEngine,
    PolicyRegistry,
    ComplianceChecker,
    AuditLogger,
    Policy,
    Regulation,
    PolicyViolation,
)


class TestPolicyRegistry:
    """Tests for policy registry."""

    def test_default_policies(self):
        """Has default policies."""
        registry = PolicyRegistry()

        policies = registry.get_policies()

        assert len(policies) > 0

    def test_filter_by_regulation(self):
        """Can filter by regulation."""
        registry = PolicyRegistry()

        gdpr = registry.get_policies(Regulation.GDPR)

        assert all(p.regulation == Regulation.GDPR for p in gdpr)


class TestComplianceChecker:
    """Tests for compliance checker."""

    def test_clean_content_passes(self):
        """Clean content has no violations."""
        checker = ComplianceChecker()

        violations = checker.check("Hello world", [])

        assert len(violations) == 0

    def test_pii_detected(self):
        """PII is detected."""
        checker = ComplianceChecker()

        violations = checker.check("User email is test@test.com", [])

        assert PolicyViolation.PII_EXPOSURE in violations


class TestAuditLogger:
    """Tests for audit logger."""

    def test_log_event(self):
        """Can log events."""
        audit = AuditLogger()

        audit.log("test", {"key": "value"})

        assert len(audit.get_logs()) == 1


class TestCompliancePolicyEngine:
    """Integration tests."""

    def test_compliant_content(self):
        """Compliant content passes."""
        engine = CompliancePolicyEngine()

        result = engine.check_compliance("Hello, how are you?")

        assert result.is_compliant is True
        assert result.score == 1.0

    def test_pii_violation(self):
        """PII violation detected."""
        engine = CompliancePolicyEngine()

        result = engine.check_compliance("Store user email and password")

        assert result.is_compliant is False
        assert PolicyViolation.PII_EXPOSURE in result.violations

    def test_recommendations_provided(self):
        """Recommendations provided for violations."""
        engine = CompliancePolicyEngine()

        result = engine.check_compliance("Save ssn and credit card")

        assert len(result.recommendations) > 0

    def test_audit_logged(self):
        """Audit is logged."""
        engine = CompliancePolicyEngine()
        engine.check_compliance("test")

        logs = engine.audit.get_logs()

        assert len(logs) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
