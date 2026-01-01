"""
Unit tests for Causal Inference Detector.
"""

import pytest
from engines.causal_inference_detector import (
    CausalInferenceDetector,
    CausalGraph,
    CausalLearner,
    ChainDetector,
    CausalNode,
    CausalEdge,
    CausalRelation,
)


class TestCausalGraph:
    """Tests for causal graph."""

    def test_add_node(self):
        """Can add node."""
        graph = CausalGraph()
        node = CausalNode("n1", "test")

        graph.add_node(node)

        assert "n1" in graph._nodes

    def test_add_edge(self):
        """Can add edge."""
        graph = CausalGraph()
        edge = CausalEdge("n1", "n2", CausalRelation.CAUSES)

        graph.add_edge(edge)

        assert graph.get_children("n1") == ["n2"]

    def test_find_path(self):
        """Path finding works."""
        graph = CausalGraph()
        graph.add_node(CausalNode("a", "t"))
        graph.add_node(CausalNode("b", "t"))
        graph.add_node(CausalNode("c", "t"))
        graph.add_edge(CausalEdge("a", "b", CausalRelation.CAUSES))
        graph.add_edge(CausalEdge("b", "c", CausalRelation.CAUSES))

        path = graph.find_path("a", "c")

        assert path == ["a", "b", "c"]


class TestCausalLearner:
    """Tests for causal learner."""

    def test_learn_from_sequence(self):
        """Learning from sequence works."""
        learner = CausalLearner()

        graph = learner.learn_from_sequence(["event1", "event2"])

        assert len(graph._nodes) == 2
        assert len(graph._edges) == 1

    def test_classify_attack_event(self):
        """Attack events classified correctly."""
        learner = CausalLearner()

        event_type = learner._classify_event("inject malicious code")

        assert event_type == "exploit"


class TestCausalInferenceDetector:
    """Integration tests."""

    def test_benign_sequence(self):
        """Benign sequence no chain."""
        detector = CausalInferenceDetector()

        result = detector.analyze(["hello", "world", "test"])

        assert result.is_attack_chain is False

    def test_attack_chain_detected(self):
        """Attack chain detected."""
        detector = CausalInferenceDetector()

        events = [
            "scan the system",
            "inject payload",
            "elevate privileges",
        ]
        result = detector.analyze(events)

        assert result.is_attack_chain is True
        assert result.chain_length > 0

    def test_has_root_cause(self):
        """Result has root cause."""
        detector = CausalInferenceDetector()

        result = detector.analyze(["event1", "event2"])

        assert result.root_cause != ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
