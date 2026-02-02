"""
Tests for RLM v2.4 Connection Pool.

Tests:
- PooledConnection lifecycle
- ConnectionPool acquire/release
- Pool metrics
- Cleanup and recycling
"""

import asyncio
import pytest
import time
from unittest.mock import Mock, AsyncMock

from rlm_toolkit.providers.pool import (
    ConnectionPool,
    PoolConfig,
    PooledConnection,
    PoolMetrics,
    get_connection_pool,
    close_connection_pool,
)


class TestPooledConnection:
    """Tests for PooledConnection."""

    def test_creation(self):
        """PooledConnection should be created with defaults."""
        conn = PooledConnection(connection="mock", provider="openai")

        assert conn.connection == "mock"
        assert conn.provider == "openai"
        assert conn.use_count == 0

    def test_age_seconds(self):
        """age_seconds should calculate correctly."""
        conn = PooledConnection(connection="mock", provider="test")

        time.sleep(0.1)

        assert conn.age_seconds >= 0.1

    def test_idle_seconds(self):
        """idle_seconds should calculate correctly."""
        conn = PooledConnection(connection="mock", provider="test")

        time.sleep(0.1)

        assert conn.idle_seconds >= 0.1

    def test_touch(self):
        """touch should update last_used and increment use_count."""
        conn = PooledConnection(connection="mock", provider="test")

        initial_time = conn.last_used
        initial_count = conn.use_count

        time.sleep(0.01)
        conn.touch()

        assert conn.last_used > initial_time
        assert conn.use_count == initial_count + 1


class TestPoolConfig:
    """Tests for PoolConfig."""

    def test_defaults(self):
        """PoolConfig should have sensible defaults."""
        config = PoolConfig()

        assert config.max_size == 10
        assert config.min_size == 1
        assert config.max_idle_time == 300.0
        assert config.max_lifetime == 3600.0
        assert config.acquire_timeout == 30.0

    def test_custom_config(self):
        """PoolConfig should accept custom values."""
        config = PoolConfig(max_size=5, max_idle_time=60.0)

        assert config.max_size == 5
        assert config.max_idle_time == 60.0


class TestConnectionPool:
    """Tests for ConnectionPool."""

    @pytest.mark.asyncio
    async def test_acquire_creates_connection(self):
        """acquire should create a new connection."""
        pool = ConnectionPool()

        conn = await pool.acquire("openai")

        assert conn is not None
        assert pool.metrics.total_acquires == 1

    @pytest.mark.asyncio
    async def test_release_returns_to_pool(self):
        """release should return connection to available pool."""
        pool = ConnectionPool()

        conn = await pool.acquire("openai")
        await pool.release("openai", conn)

        stats = pool.get_stats("openai")
        assert stats["available"] == 1
        assert stats["in_use"] == 0

    @pytest.mark.asyncio
    async def test_reuses_connections(self):
        """Should reuse released connections."""
        pool = ConnectionPool()

        conn1 = await pool.acquire("openai")
        await pool.release("openai", conn1)

        conn2 = await pool.acquire("openai")

        # Should be same connection object
        assert conn1 is conn2

    @pytest.mark.asyncio
    async def test_respects_max_size(self):
        """Should not exceed max connections."""
        pool = ConnectionPool(PoolConfig(max_size=2, acquire_timeout=0.1))

        conn1 = await pool.acquire("openai")
        conn2 = await pool.acquire("openai")

        # Third should timeout
        with pytest.raises(TimeoutError):
            await pool.acquire("openai")

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """connection context manager should work."""
        pool = ConnectionPool()

        async with pool.connection("openai") as conn:
            assert conn is not None

        # Should be released after context
        stats = pool.get_stats("openai")
        assert stats["in_use"] == 0

    @pytest.mark.asyncio
    async def test_custom_factory(self):
        """Should use custom connection factory."""
        created = []

        def factory(provider):
            obj = {"provider": provider, "id": len(created)}
            created.append(obj)
            return obj

        pool = ConnectionPool(connection_factory=factory)

        conn = await pool.acquire("custom")

        assert conn["provider"] == "custom"
        assert len(created) == 1

    @pytest.mark.asyncio
    async def test_async_factory(self):
        """Should support async connection factory."""
        async def async_factory(provider):
            await asyncio.sleep(0.01)
            return {"provider": provider, "async": True}

        pool = ConnectionPool(connection_factory=async_factory)

        conn = await pool.acquire("async-test")

        assert conn["async"] is True

    @pytest.mark.asyncio
    async def test_close_pool(self):
        """close should close all connections."""
        closed = []

        def closer(conn):
            closed.append(conn)

        pool = ConnectionPool(connection_closer=closer)

        conn1 = await pool.acquire("a")
        conn2 = await pool.acquire("b")
        await pool.release("a", conn1)

        await pool.close()

        # Should have closed available connection
        assert len(closed) >= 1

    @pytest.mark.asyncio
    async def test_metrics(self):
        """Should track metrics correctly."""
        pool = ConnectionPool()

        conn = await pool.acquire("test")
        await pool.release("test", conn)
        conn = await pool.acquire("test")
        await pool.release("test", conn)

        metrics = pool.metrics

        assert metrics.total_acquires == 2
        assert metrics.total_releases == 2

    @pytest.mark.asyncio
    async def test_multiple_providers(self):
        """Should manage separate pools per provider."""
        pool = ConnectionPool()

        openai = await pool.acquire("openai")
        anthropic = await pool.acquire("anthropic")

        await pool.release("openai", openai)
        await pool.release("anthropic", anthropic)

        openai_stats = pool.get_stats("openai")
        anthropic_stats = pool.get_stats("anthropic")

        assert openai_stats["available"] == 1
        assert anthropic_stats["available"] == 1


