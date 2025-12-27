"""
Unit tests for Provenance Chain Tracker.
"""

import pytest
from provenance_tracker import (
    ProvenanceChainTracker,
    ProvenanceDAG,
    OriginVerifier,
    TaintPropagator,
    ProvenanceNode,
    TaintType,
    TrustLevel,
)


class TestProvenanceDAG:
    """Tests for DAG operations."""

    def test_add_and_get_node(self):
        """Node can be added and retrieved."""
        dag = ProvenanceDAG()
        node = ProvenanceNode(
            node_id="n1",
            content_hash="abc123",
            source_type=TaintType.USER_INPUT,
            trust_level=TrustLevel.LOW,
            timestamp=1.0,
        )

        dag.add_node(node)
        retrieved = dag.get_node("n1")

        assert retrieved is not None
        assert retrieved.node_id == "n1"

    def test_hop_count(self):
        """Hop count is calculated correctly."""
        dag = ProvenanceDAG()

        # Root node
        dag.add_node(
            ProvenanceNode(
                "n1",
                "h1",
                TaintType.USER_INPUT,
                TrustLevel.LOW,
                1.0)
        )
        # Child
        dag.add_node(
            ProvenanceNode(
                "n2",
                "h2",
                TaintType.AGENT_OUTPUT,
                TrustLevel.MEDIUM,
                2.0,
                parent_ids=["n1"],
            )
        )
        # Grandchild
        dag.add_node(
            ProvenanceNode(
                "n3",
                "h3",
                TaintType.AGENT_OUTPUT,
                TrustLevel.MEDIUM,
                3.0,
                parent_ids=["n2"],
            )
        )

        assert dag.get_hop_count("n1") == 0
        assert dag.get_hop_count("n2") == 1
        assert dag.get_hop_count("n3") == 2

    def test_taint_chain(self):
        """Taint chain is built correctly."""
        dag = ProvenanceDAG()

        dag.add_node(
            ProvenanceNode(
                "n1",
                "h1",
                TaintType.WEB_CONTENT,
                TrustLevel.LOW,
                1.0)
        )
        dag.add_node(
            ProvenanceNode(
                "n2",
                "h2",
                TaintType.AGENT_OUTPUT,
                TrustLevel.MEDIUM,
                2.0,
                parent_ids=["n1"],
            )
        )

        chain = dag.get_taint_chain("n2")

        assert TaintType.WEB_CONTENT in chain
        assert TaintType.AGENT_OUTPUT in chain


class TestOriginVerifier:
    """Tests for origin verification."""

    def test_user_input_low_trust(self):
        """User input gets low trust."""
        verifier = OriginVerifier()

        trust, reason = verifier.verify(TaintType.USER_INPUT)

        assert trust == TrustLevel.LOW

    def test_trusted_domain_medium_trust(self):
        """Trusted domain gets medium trust."""
        verifier = OriginVerifier()
        verifier.add_trusted_domain("example.com")

        trust, reason = verifier.verify(
            TaintType.WEB_CONTENT, metadata={"domain": "example.com"}
        )

        assert trust == TrustLevel.MEDIUM

    def test_blocked_source_untrusted(self):
        """Blocked source gets untrusted."""
        verifier = OriginVerifier()
        verifier.block_source("evil.com")

        trust, reason = verifier.verify(
            TaintType.WEB_CONTENT, source_id="evil.com")

        assert trust == TrustLevel.UNTRUSTED


class TestTaintPropagator:
    """Tests for taint propagation."""

    def test_min_trust_propagates(self):
        """Minimum trust propagates."""
        propagator = TaintPropagator()

        taints = [TaintType.USER_INPUT, TaintType.AGENT_OUTPUT]
        trusts = [TrustLevel.LOW, TrustLevel.HIGH]

        _, result_trust = propagator.propagate(taints, trusts)

        assert result_trust == TrustLevel.LOW

    def test_dangerous_taint_propagates(self):
        """Most dangerous taint propagates."""
        propagator = TaintPropagator()

        taints = [TaintType.WEB_CONTENT, TaintType.AGENT_OUTPUT]
        trusts = [TrustLevel.MEDIUM, TrustLevel.MEDIUM]

        result_taint, _ = propagator.propagate(taints, trusts)

        assert result_taint == TaintType.WEB_CONTENT


class TestProvenanceChainTracker:
    """Integration tests."""

    def test_track_single_node(self):
        """Single node tracking works."""
        tracker = ProvenanceChainTracker()

        node_id, result = tracker.track(
            content="Hello world",
            source_type=TaintType.USER_INPUT,
        )

        assert node_id is not None
        assert result.hop_count == 0

    def test_track_chain(self):
        """Chain tracking works."""
        tracker = ProvenanceChainTracker()

        id1, _ = tracker.track("Input", TaintType.USER_INPUT)
        id2, result = tracker.track(
            "Processed", TaintType.AGENT_OUTPUT, parent_ids=[id1]
        )

        assert result.hop_count == 1
        assert len(result.taint_chain) == 2

    def test_hop_limit_exceeded(self):
        """Hop limit violation detected."""
        tracker = ProvenanceChainTracker(max_hops=2)

        id1, _ = tracker.track("1", TaintType.USER_INPUT)
        id2, _ = tracker.track("2", TaintType.AGENT_OUTPUT, parent_ids=[id1])
        id3, _ = tracker.track("3", TaintType.AGENT_OUTPUT, parent_ids=[id2])
        id4, result = tracker.track(
            "4", TaintType.AGENT_OUTPUT, parent_ids=[id3])

        assert result.is_safe is False
        assert "exceeds" in result.violations[0].lower()

    def test_verify_chain(self):
        """Chain verification works."""
        tracker = ProvenanceChainTracker()

        id1, _ = tracker.track("Data", TaintType.USER_INPUT)
        result = tracker.verify_chain(id1)

        assert result.hop_count == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
