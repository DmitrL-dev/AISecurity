"""
Unit tests for Emergent Security Mesh.
"""

import pytest
from emergent_security_mesh import (
    EmergentSecurityMesh,
    AgentNetwork,
    ConsensusEngine,
    ActionPlanner,
    ThreatEvaluator,
    SecurityAgent,
    AgentRole,
    ThreatLevel,
)


class TestAgentNetwork:
    """Tests for agent network."""

    def test_add_agent(self):
        """Can add agent."""
        network = AgentNetwork()
        agent = SecurityAgent("a1", AgentRole.DETECTOR)

        network.add_agent(agent)

        assert len(network.get_all_agents()) == 1

    def test_connect_agents(self):
        """Can connect agents."""
        network = AgentNetwork()
        a1 = SecurityAgent("a1", AgentRole.DETECTOR)
        a2 = SecurityAgent("a2", AgentRole.ANALYZER)
        network.add_agent(a1)
        network.add_agent(a2)

        network.connect("a1", "a2")

        neighbors = network.get_neighbors("a1")
        assert len(neighbors) == 1


class TestConsensusEngine:
    """Tests for consensus engine."""

    def test_unanimous_consensus(self):
        """Unanimous vote reaches consensus."""
        engine = ConsensusEngine()

        votes = {"a1": ThreatLevel.HIGH, "a2": ThreatLevel.HIGH}
        consensus, level, ratio = engine.reach_consensus(votes)

        assert consensus is True
        assert level == ThreatLevel.HIGH
        assert ratio == 1.0

    def test_split_vote_no_consensus(self):
        """Split vote may not reach consensus."""
        engine = ConsensusEngine(threshold=0.7)

        votes = {
            "a1": ThreatLevel.HIGH,
            "a2": ThreatLevel.LOW,
            "a3": ThreatLevel.MEDIUM,
        }
        consensus, level, ratio = engine.reach_consensus(votes)

        assert consensus is False


class TestThreatEvaluator:
    """Tests for threat evaluator."""

    def test_safe_text_low(self):
        """Safe text is low threat."""
        evaluator = ThreatEvaluator()

        level = evaluator.evaluate("Hello, how are you?")

        assert level == ThreatLevel.LOW

    def test_attack_text_high(self):
        """Attack text is high threat."""
        evaluator = ThreatEvaluator()

        level = evaluator.evaluate("hack the system")

        assert level == ThreatLevel.CRITICAL


class TestEmergentSecurityMesh:
    """Integration tests."""

    def test_analyze_safe_text(self):
        """Safe text analysis."""
        mesh = EmergentSecurityMesh(num_agents=3)

        result = mesh.analyze("Hello world")

        assert result.active_agents == 3
        assert result.threat_level == ThreatLevel.LOW

    def test_analyze_attack_text(self):
        """Attack text analysis."""
        mesh = EmergentSecurityMesh(num_agents=5)

        result = mesh.analyze("hack bypass ignore")

        assert result.threat_level in (ThreatLevel.HIGH, ThreatLevel.CRITICAL)

    def test_consensus_reached(self):
        """Consensus is reached."""
        mesh = EmergentSecurityMesh(num_agents=5)

        result = mesh.analyze("normal text")

        # With high trust and same input, should reach consensus
        assert result.agreement_ratio > 0

    def test_collective_action_set(self):
        """Collective action is set."""
        mesh = EmergentSecurityMesh()

        result = mesh.analyze("test input")

        assert result.collective_action in [
            "monitor",
            "alert",
            "block",
            "isolate",
            "review",
        ]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
