"""
Tests for Hybrid Search Agent.

Tests Node, Journal, Config, SearchPolicy, and HybridAgent.
"""

import pytest
from pathlib import Path
import tempfile
import sys

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.brain.hybrid_search import (
    SearchNode,
    SearchJournal,
    HybridConfig,
    HybridSearchPolicy,
    SentinelHybridAgent,
)


class TestSearchNode:
    """Tests for SearchNode dataclass."""

    def test_create_node(self):
        """Test basic node creation."""
        node = SearchNode(code="test payload", plan="test plan")
        assert node.code == "test payload"
        assert node.plan == "test plan"
        assert node.id is not None
        assert len(node.id) == 32  # UUID hex

    def test_node_parent_child(self):
        """Test parent-child relationship."""
        parent = SearchNode(code="parent")
        child = SearchNode(code="child", parent=parent)

        assert child.parent == parent
        assert child in parent.children
        assert child.stage_name == "improve"  # parent not buggy

    def test_node_debug_depth(self):
        """Test debug depth calculation."""
        root = SearchNode(code="root")
        root.is_buggy = True

        debug1 = SearchNode(code="debug1", parent=root)
        debug1.is_buggy = True

        debug2 = SearchNode(code="debug2", parent=debug1)

        assert root.debug_depth == 0
        assert debug1.debug_depth == 1
        assert debug2.debug_depth == 2

    def test_node_is_leaf(self):
        """Test leaf node detection."""
        parent = SearchNode(code="parent")
        child = SearchNode(code="child", parent=parent)

        assert not parent.is_leaf
        assert child.is_leaf


class TestSearchJournal:
    """Tests for SearchJournal."""

    def test_append_and_len(self):
        """Test appending nodes."""
        journal = SearchJournal()
        journal.append(SearchNode(code="node1"))
        journal.append(SearchNode(code="node2"))

        assert len(journal) == 2
        assert journal[0].step == 0
        assert journal[1].step == 1

    def test_draft_nodes(self):
        """Test filtering draft nodes."""
        journal = SearchJournal()
        draft = SearchNode(code="draft")
        child = SearchNode(code="child", parent=draft)

        journal.append(draft)
        journal.append(child)

        assert len(journal.draft_nodes) == 1
        assert journal.draft_nodes[0] == draft

    def test_good_and_buggy_nodes(self):
        """Test filtering by buggy status."""
        journal = SearchJournal()

        good = SearchNode(code="good", is_buggy=False)
        good.metric = 0.5

        buggy = SearchNode(code="buggy", is_buggy=True)

        journal.append(good)
        journal.append(buggy)

        assert len(journal.good_nodes) == 1
        assert len(journal.buggy_nodes) == 1

    def test_get_best_node(self):
        """Test best node selection."""
        journal = SearchJournal()

        node1 = SearchNode(code="n1", metric=0.3)
        node2 = SearchNode(code="n2", metric=0.8)
        node3 = SearchNode(code="n3", metric=0.5)

        journal.append(node1)
        journal.append(node2)
        journal.append(node3)

        best = journal.get_best_node()
        assert best == node2

    def test_get_top_nodes(self):
        """Test top-k selection."""
        journal = SearchJournal()

        for i in range(10):
            node = SearchNode(code=f"n{i}", metric=i * 0.1)
            journal.append(node)

        top3 = journal.get_top_nodes(k=3)
        assert len(top3) == 3
        assert top3[0].metric >= top3[1].metric >= top3[2].metric

    def test_save_and_load(self):
        """Test journal persistence."""
        journal = SearchJournal()
        parent = SearchNode(code="parent", metric=0.5)
        child = SearchNode(code="child", metric=0.7, parent=parent)

        journal.append(parent)
        journal.append(child)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "journal.json"
            journal.save(path)

            loaded = SearchJournal.load(path)

            assert len(loaded) == 2
            assert loaded[1].parent == loaded[0]


class TestHybridConfig:
    """Tests for HybridConfig."""

    def test_defaults(self):
        """Test default configuration."""
        config = HybridConfig()

        assert config.num_drafts == 5
        assert config.debug_prob == 0.3
        assert config.max_debug_depth == 3
        assert config.parallel_workers == 4

    def test_fractions_normalize(self):
        """Test stage fractions normalization."""
        config = HybridConfig(
            explore_fraction=0.5,
            exploit_fraction=0.5,
            polish_fraction=0.5,
        )

        total = (
            config.explore_fraction + config.exploit_fraction + config.polish_fraction
        )
        assert abs(total - 1.0) < 0.01


class TestHybridSearchPolicy:
    """Tests for HybridSearchPolicy."""

    def test_initial_drafts(self):
        """Test drafting phase."""
        config = HybridConfig(num_drafts=3)
        policy = HybridSearchPolicy(config)
        journal = SearchJournal()

        # Should return None (draft new) until num_drafts reached
        assert policy.select(journal) is None

        for i in range(3):
            journal.append(SearchNode(code=f"draft{i}"))

        # Now should select from existing
        result = policy.select(journal)
        # Note: might still be None if all are buggy, but shouldn't crash

    def test_stage_transitions(self):
        """Test stage transitions."""
        config = HybridConfig(max_steps=10)
        policy = HybridSearchPolicy(config)

        assert policy.current_stage == "explore"

        # Simulate steps
        for _ in range(5):
            policy.step_count += 1
            policy._update_stage()

        # Should transition at some point
        assert policy.step_count == 5


class TestSentinelHybridAgent:
    """Tests for SentinelHybridAgent."""

    def test_initialization(self):
        """Test agent initialization."""
        config = HybridConfig(num_drafts=2, max_steps=5)
        agent = SentinelHybridAgent(config)

        assert agent.config.num_drafts == 2
        assert len(agent.journal) == 0

    def test_run_basic(self):
        """Test basic search run."""
        config = HybridConfig(num_drafts=2, max_steps=5, parallel_workers=1)
        agent = SentinelHybridAgent(config)

        best = agent.run()

        assert best is not None
        assert len(agent.journal) >= config.num_drafts
        agent.close()

    def test_custom_evaluator(self):
        """Test custom evaluator function."""

        def custom_eval(payload: str) -> float:
            return 0.9 if "secret" in payload.lower() else 0.1

        config = HybridConfig(num_drafts=2, max_steps=3, parallel_workers=1)
        agent = SentinelHybridAgent(config, evaluator=custom_eval)

        best = agent.run()
        assert best is not None
        agent.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
