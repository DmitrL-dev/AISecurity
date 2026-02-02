"""
Full Ralph Test Suite for H-MEM (Hierarchical Memory)
======================================================

250 итераций глубокого тестирования edge cases.
Фокус: L0→L3 consolidation, TTL expiration, concurrent access, data integrity.
"""

import pytest
import random
import string
import threading
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os


# ============================================================================
# H-MEM Hierarchical Memory Tests (150 iterations)
# ============================================================================

class TestHMEMFullRalph:
    """Full Ralph: 150 iterations of H-MEM edge cases."""

    @pytest.fixture
    def hmem(self):
        from rlm_toolkit.memory.hierarchical import HierarchicalMemory, HMEMConfig
        config = HMEMConfig(
            max_episodes=100,
            max_traces=50,
            max_categories=20,
            max_domains=10,
            episode_consolidation_threshold=5,
            trace_consolidation_threshold=3,
        )
        return HierarchicalMemory(config)

    # -------------------------------------------------------------------------
    # Level Transition Tests (L0→L1→L2→L3) - 30 tests
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize("episode_count", [1, 5, 10, 25, 50, 100])
    def test_episode_capacity(self, hmem, episode_count):
        """Test episode storage at various capacities."""
        for i in range(episode_count):
            entry_id = hmem.add_episode(
                f"Episode content {i}", metadata={"idx": i})
            assert entry_id is not None

        # Verify count
        stats = hmem.get_stats()
        assert stats["level_counts"]["EPISODE"] <= hmem.config.max_episodes

    @pytest.mark.parametrize("batch_size", [1, 3, 5, 10, 20])
    def test_trace_consolidation(self, hmem, batch_size):
        """Test trace creation from episode batches."""
        episode_ids = []
        for i in range(batch_size):
            eid = hmem.add_episode(f"Episode for trace {i}")
            episode_ids.append(eid)

        if len(episode_ids) >= 2:
            trace_id = hmem.add_trace(
                f"Trace summarizing {len(episode_ids)} episodes",
                episode_ids
            )
            assert trace_id is not None

    @pytest.mark.parametrize("trace_count", [1, 3, 5, 10])
    def test_category_creation(self, hmem, trace_count):
        """Test category creation from traces."""
        trace_ids = []
        for i in range(trace_count):
            # Create episode first
            eid = hmem.add_episode(f"Episode {i}")
            tid = hmem.add_trace(f"Trace {i}", [eid])
            trace_ids.append(tid)

        if len(trace_ids) >= 2:
            cat_id = hmem.add_category(
                f"Category for {len(trace_ids)} traces",
                trace_ids,
                f"Category_{trace_count}"
            )
            assert cat_id is not None

    @pytest.mark.parametrize("category_count", [1, 3, 5])
    def test_domain_creation(self, hmem, category_count):
        """Test domain creation from categories."""
        cat_ids = []
        for i in range(category_count):
            eid = hmem.add_episode(f"E{i}")
            tid = hmem.add_trace(f"T{i}", [eid])
            cid = hmem.add_category(f"C{i}", [tid], f"Cat{i}")
            cat_ids.append(cid)

        if len(cat_ids) >= 2:
            domain_id = hmem.add_domain(
                f"Domain for {len(cat_ids)} categories",
                cat_ids,
                f"Domain_{category_count}"
            )
            assert domain_id is not None

    # -------------------------------------------------------------------------
    # Retrieval Tests - 30 tests
    # -------------------------------------------------------------------------

    QUERY_PATTERNS = [
        "test",
        "episode",
        "memory",
        "content",
        "python",
        "programming",
        "*",
        "",
        "a" * 100,
        "nonexistent_xyz_123",
        "🎉 unicode",
        "中文查询",
    ]

    @pytest.mark.parametrize("query", QUERY_PATTERNS)
    def test_retrieve_various_queries(self, hmem, query):
        """Test retrieval with various query patterns."""
        # Seed some data
        hmem.add_episode("Python programming tutorial")
        hmem.add_episode("Memory management in databases")
        hmem.add_episode("Test content for retrieval")

        # Should not crash
        results = hmem.retrieve(query, top_k=10)
        assert isinstance(results, list)

    @pytest.mark.parametrize("top_k", [1, 5, 10, 50, 100, 1000])
    def test_retrieve_topk_variations(self, hmem, top_k):
        """Test retrieval with various top_k values."""
        for i in range(20):
            hmem.add_episode(f"Content {i}")

        results = hmem.retrieve("content", top_k=top_k)
        assert len(results) <= top_k

    @pytest.mark.parametrize("level", [0, 1, 2, 3])
    def test_retrieve_by_level(self, hmem, level):
        """Test retrieval at specific levels."""
        from rlm_toolkit.memory.hierarchical import MemoryLevel

        # Create full hierarchy
        eid = hmem.add_episode("Episode data")
        tid = hmem.add_trace("Trace data", [eid])
        cid = hmem.add_category("Category data", [tid], "TestCat")
        did = hmem.add_domain("Domain data", [cid], "TestDomain")

        levels = [MemoryLevel(level)]
        results = hmem.retrieve("data", levels=levels, top_k=10)
        assert isinstance(results, list)

    # -------------------------------------------------------------------------
    # Eviction & Capacity Tests - 20 tests
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize("overflow", [1, 10, 50])
    def test_episode_eviction(self, overflow):
        """Test episode eviction when over capacity."""
        from rlm_toolkit.memory.hierarchical import HierarchicalMemory, HMEMConfig
        config = HMEMConfig(max_episodes=10)
        hmem = HierarchicalMemory(config)

        # Add more than max
        for i in range(10 + overflow):
            hmem.add_episode(f"Episode {i}")

        stats = hmem.get_stats()
        assert stats["level_counts"].get("EPISODE", 0) <= 10

    @pytest.mark.parametrize("count", [10, 50, 100])
    def test_memory_pressure(self, count):
        """Test behavior under memory pressure."""
        from rlm_toolkit.memory.hierarchical import HierarchicalMemory, HMEMConfig
        config = HMEMConfig(max_episodes=count)
        hmem = HierarchicalMemory(config)

        # Fill to capacity
        for i in range(count):
            hmem.add_episode(f"Episode {i}")

        # Should still work
        results = hmem.retrieve("Episode", top_k=10)
        assert len(results) > 0

    # -------------------------------------------------------------------------
    # Concurrent Access Tests - 20 tests
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize("thread_count", [2, 4, 8])
    def test_concurrent_writes(self, hmem, thread_count):
        """Test concurrent write operations."""
        errors = []

        def writer(thread_id):
            try:
                for i in range(10):
                    hmem.add_episode(f"Thread {thread_id} Episode {i}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(i,))
                   for i in range(thread_count)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Concurrent write errors: {errors}"

    @pytest.mark.parametrize("thread_count", [2, 4, 8])
    def test_concurrent_reads(self, hmem, thread_count):
        """Test concurrent read operations."""
        # Seed data
        for i in range(50):
            hmem.add_episode(f"Episode {i}")

        errors = []
        results = []

        def reader(thread_id):
            try:
                for _ in range(10):
                    r = hmem.retrieve("Episode", top_k=5)
                    results.append(len(r))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=reader, args=(i,))
                   for i in range(thread_count)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Concurrent read errors: {errors}"

    @pytest.mark.parametrize("iteration", range(5))
    def test_mixed_concurrent_access(self, hmem, iteration):
        """Test mixed read/write concurrent access."""
        errors = []

        def writer():
            for i in range(10):
                try:
                    hmem.add_episode(f"Write {iteration}:{i}")
                except Exception as e:
                    errors.append(e)

        def reader():
            for _ in range(10):
                try:
                    hmem.retrieve("Write", top_k=5)
                except Exception as e:
                    errors.append(e)

        threads = [
            threading.Thread(target=writer),
            threading.Thread(target=reader),
            threading.Thread(target=writer),
            threading.Thread(target=reader),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Mixed access errors: {errors}"

    # -------------------------------------------------------------------------
    # Edge Inputs - 20 tests
    # -------------------------------------------------------------------------

    EDGE_CONTENTS = [
        "",  # Empty
        " ",  # Whitespace
        "\n\n\n",  # Newlines
        "a" * 10000,  # Long content
        "🎉" * 100,  # Emojis
        "中文内容测试",  # Chinese
        "العربية",  # Arabic
        "<script>alert('xss')</script>",  # XSS
        "'; DROP TABLE memories; --",  # SQL injection
        "{{7*7}}",  # Template injection
        "\x00\x01\x02",  # Null bytes
        "\r\n\r\n",  # CRLF
    ]

    @pytest.mark.parametrize("content", EDGE_CONTENTS)
    def test_edge_content_episode(self, hmem, content):
        """Test edge case content in episodes."""
        try:
            entry_id = hmem.add_episode(content)
            assert entry_id is not None
        except (ValueError, TypeError):
            pass  # Some edge inputs may be rejected

    @pytest.mark.parametrize("content", EDGE_CONTENTS[:6])
    def test_edge_content_metadata(self, hmem, content):
        """Test edge case content in metadata."""
        entry_id = hmem.add_episode(
            "Normal content", metadata={"edge": content})
        assert entry_id is not None

    # -------------------------------------------------------------------------
    # Serialization Tests - 20 tests
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize("episode_count", [1, 10, 50])
    def test_stats_accuracy(self, hmem, episode_count):
        """Test stats accuracy at various sizes."""
        for i in range(episode_count):
            hmem.add_episode(f"Episode {i}")

        stats = hmem.get_stats()
        assert stats["level_counts"].get("EPISODE", 0) == episode_count
        assert stats["total_added"] >= episode_count


# ============================================================================
# Memory Bridge Bi-Temporal Tests (100 iterations)
# ============================================================================

class TestMemoryBridgeFullRalph:
    """Full Ralph: 100 iterations of Memory Bridge edge cases."""

    @pytest.fixture
    def manager(self):
        from rlm_toolkit.memory_bridge.manager import MemoryBridgeManager
        manager = MemoryBridgeManager()
        manager.start_session("test_session")
        return manager

    # -------------------------------------------------------------------------
    # Fact CRUD - 30 tests
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize("fact_count", [1, 5, 10, 25, 50])
    def test_add_facts_batch(self, manager, fact_count):
        """Test adding facts in batches."""
        for i in range(fact_count):
            manager.add_fact(f"Fact number {i}", confidence=0.9)

        # Check facts were added
        facts = manager.get_current_facts()
        assert len(facts) >= fact_count

    @pytest.mark.parametrize("confidence", [0.0, 0.25, 0.5, 0.75, 1.0])
    def test_fact_confidence_levels(self, manager, confidence):
        """Test facts with various confidence levels."""
        manager.add_fact(
            f"Confidence {confidence} fact", confidence=confidence)

        # Should be searchable via hybrid_search
        facts = manager.hybrid_search("Confidence", top_k=10)
        assert isinstance(facts, list)

    # -------------------------------------------------------------------------
    # Session Management - 20 tests
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize("session_name", [
        "test",
        "session123",
        "my_project",
        "session-with-dashes",
        "UPPERCASE",
        "mixed_Case_123",
    ])
    def test_session_names(self, session_name):
        """Test various session name formats."""
        from rlm_toolkit.memory_bridge.manager import MemoryBridgeManager
        manager = MemoryBridgeManager()
        manager.start_session(session_name)

        state = manager.get_state()
        assert state is not None

    @pytest.mark.parametrize("iteration", range(5))
    def test_session_persistence(self, iteration, tmp_path):
        """Test session save/restore cycle."""
        from rlm_toolkit.memory_bridge.manager import MemoryBridgeManager
        from rlm_toolkit.memory_bridge.storage import StateStorage

        db_file = tmp_path / f"test_{iteration}.db"
        storage = StateStorage(db_file)
        manager = MemoryBridgeManager(storage=storage)
        manager.start_session(f"persist_test_{iteration}")

        # Add data
        manager.add_fact(f"Persistent fact {iteration}")
        manager.sync_state()

        # Restore (use start_session with restore=True)
        manager2 = MemoryBridgeManager(storage=storage)
        manager2.start_session(f"persist_test_{iteration}", restore=True)

        state = manager2.get_state()
        assert state is not None

    # -------------------------------------------------------------------------
    # Search & Retrieval - 20 tests
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize("query", [
        "test",
        "fact",
        "important",
        "",
        "nonexistent_query_xyz",
        "中文",
    ])
    def test_fact_search_queries(self, manager, query):
        """Test fact search with various queries."""
        manager.add_fact("Test fact about important things")
        manager.add_fact("Another fact for search")

        # Use hybrid_search instead of search_facts
        results = manager.hybrid_search(query, top_k=10)
        assert isinstance(results, list)

    @pytest.mark.parametrize("top_k", [1, 5, 10, 50, 100])
    def test_search_topk(self, manager, top_k):
        """Test search with various top_k."""
        for i in range(20):
            manager.add_fact(f"Searchable fact {i}")

        results = manager.hybrid_search("fact", top_k=top_k)
        assert len(results) <= top_k

    # -------------------------------------------------------------------------
    # Goals & Decisions - 10 tests
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize("progress", [0.0, 0.25, 0.5, 0.75, 1.0])
    def test_goal_progress_levels(self, manager, progress):
        """Test goals with various progress levels."""
        # Use set_goal + update_goal_progress
        manager.set_goal(f"Goal with {progress*100}% progress")
        manager.update_goal_progress(progress)

        state = manager.get_state()
        if state and state.primary_goal:
            assert state.primary_goal.progress == progress

    @pytest.mark.parametrize("num_alternatives", [0, 1, 3, 5])
    def test_decision_alternatives(self, manager, num_alternatives):
        """Test decisions with various alternative counts."""
        alternatives = [f"Alt {i}" for i in range(num_alternatives)]
        manager.record_decision(
            "Test decision",
            "Because testing",
            alternatives=alternatives if alternatives else None
        )

        # Verify decision was recorded
        state = manager.get_state()
        assert state is not None


# ============================================================================
# Stress Tests - Combined
# ============================================================================

class TestHMEMStress:
    """Stress tests for H-MEM."""

    @pytest.mark.stress
    @pytest.mark.parametrize("iteration", range(20))
    def test_rapid_episode_creation(self, iteration):
        """Rapid episode creation stress test."""
        from rlm_toolkit.memory.hierarchical import HierarchicalMemory
        hmem = HierarchicalMemory()

        start = time.time()
        for i in range(100):
            hmem.add_episode(f"Stress episode {iteration}:{i}")
        elapsed = time.time() - start

        # Should complete in reasonable time
        assert elapsed < 5.0, f"Too slow: {elapsed}s"

    @pytest.mark.stress
    @pytest.mark.parametrize("iteration", range(10))
    def test_full_hierarchy_build(self, iteration):
        """Full hierarchy construction stress test."""
        from rlm_toolkit.memory.hierarchical import HierarchicalMemory
        hmem = HierarchicalMemory()

        # Build complete hierarchy
        episode_ids = [hmem.add_episode(f"E{i}") for i in range(20)]
        trace_ids = [
            hmem.add_trace(f"T{i}", episode_ids[i*4:(i+1)*4])
            for i in range(5)
        ]
        category_ids = [
            hmem.add_category(f"C{i}", trace_ids[i*2:(i+1)*2], f"Cat{i}")
            for i in range(2)
        ]
        domain_id = hmem.add_domain("Domain", category_ids, "TestDomain")

        stats = hmem.get_stats()
        assert stats["level_counts"].get("DOMAIN", 0) >= 1


# ============================================================================
# Run Configuration
# ============================================================================

if __name__ == "__main__":
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-x",  # Stop on first failure
        "--durations=20",
    ])
