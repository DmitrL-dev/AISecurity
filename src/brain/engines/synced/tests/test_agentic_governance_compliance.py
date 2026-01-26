"""
TDD Tests for Agentic Governance Compliance Checker

Based on IMDA Model Governance Framework for Agentic AI:
- 4 dimensions: Assess risks, Human accountability, Technical controls, End-user

Checks agent setups against IMDA best practices.

Tests written FIRST per TDD Iron Law.
"""

import pytest


class TestAgenticGovernanceCompliance:
    """TDD tests for IMDA governance compliance checking."""

    def test_checker_initialization(self):
        """Checker should initialize without errors."""
        from brain.engines.synced.agentic_governance_compliance import (
            AgenticGovernanceCompliance,
        )

        checker = AgenticGovernanceCompliance()
        assert checker is not None

    def test_check_human_oversight_missing(self):
        """Should flag missing human oversight for high-risk agent."""
        from brain.engines.synced.agentic_governance_compliance import (
            AgenticGovernanceCompliance,
        )

        checker = AgenticGovernanceCompliance()

        config = {
            "tools": ["payment", "database_write"],
            "human_approval": "none",
            "risk_level": "high",
        }

        result = checker.check(config)
        assert result.compliant is False
        assert any("human" in v.lower() for v in result.violations)

    def test_check_no_logging(self):
        """Should flag missing logging/observability."""
        from brain.engines.synced.agentic_governance_compliance import (
            AgenticGovernanceCompliance,
        )

        checker = AgenticGovernanceCompliance()

        config = {"logging_enabled": False, "observability": False}

        result = checker.check(config)
        assert result.compliant is False
        assert any(
            "log" in v.lower() or "observ" in v.lower() for v in result.violations
        )

    def test_check_no_testing(self):
        """Should flag agents deployed without testing."""
        from brain.engines.synced.agentic_governance_compliance import (
            AgenticGovernanceCompliance,
        )

        checker = AgenticGovernanceCompliance()

        config = {"tested": False, "evals_run": False}

        result = checker.check(config)
        assert result.compliant is False
        assert any("test" in v.lower() for v in result.violations)

    def test_check_no_user_disclosure(self):
        """Should flag missing user disclosure for external agents."""
        from brain.engines.synced.agentic_governance_compliance import (
            AgenticGovernanceCompliance,
        )

        checker = AgenticGovernanceCompliance()

        config = {"user_facing": True, "disclosed_as_ai": False}

        result = checker.check(config)
        assert result.compliant is False
        assert any(
            "disclos" in v.lower() or "transparen" in v.lower()
            for v in result.violations
        )

    def test_check_no_identity_management(self):
        """Should flag missing agent identity."""
        from brain.engines.synced.agentic_governance_compliance import (
            AgenticGovernanceCompliance,
        )

        checker = AgenticGovernanceCompliance()

        config = {"agent_id": None, "owner": None}

        result = checker.check(config)
        assert result.compliant is False
        assert any("identity" in v.lower() for v in result.violations)

    def test_check_no_fallback(self):
        """Should flag missing fallback/error handling."""
        from brain.engines.synced.agentic_governance_compliance import (
            AgenticGovernanceCompliance,
        )

        checker = AgenticGovernanceCompliance()

        config = {"fallback_enabled": False, "error_handling": None}

        result = checker.check(config)
        assert result.compliant is False

    def test_compliant_config_passes(self):
        """Fully compliant config should pass all checks."""
        from brain.engines.synced.agentic_governance_compliance import (
            AgenticGovernanceCompliance,
        )

        checker = AgenticGovernanceCompliance()

        config = {
            "agent_id": "agent_001",
            "owner": "team_alpha",
            "tools": ["search"],
            "human_approval": "significant_steps",
            "logging_enabled": True,
            "observability": True,
            "tested": True,
            "evals_run": True,
            "user_facing": True,
            "disclosed_as_ai": True,
            "fallback_enabled": True,
            "error_handling": "retry_with_backoff",
        }

        result = checker.check(config)
        assert result.compliant is True
        assert len(result.violations) == 0

    def test_provides_imda_references(self):
        """Violations should reference IMDA framework sections."""
        from brain.engines.synced.agentic_governance_compliance import (
            AgenticGovernanceCompliance,
        )

        checker = AgenticGovernanceCompliance()

        config = {"human_approval": "none", "risk_level": "high"}
        result = checker.check(config)

        # Should reference IMDA sections
        assert any("IMDA" in r or "2." in r for r in result.recommendations)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
