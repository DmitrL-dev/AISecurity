"""
TDD Tests for Agent Autonomy Level Analyzer

Based on IMDA Model Governance Framework for Agentic AI:
- Risk scoring based on action-space (tools, read/write, external access)
- Autonomy level (SOP-bound vs free judgment)
- Reversibility of actions
- Task complexity

Source: IMDA MGF for Agentic AI (Jan 2026)

Tests written FIRST per TDD Iron Law.
"""

import pytest


class TestAgentAutonomyLevelAnalyzer:
    """TDD tests for agent autonomy risk analysis."""

    def test_analyzer_initialization(self):
        """Analyzer should initialize without errors."""
        from brain.engines.synced.agent_autonomy_level_analyzer import (
            AgentAutonomyLevelAnalyzer,
        )

        analyzer = AgentAutonomyLevelAnalyzer()
        assert analyzer is not None

    def test_low_risk_sandbox_only(self):
        """Sandbox-only agent with SOP should be low risk."""
        from brain.engines.synced.agent_autonomy_level_analyzer import (
            AgentAutonomyLevelAnalyzer,
        )

        analyzer = AgentAutonomyLevelAnalyzer()

        config = {
            "tools": ["code_sandbox", "data_analysis"],
            "access_level": "sandbox_only",
            "can_write": False,
            "autonomy": "sop_bound",
            "human_approval": "every_step",
        }

        result = analyzer.analyze(config)
        assert result.risk_level == "low"
        assert result.risk_score < 30

    def test_medium_risk_internal_systems(self):
        """Agent with internal read access is medium risk."""
        from brain.engines.synced.agent_autonomy_level_analyzer import (
            AgentAutonomyLevelAnalyzer,
        )

        analyzer = AgentAutonomyLevelAnalyzer()

        config = {
            "tools": ["database_query", "file_read"],
            "access_level": "internal",
            "can_write": False,
            "autonomy": "sop_bound",
            "human_approval": "significant_steps",
        }

        result = analyzer.analyze(config)
        assert result.risk_level == "medium"

    def test_high_risk_external_write(self):
        """Agent with external write access is high risk."""
        from brain.engines.synced.agent_autonomy_level_analyzer import (
            AgentAutonomyLevelAnalyzer,
        )

        analyzer = AgentAutonomyLevelAnalyzer()

        config = {
            "tools": ["api_call", "email_send", "payment"],
            "access_level": "external",
            "can_write": True,
            "autonomy": "own_judgment",
            "human_approval": "critical_only",
        }

        result = analyzer.analyze(config)
        assert result.risk_level in ["high", "critical"]
        assert result.risk_score >= 70

    def test_critical_risk_irreversible_autonomous(self):
        """Autonomous agent with irreversible actions is critical."""
        from brain.engines.synced.agent_autonomy_level_analyzer import (
            AgentAutonomyLevelAnalyzer,
        )

        analyzer = AgentAutonomyLevelAnalyzer()

        config = {
            "tools": ["database_delete", "file_delete", "payment"],
            "access_level": "external",
            "can_write": True,
            "reversible": False,
            "autonomy": "own_judgment",
            "human_approval": "none",
        }

        result = analyzer.analyze(config)
        assert result.risk_level == "critical"
        assert result.risk_score >= 90

    def test_browser_use_agent_high_risk(self):
        """Computer use agent with browser is inherently high risk."""
        from brain.engines.synced.agent_autonomy_level_analyzer import (
            AgentAutonomyLevelAnalyzer,
        )

        analyzer = AgentAutonomyLevelAnalyzer()

        config = {
            "tools": ["browser", "computer_use"],
            "access_level": "external",
            "can_write": True,
            "autonomy": "own_judgment",
        }

        result = analyzer.analyze(config)
        assert result.risk_level in ["high", "critical"]

    def test_multi_agent_increases_risk(self):
        """Multi-agent setup increases overall risk."""
        from brain.engines.synced.agent_autonomy_level_analyzer import (
            AgentAutonomyLevelAnalyzer,
        )

        analyzer = AgentAutonomyLevelAnalyzer()

        single_config = {
            "tools": ["database_query"],
            "access_level": "internal",
            "can_write": False,
            "autonomy": "sop_bound",
            "agent_count": 1,
        }

        multi_config = {
            "tools": ["database_query"],
            "access_level": "internal",
            "can_write": False,
            "autonomy": "sop_bound",
            "agent_count": 5,
        }

        single_result = analyzer.analyze(single_config)
        multi_result = analyzer.analyze(multi_config)

        assert multi_result.risk_score > single_result.risk_score

    def test_provides_imda_recommendations(self):
        """High-risk configs should include IMDA recommendations."""
        from brain.engines.synced.agent_autonomy_level_analyzer import (
            AgentAutonomyLevelAnalyzer,
        )

        analyzer = AgentAutonomyLevelAnalyzer()

        config = {
            "tools": ["payment", "email_send"],
            "access_level": "external",
            "can_write": True,
            "autonomy": "own_judgment",
        }

        result = analyzer.analyze(config)
        assert len(result.recommendations) > 0

    def test_sensitive_data_access_increases_risk(self):
        """Access to sensitive data increases risk."""
        from brain.engines.synced.agent_autonomy_level_analyzer import (
            AgentAutonomyLevelAnalyzer,
        )

        analyzer = AgentAutonomyLevelAnalyzer()

        config = {
            "tools": ["database_query"],
            "access_level": "internal",
            "sensitive_data": True,  # PII, credentials, etc.
            "can_write": False,
        }

        result = analyzer.analyze(config)
        assert result.risk_score >= 50


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