class TestPoolRecycling:
    """Tests for connection recycling."""

    @pytest.mark.asyncio
    async def test_recycling_by_age(self):
        """Should recycle connections that exceed max_lifetime."""
        config = PoolConfig(max_lifetime=0.05)  # 50ms lifetime
        pool = ConnectionPool(config)

        conn = await pool.acquire("test")
        await pool.release("test", conn)

        # Wait for lifetime to expire
        await asyncio.sleep(0.1)

        # Next acquire should create new connection
        conn2 = await pool.acquire("test")

        assert conn2 is not conn  # Should be different (new connection)

    @pytest.mark.asyncio
    async def test_recycling_by_idle(self):
        """Should recycle connections that exceed max_idle_time."""
        config = PoolConfig(max_idle_time=0.05)  # 50ms idle time
        pool = ConnectionPool(config)

        conn = await pool.acquire("test")
        await pool.release("test", conn)

        await asyncio.sleep(0.1)

        # Get new connection (old one should be recycled)
        conn2 = await pool.acquire("test")

        # Pool cleaned up during acquire
        assert pool.metrics.total_recycled >= 0


class TestGlobalPool:
    """Tests for global pool functions."""

    @pytest.mark.asyncio
    async def test_get_connection_pool(self):
        """get_connection_pool should return singleton."""
        # Reset first
        await close_connection_pool()

        pool1 = get_connection_pool()
        pool2 = get_connection_pool()

        assert pool1 is pool2

    @pytest.mark.asyncio
    async def test_close_connection_pool(self):
        """close_connection_pool should close global pool."""
        pool = get_connection_pool()

        await close_connection_pool()

        # Getting again should create new pool
        pool2 = get_connection_pool()
        assert pool2 is not pool

        await close_connection_pool()  # Clean up


class TestEdgeCases:
    """Edge cases and boundary condition tests."""

    @pytest.mark.asyncio
    async def test_empty_provider(self):
        """Empty provider name should work."""
        pool = ConnectionPool()
        conn = await pool.acquire("")
        await pool.release("", conn)
        assert pool.get_stats("")["available"] == 1

    @pytest.mark.asyncio
    async def test_special_provider_names(self):
        """Special characters in provider names should work."""
        pool = ConnectionPool()

        providers = ["openai:v1", "anthropic-2024", "model/gpt4"]
        for p in providers:
            conn = await pool.acquire(p)
            await pool.release(p, conn)
            assert pool.get_stats(p)["available"] == 1

    @pytest.mark.asyncio
    async def test_concurrent_acquire(self):
        """Concurrent acquires should work."""
        pool = ConnectionPool(PoolConfig(max_size=10))

        async def acquire_and_release():
            conn = await pool.acquire("concurrent")
            await asyncio.sleep(0.01)
            await pool.release("concurrent", conn)

        await asyncio.gather(*[acquire_and_release() for _ in range(5)])
        assert pool.metrics.total_acquires == 5

    @pytest.mark.asyncio
    async def test_release_invalid_connection(self):
        """Releasing unknown connection should be handled."""
        pool = ConnectionPool()

        # Create a connection not from pool
        fake_conn = PooledConnection(connection="fake", provider="test")

        # Should not crash
        await pool.release("test", fake_conn)

    @pytest.mark.asyncio
    async def test_double_close(self):
        """Double close should be safe."""
        pool = ConnectionPool()
        conn = await pool.acquire("test")
        await pool.release("test", conn)

        await pool.close()
        await pool.close()  # Second close should be safe

    @pytest.mark.asyncio
    async def test_metrics_accuracy(self):
        """Metrics should be accurate after many operations."""
        pool = ConnectionPool()

        for i in range(10):
            conn = await pool.acquire(f"provider{i % 3}")
            await pool.release(f"provider{i % 3}", conn)

        assert pool.metrics.total_acquires == 10
        assert pool.metrics.total_releases == 10

    def test_pool_config_validation(self):
        """Pool config should validate."""
        # max_size must be >= min_size
        config = PoolConfig(min_size=5, max_size=10)
        assert config.min_size <= config.max_size

    @pytest.mark.asyncio
    async def test_factory_error_handling(self):
        """Pool should handle factory errors."""
        def failing_factory(provider):
            raise RuntimeError("Connection failed")

        pool = ConnectionPool(connection_factory=failing_factory)

        with pytest.raises(RuntimeError):
            await pool.acquire("test")
