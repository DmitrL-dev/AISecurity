"""
Performance Benchmarks for Memory Bridge v2.1

Tests performance at scale to validate enterprise readiness.
"""

import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from rlm_toolkit.memory_bridge.v2.hierarchical import (
    HierarchicalMemoryStore,
    MemoryLevel,
)
from rlm_toolkit.memory_bridge.v2.router import SemanticRouter
from rlm_toolkit.memory_bridge.v2.automode import (
    DiscoveryOrchestrator,
    EnterpriseContextBuilder,
)
from rlm_toolkit.memory_bridge.v2.causal import CausalChainTracker
from rlm_toolkit.memory_bridge.v2.coldstart import ColdStartOptimizer


class TestPerformanceBenchmarks:
    """Performance benchmarks for Memory Bridge."""

    @pytest.fixture
    def large_store(self, tmp_path):
        """Create store with many facts."""
        db_path = tmp_path / "bench.db"
        store = HierarchicalMemoryStore(db_path=db_path)
        return store

    def test_add_1000_facts(self, large_store, benchmark):
        """Benchmark: Add 1000 facts."""
        domains = ["api", "auth", "db", "frontend", "backend"]

        def add_facts():
            for i in range(1000):
                large_store.add_fact(
                    content=f"Fact {i} about functionality",
                    level=MemoryLevel.L1_DOMAIN,
                    domain=domains[i % len(domains)],
                )

        benchmark(add_facts)

        stats = large_store.get_stats()
        # Benchmark runs multiple iterations, so total >= 1000
        assert stats["total_facts"] >= 1000

    def test_get_facts_by_domain_1000(self, large_store, benchmark):
        """Benchmark: Query domain with 1000 facts."""
        # Setup
        for i in range(1000):
            large_store.add_fact(
                content=f"API fact number {i}",
                level=MemoryLevel.L1_DOMAIN,
                domain="api",
            )

        def query_domain():
            return large_store.get_domain_facts("api")

        result = benchmark(query_domain)
        assert len(result) == 1000

    def test_route_latency_1000_facts(self, large_store, tmp_path, benchmark):
        """Benchmark: Semantic routing with 1000 facts."""
        # Setup
        domains = ["api", "auth", "db", "frontend", "backend"]
        for i in range(1000):
            large_store.add_fact(
                content=f"Fact about {domains[i % len(domains)]} module {i}",
                level=MemoryLevel.L1_DOMAIN,
                domain=domains[i % len(domains)],
            )

        router = SemanticRouter(store=large_store, max_tokens=2000)

        def route_query():
            return router.route("How does authentication work?")

        result = benchmark(route_query)
        assert result.total_tokens <= 2000

    def test_enterprise_context_latency(self, tmp_path, benchmark):
        """Benchmark: Full enterprise context build."""
        db_path = tmp_path / "enterprise.db"
        store = HierarchicalMemoryStore(db_path=db_path)
        router = SemanticRouter(store=store)
        causal = CausalChainTracker(db_path=tmp_path / "causal.db")
        cold_start = ColdStartOptimizer(store=store, project_root=tmp_path)
        orchestrator = DiscoveryOrchestrator(
            store=store,
            cold_start=cold_start,
            project_root=tmp_path,
        )
        builder = EnterpriseContextBuilder(
            store=store,
            router=router,
            causal_tracker=causal,
            orchestrator=orchestrator,
        )

        # Add some facts
        store.add_fact("Project overview", level=MemoryLevel.L0_PROJECT)
        for i in range(100):
            store.add_fact(
                f"Fact {i}",
                level=MemoryLevel.L1_DOMAIN,
                domain="test",
            )

        def build_context():
            return builder.build(query="How does it work?", max_tokens=2000)

        result = benchmark(build_context)
        assert result.total_tokens <= 2000


class TestScaleValidation:
    """Validate behavior at scale."""

    def test_10k_facts_storage(self, tmp_path):
        """Test storing 10,000 facts."""
        db_path = tmp_path / "10k.db"
        store = HierarchicalMemoryStore(db_path=db_path)

        start = time.perf_counter()

        domains = [
            "api",
            "auth",
            "db",
            "cache",
            "frontend",
            "backend",
            "worker",
            "queue",
            "config",
            "test",
        ]

        for i in range(10000):
            store.add_fact(
                content=f"Enterprise fact {i} with content",
                level=MemoryLevel(i % 4),
                domain=domains[i % len(domains)],
            )

        duration = time.perf_counter() - start

        stats = store.get_stats()
        assert stats["total_facts"] == 10000
        assert stats["domains"] == 10

        # Should complete in reasonable time (120s for slower machines)
        assert duration < 120, f"10K insert took {duration:.1f}s"

        print(f"\n10K facts: {duration:.2f}s ({10000/duration:.0f} facts/sec)")

    def test_query_performance_10k(self, tmp_path):
        """Test query performance with 10K facts."""
        db_path = tmp_path / "query_10k.db"
        store = HierarchicalMemoryStore(db_path=db_path)

        # Insert 10K facts
        for i in range(10000):
            store.add_fact(
                content=f"Fact {i}",
                level=MemoryLevel.L1_DOMAIN,
                domain=f"domain_{i % 100}",
            )

        # Test query speed
        start = time.perf_counter()
        for _ in range(100):
            store.get_domain_facts("domain_50")
        duration = time.perf_counter() - start

        assert duration < 5, f"100 queries took {duration:.1f}s"
        print(f"\n100 domain queries: {duration*1000:.1f}ms total")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--benchmark-only"])
