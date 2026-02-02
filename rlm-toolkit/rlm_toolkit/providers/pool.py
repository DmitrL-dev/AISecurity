"""
Connection Pooling for LLM Providers.

Manages persistent connections to LLM providers for improved performance.
Reduces connection overhead and enables connection reuse.

Example:
    >>> pool = ConnectionPool(max_size=10)
    >>> async with pool.acquire("openai") as conn:
    ...     response = await conn.generate(prompt)
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Generic, Optional, TypeVar
from collections import defaultdict
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


T = TypeVar('T')


@dataclass
class PooledConnection(Generic[T]):
    """A connection in the pool.

    Attributes:
        connection: The actual connection object
        provider: Provider name
        created_at: Connection creation time
        last_used: Last usage time
        use_count: Number of times used
    """
    connection: T
    provider: str
    created_at: float = field(default_factory=time.time)
    last_used: float = field(default_factory=time.time)
    use_count: int = 0

    @property
    def age_seconds(self) -> float:
        """Connection age in seconds."""
        return time.time() - self.created_at

    @property
    def idle_seconds(self) -> float:
        """Time since last use in seconds."""
        return time.time() - self.last_used

    def touch(self) -> None:
        """Update last used time and increment use count."""
        self.last_used = time.time()
        self.use_count += 1


@dataclass
class PoolConfig:
    """Connection pool configuration.

    Attributes:
        max_size: Maximum connections per provider
        min_size: Minimum connections to maintain
        max_idle_time: Max seconds before idle connection is closed
        max_lifetime: Max seconds before connection is recycled
        acquire_timeout: Max seconds to wait for a connection
    """
    max_size: int = 10
    min_size: int = 1
    max_idle_time: float = 300.0  # 5 minutes
    max_lifetime: float = 3600.0  # 1 hour
    acquire_timeout: float = 30.0


@dataclass
class PoolMetrics:
    """Pool metrics for monitoring."""
    total_connections: int = 0
    available_connections: int = 0
    in_use_connections: int = 0
    total_acquires: int = 0
    total_releases: int = 0
    total_timeouts: int = 0
    total_recycled: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_connections": self.total_connections,
            "available": self.available_connections,
            "in_use": self.in_use_connections,
            "acquires": self.total_acquires,
            "releases": self.total_releases,
            "timeouts": self.total_timeouts,
            "recycled": self.total_recycled,
        }


class ConnectionPool(Generic[T]):
    """Connection pool for LLM providers.

    Manages a pool of connections per provider, with automatic
    lifecycle management and metrics.

    Args:
        config: Pool configuration
        connection_factory: Async function to create connections
        connection_closer: Async function to close connections

    Example:
        >>> async def create_openai():
        ...     return OpenAIClient(api_key=key)
        >>> 
        >>> pool = ConnectionPool(
        ...     connection_factory=create_openai,
        ...     connection_closer=lambda c: c.close()
        ... )
        >>> 
        >>> async with pool.acquire("openai") as client:
        ...     response = await client.complete(prompt)
    """

    def __init__(
        self,
        config: Optional[PoolConfig] = None,
        connection_factory: Optional[Callable[[str], T]] = None,
        connection_closer: Optional[Callable[[T], None]] = None,
    ):
        self.config = config or PoolConfig()
        self._factory = connection_factory
        self._closer = connection_closer

        # Pool state: provider -> list of available connections
        self._available: Dict[str, list] = defaultdict(list)
        # In-use connections: provider -> list of connections
        self._in_use: Dict[str, list] = defaultdict(list)

        self._lock = asyncio.Lock()
        self._metrics = PoolMetrics()
        self._closed = False

    @property
    def metrics(self) -> PoolMetrics:
        """Get pool metrics."""
        self._update_metrics()
        return self._metrics

    def _update_metrics(self) -> None:
        """Update metrics from current state."""
        total_available = sum(len(conns) for conns in self._available.values())
        total_in_use = sum(len(conns) for conns in self._in_use.values())

        self._metrics.available_connections = total_available
        self._metrics.in_use_connections = total_in_use
        self._metrics.total_connections = total_available + total_in_use

    def _should_recycle(self, conn: PooledConnection) -> bool:
        """Check if connection should be recycled."""
        if conn.age_seconds > self.config.max_lifetime:
            return True
        if conn.idle_seconds > self.config.max_idle_time:
            return True
        return False

    async def _create_connection(self, provider: str) -> PooledConnection[T]:
        """Create a new pooled connection."""
        if self._factory:
            # Check if factory is async
            result = self._factory(provider)
            if asyncio.iscoroutine(result):
                connection = await result
            else:
                connection = result
        else:
            # Placeholder connection
            connection = {"provider": provider, "active": True}

        return PooledConnection(
            connection=connection,
            provider=provider,
        )

    async def _close_connection(self, conn: PooledConnection) -> None:
        """Close a pooled connection."""
        if self._closer:
            result = self._closer(conn.connection)
            if asyncio.iscoroutine(result):
                await result
        self._metrics.total_recycled += 1

    async def acquire(self, provider: str) -> T:
        """Acquire a connection from the pool.

        Args:
            provider: Provider name

        Returns:
            Connection object

        Raises:
            TimeoutError: If no connection available within timeout
        """
        if self._closed:
            raise RuntimeError("Pool is closed")

        start_time = time.time()

        async with self._lock:
            # Clean up expired connections
            await self._cleanup_expired(provider)

            # Try to get an available connection
            while self._available[provider]:
                conn = self._available[provider].pop()

                # Check if should recycle
                if self._should_recycle(conn):
                    await self._close_connection(conn)
                    continue

                # Valid connection found
                conn.touch()
                self._in_use[provider].append(conn)
                self._metrics.total_acquires += 1
                return conn.connection

            # Check if we can create a new connection
            current_size = len(self._in_use[provider])
            if current_size < self.config.max_size:
                conn = await self._create_connection(provider)
                conn.touch()
                self._in_use[provider].append(conn)
                self._metrics.total_acquires += 1
                return conn.connection

        # Wait for a connection to become available
        while True:
            elapsed = time.time() - start_time
            if elapsed >= self.config.acquire_timeout:
                self._metrics.total_timeouts += 1
                raise TimeoutError(
                    f"Could not acquire connection for '{provider}' "
                    f"within {self.config.acquire_timeout}s"
                )

            await asyncio.sleep(0.1)

            async with self._lock:
                if self._available[provider]:
                    conn = self._available[provider].pop()
                    if not self._should_recycle(conn):
                        conn.touch()
                        self._in_use[provider].append(conn)
                        self._metrics.total_acquires += 1
                        return conn.connection
                    else:
                        await self._close_connection(conn)

    async def release(self, provider: str, connection: T) -> None:
        """Release a connection back to the pool.

        Args:
            provider: Provider name
            connection: Connection to release
        """
        async with self._lock:
            # Find the pooled connection
            to_remove = None
            for conn in self._in_use[provider]:
                if conn.connection is connection:
                    to_remove = conn
                    break

            if to_remove:
                self._in_use[provider].remove(to_remove)

                # Return to available if not stale
                if not self._should_recycle(to_remove):
                    self._available[provider].append(to_remove)
                else:
                    await self._close_connection(to_remove)

                self._metrics.total_releases += 1

    @asynccontextmanager
    async def connection(self, provider: str):
        """Context manager for acquiring and releasing connections.

        Example:
            >>> async with pool.connection("openai") as conn:
            ...     response = await conn.generate(prompt)
        """
        conn = await self.acquire(provider)
        try:
            yield conn
        finally:
            await self.release(provider, conn)

    async def _cleanup_expired(self, provider: str) -> None:
        """Clean up expired connections for a provider."""
        expired = []
        for conn in self._available[provider]:
            if self._should_recycle(conn):
                expired.append(conn)

        for conn in expired:
            self._available[provider].remove(conn)
            await self._close_connection(conn)

    async def cleanup_all(self) -> int:
        """Clean up all expired connections.

        Returns:
            Number of connections cleaned up
        """
        cleaned = 0
        async with self._lock:
            for provider in list(self._available.keys()):
                before = len(self._available[provider])
                await self._cleanup_expired(provider)
                cleaned += before - len(self._available[provider])
        return cleaned

    async def close(self) -> None:
        """Close the pool and all connections."""
        self._closed = True

        async with self._lock:
            # Close all available connections
            for provider, conns in self._available.items():
                for conn in conns:
                    await self._close_connection(conn)
                conns.clear()

            # Close all in-use connections
            for provider, conns in self._in_use.items():
                for conn in conns:
                    await self._close_connection(conn)
                conns.clear()

        logger.info("Connection pool closed")

    def get_stats(self, provider: Optional[str] = None) -> Dict[str, Any]:
        """Get pool statistics.

        Args:
            provider: Specific provider or None for all

        Returns:
            Pool statistics
        """
        if provider:
            return {
                "provider": provider,
                "available": len(self._available.get(provider, [])),
                "in_use": len(self._in_use.get(provider, set())),
            }

        self._update_metrics()
        return self._metrics.to_dict()


# Global pool instance
_default_pool: Optional[ConnectionPool] = None


def get_connection_pool(config: Optional[PoolConfig] = None) -> ConnectionPool:
    """Get or create the default connection pool.

    Args:
        config: Optional configuration for new pool

    Returns:
        ConnectionPool instance
    """
    global _default_pool
    if _default_pool is None:
        _default_pool = ConnectionPool(config=config)
    return _default_pool


async def close_connection_pool() -> None:
    """Close the default connection pool."""
    global _default_pool
    if _default_pool:
        await _default_pool.close()
        _default_pool = None
