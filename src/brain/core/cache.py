"""
SENTINEL Brain - Redis Cache Layer

High-performance caching with Redis support.
Fallback to in-memory LRU if Redis unavailable.
"""

import hashlib
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class CacheConfig:
    """Cache configuration."""
    
    def __init__(
        self,
        redis_url: str = None,
        default_ttl: int = 300,
        max_memory_items: int = 10000,
        prefix: str = "sentinel:",
    ):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.default_ttl = default_ttl
        self.max_memory_items = max_memory_items
        self.prefix = prefix


class MemoryCache:
    """In-memory LRU cache fallback."""
    
    def __init__(self, max_size: int = 10000, default_ttl: int = 300):
        self.max_size = max_size
        self.default_ttl = timedelta(seconds=default_ttl)
        self._cache: Dict[str, tuple] = {}  # key -> (value, expires_at)
        self.hits = 0
        self.misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if key in self._cache:
            value, expires_at = self._cache[key]
            if datetime.now() < expires_at:
                self.hits += 1
                return value
            else:
                del self._cache[key]
        self.misses += 1
        return None
    
    def set(self, key: str, value: Any, ttl: int = None) -> None:
        """Set value in cache."""
        if len(self._cache) >= self.max_size:
            # Evict oldest
            oldest = next(iter(self._cache))
            del self._cache[oldest]
        
        ttl_delta = timedelta(seconds=ttl) if ttl else self.default_ttl
        self._cache[key] = (value, datetime.now() + ttl_delta)
    
    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if key in self._cache:
            del self._cache[key]
            return True
        return False
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
        self.hits = 0
        self.misses = 0
    
    def stats(self) -> dict:
        """Get cache statistics."""
        total = self.hits + self.misses
        return {
            "type": "memory",
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": self.hits / total if total > 0 else 0.0,
        }


class RedisCache:
    """Redis-backed cache."""
    
    def __init__(self, config: CacheConfig):
        self.config = config
        self._client = None
        self._connected = False
        self._connect()
    
    def _connect(self) -> None:
        """Connect to Redis."""
        try:
            import redis
            self._client = redis.from_url(
                self.config.redis_url,
                decode_responses=True,
            )
            self._client.ping()
            self._connected = True
            logger.info(f"Connected to Redis: {self.config.redis_url}")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            self._connected = False
    
    @property
    def is_connected(self) -> bool:
        """Check if connected to Redis."""
        if not self._connected or not self._client:
            return False
        try:
            self._client.ping()
            return True
        except Exception:
            self._connected = False
            return False
    
    def _make_key(self, key: str) -> str:
        """Create prefixed key."""
        return f"{self.config.prefix}{key}"
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from Redis."""
        if not self.is_connected:
            return None
        
        try:
            full_key = self._make_key(key)
            data = self._client.get(full_key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.debug(f"Redis get error: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """Set value in Redis."""
        if not self.is_connected:
            return False
        
        try:
            full_key = self._make_key(key)
            ttl = ttl or self.config.default_ttl
            data = json.dumps(value)
            self._client.setex(full_key, ttl, data)
            return True
        except Exception as e:
            logger.debug(f"Redis set error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from Redis."""
        if not self.is_connected:
            return False
        
        try:
            full_key = self._make_key(key)
            return self._client.delete(full_key) > 0
        except Exception:
            return False
    
    def clear(self, pattern: str = "*") -> int:
        """Clear keys matching pattern."""
        if not self.is_connected:
            return 0
        
        try:
            full_pattern = self._make_key(pattern)
            keys = self._client.keys(full_pattern)
            if keys:
                return self._client.delete(*keys)
            return 0
        except Exception:
            return 0
    
    def stats(self) -> dict:
        """Get Redis statistics."""
        if not self.is_connected:
            return {"type": "redis", "connected": False}
        
        try:
            info = self._client.info("stats")
            return {
                "type": "redis",
                "connected": True,
                "hits": info.get("keyspace_hits", 0),
                "misses": info.get("keyspace_misses", 0),
                "keys": self._client.dbsize(),
            }
        except Exception:
            return {"type": "redis", "connected": False}


class HybridCache:
    """
    Hybrid cache: Redis primary, memory fallback.
    
    Provides high availability by falling back to
    in-memory cache when Redis is unavailable.
    """
    
    def __init__(self, config: CacheConfig = None):
        self.config = config or CacheConfig()
        self.redis = RedisCache(self.config)
        self.memory = MemoryCache(
            max_size=self.config.max_memory_items,
            default_ttl=self.config.default_ttl,
        )
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache (Redis first, then memory)."""
        # Try Redis first
        if self.redis.is_connected:
            value = self.redis.get(key)
            if value is not None:
                return value
        
        # Fallback to memory
        return self.memory.get(key)
    
    def set(self, key: str, value: Any, ttl: int = None) -> None:
        """Set value in both caches."""
        # Set in Redis
        if self.redis.is_connected:
            self.redis.set(key, value, ttl)
        
        # Also set in memory for fast access
        self.memory.set(key, value, ttl)
    
    def delete(self, key: str) -> bool:
        """Delete from both caches."""
        redis_result = self.redis.delete(key) if self.redis.is_connected else False
        memory_result = self.memory.delete(key)
        return redis_result or memory_result
    
    def clear(self) -> None:
        """Clear both caches."""
        if self.redis.is_connected:
            self.redis.clear()
        self.memory.clear()
    
    def stats(self) -> dict:
        """Get combined statistics."""
        return {
            "redis": self.redis.stats(),
            "memory": self.memory.stats(),
        }


# Global cache instance
_cache: Optional[HybridCache] = None


def get_cache() -> HybridCache:
    """Get global cache instance."""
    global _cache
    if _cache is None:
        _cache = HybridCache()
    return _cache


def cache_key(*args, **kwargs) -> str:
    """Generate cache key from arguments."""
    parts = [str(a) for a in args]
    parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
    combined = ":".join(parts)
    return hashlib.sha256(combined.encode()).hexdigest()[:32]
