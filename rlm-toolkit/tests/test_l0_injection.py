"""
TDD Tests for L0 Auto-Injection (RLM Critical Gap Fix)

Tests written FIRST per TDD Iron Law.
These tests define the expected behavior for:
1. get_l0_context() - returns formatted L0 facts for injection
2. Auto-embedding generation on add_fact()
3. Enforcement check for pre-implementation validation
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from rlm_toolkit.memory_bridge.v2.hierarchical import (
    MemoryLevel,
    HierarchicalMemoryStore,
)


class TestL0AutoInjection:
    """Tests for L0 context auto-injection."""

    @pytest.fixture
    def store(self, tmp_path):
        """Create a temporary store."""
        db_path = tmp_path / "test_l0_injection.db"
        return HierarchicalMemoryStore(db_path=db_path)

    def test_get_l0_context_returns_string(self, store):
        """L0 context should return a formatted string for injection."""
        # Add L0 facts
        store.add_fact(
            "TDD IRON LAW: Tests must be written before implementation.",
            level=MemoryLevel.L0_PROJECT,
            domain="development",
        )
        store.add_fact(
            "Project uses Python 3.11 with FastAPI.",
            level=MemoryLevel.L0_PROJECT,
        )

        # Method under test
        context = store.get_l0_context()

        assert isinstance(context, str)
        assert "TDD IRON LAW" in context
        assert "Python 3.11" in context

    def test_get_l0_context_empty_store(self, store):
        """Empty store should return empty or default L0 context."""
        context = store.get_l0_context()

        assert isinstance(context, str)
        # May be empty or contain a header

    def test_get_l0_context_ignores_other_levels(self, store):
        """L0 context should NOT include L1, L2, L3 facts."""
        store.add_fact(
            "L0 Project Rule",
            level=MemoryLevel.L0_PROJECT,
        )
        store.add_fact(
            "L1 Domain Fact",
            level=MemoryLevel.L1_DOMAIN,
            domain="api",
        )
        store.add_fact(
            "L2 Module Fact",
            level=MemoryLevel.L2_MODULE,
            domain="api",
            module="routes",
        )

        context = store.get_l0_context()

        assert "L0 Project Rule" in context
        assert "L1 Domain Fact" not in context
        assert "L2 Module Fact" not in context

    def test_get_l0_context_with_max_tokens(self, store):
        """L0 context should respect token budget."""
        # Add many L0 facts
        for i in range(20):
            store.add_fact(
                f"Project rule number {i}: " + "word " * 50,
                level=MemoryLevel.L0_PROJECT,
            )

        context = store.get_l0_context(max_tokens=500)

        # Rough check: 500 tokens ≈ 2000 chars
        assert len(context) < 3000


class TestAutoEmbeddingGeneration:
    """Tests for automatic embedding generation on add_fact."""

    @pytest.fixture
    def store(self, tmp_path):
        """Create a temporary store."""
        db_path = tmp_path / "test_auto_embed.db"
        return HierarchicalMemoryStore(db_path=db_path)

    def test_add_fact_generates_embedding_when_embedder_available(self, store):
        """When embedder is available, add_fact should generate embedding."""
        # Mock embedder
        mock_embedder = MagicMock()
        mock_embedder.encode.return_value = [0.1] * 384  # MiniLM dimension
        store.set_embedder(mock_embedder)

        fact_id = store.add_fact(
            "New fact that needs embedding",
            level=MemoryLevel.L1_DOMAIN,
            domain="test",
        )

        # Verify embedding was generated
        fact = store.get_fact(fact_id)
        assert fact.embedding is not None
        assert len(fact.embedding) == 384
        mock_embedder.encode.assert_called_once()

    def test_add_fact_works_without_embedder(self, store):
        """Without embedder, add_fact should still work (embedding = None)."""
        fact_id = store.add_fact(
            "Fact without embedding",
            level=MemoryLevel.L0_PROJECT,
        )

        fact = store.get_fact(fact_id)
        assert fact_id is not None
        assert fact.embedding is None

    def test_stats_show_embeddings_count(self, store):
        """Stats should report number of facts with embeddings."""
        # Add fact with embedding
        embedding = [0.1] * 384
        store.add_fact(
            "Fact with embedding",
            level=MemoryLevel.L0_PROJECT,
            embedding=embedding,
        )

        stats = store.get_stats()
        assert stats["with_embeddings"] >= 1


class TestEnforcementCheck:
    """Tests for pre-implementation enforcement checks."""

    @pytest.fixture
    def store(self, tmp_path):
        """Create a store with enforcement rules."""
        db_path = tmp_path / "test_enforcement.db"
        store = HierarchicalMemoryStore(db_path=db_path)

        # Add TDD Iron Law
        store.add_fact(
            "TDD IRON LAW: Before ANY code implementation, tests MUST be written first. No exceptions.",
            level=MemoryLevel.L0_PROJECT,
            domain="development",
        )
        return store

    def test_check_before_implementation_returns_warnings(self, store):
        """Enforcement check should return warnings based on L0 rules."""
        warnings = store.check_before_implementation(
            task_description="Implement new user registration module"
        )

        assert isinstance(warnings, list)
        # Should have TDD warning for implementation task
        tdd_warnings = [w for w in warnings if "TDD" in w or "test" in w.lower()]
        assert len(tdd_warnings) >= 1

    def test_check_before_implementation_no_warning_for_tests(self, store):
        """No TDD warning when task is about writing tests."""
        warnings = store.check_before_implementation(
            task_description="Write unit tests for user registration"
        )

        # May still return info, but should not block
        blocking = [w for w in warnings if "MUST" in w]
        assert len(blocking) == 0 or "test" not in str(blocking).lower()

    def test_check_before_implementation_empty_store(self, tmp_path):
        """Empty store should return no enforcement warnings."""
        db_path = tmp_path / "test_empty.db"
        store = HierarchicalMemoryStore(db_path=db_path)

        warnings = store.check_before_implementation(
            task_description="Implement new feature"
        )

        assert isinstance(warnings, list)
        # No L0 rules = no warnings
        assert len(warnings) == 0


class TestDefaultTTL:
    """TDD Tests for default TTL on L2/L3 facts."""

    @pytest.fixture
    def store(self, tmp_path):
        """Create a temporary store."""
        db_path = tmp_path / "test_ttl.db"
        return HierarchicalMemoryStore(db_path=db_path)

    def test_l2_fact_gets_default_ttl(self, store):
        """L2 facts should get 30-day TTL by default."""
        fact_id = store.add_fact(
            "Module-specific fact",
            level=MemoryLevel.L2_MODULE,
            domain="api",
            module="routes",
        )

        fact = store.get_fact(fact_id)
        assert fact.ttl_config is not None
        # 30 days = 30 * 24 * 3600 = 2592000 seconds
        assert fact.ttl_config.ttl_seconds == 30 * 24 * 3600

    def test_l3_fact_gets_default_ttl(self, store):
        """L3 facts should get 7-day TTL by default."""
        fact_id = store.add_fact(
            "Code-specific fact",
            level=MemoryLevel.L3_CODE,
            domain="api",
            module="routes",
            code_ref="file:///path/to/file.py#L10",
        )

        fact = store.get_fact(fact_id)
        assert fact.ttl_config is not None
        # 7 days = 7 * 24 * 3600 = 604800 seconds
        assert fact.ttl_config.ttl_seconds == 7 * 24 * 3600

    def test_l0_l1_no_default_ttl(self, store):
        """L0 and L1 facts should NOT get default TTL."""
        l0_id = store.add_fact("Project rule", level=MemoryLevel.L0_PROJECT)
        l1_id = store.add_fact(
            "Domain fact",
            level=MemoryLevel.L1_DOMAIN,
            domain="api",
        )

        l0_fact = store.get_fact(l0_id)
        l1_fact = store.get_fact(l1_id)

        assert l0_fact.ttl_config is None
        assert l1_fact.ttl_config is None

    def test_explicit_ttl_overrides_default(self, store):
        """Explicit TTL should override default."""
        from rlm_toolkit.memory_bridge.v2.hierarchical import TTLConfig

        custom_ttl = TTLConfig(ttl_seconds=3600)  # 1 hour

        fact_id = store.add_fact(
            "Custom TTL fact",
            level=MemoryLevel.L2_MODULE,
            domain="api",
            module="routes",
            ttl_config=custom_ttl,
        )

        fact = store.get_fact(fact_id)
        assert fact.ttl_config.ttl_seconds == 3600
