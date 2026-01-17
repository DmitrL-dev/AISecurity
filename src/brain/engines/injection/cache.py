"""
SENTINEL Brain Injection Engine - Cache Layer

LRU cache for instant decisions on repeated queries.
Extracted from injection.py CacheLayer (lines 76-113).
"""

import hashlib
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

from .models import InjectionResult


class CacheLayer:
    """
    LRU cache for instant decisions on repeated queries.
    
    Provides O(1) lookup for previously analyzed queries,
    dramatically reducing latency for common inputs.
    
    Attributes:
        max_size: Maximum cache entries
        ttl: Time-to-live for cache entries
    """
    
    def __init__(self, max_size: int = 10000, ttl_seconds: int = 300):
        """
        Initialize cache layer.
        
        Args:
            max_size: Maximum number of entries
            ttl_seconds: Entry lifetime in seconds
        """
        self.cache: Dict[str, Tuple[InjectionResult, datetime]] = {}
        self.max_size = max_size
        self.ttl = timedelta(seconds=ttl_seconds)
        
        # Stats
        self.hits = 0
        self.misses = 0
    
    def _hash_query(self, query: str, profile: str) -> str:
        """Create hash key for query+profile."""
        combined = f"{profile}:{query}"
        return hashlib.sha256(combined.encode()).hexdigest()[:32]
    
    def get(self, query: str, profile: str = "standard") -> Optional[InjectionResult]:
        """
        Get cached result.
        
        Args:
            query: Input query
            profile: Security profile
            
        Returns:
            Cached InjectionResult or None if miss/expired
        """
        key = self._hash_query(query, profile)
        
        if key in self.cache:
            result, timestamp = self.cache[key]
            
            # Check TTL
            if datetime.now() - timestamp < self.ttl:
                self.hits += 1
                # Update latency to indicate cache hit
                result.layer = "cache"
                result.latency_ms = 0.1
                return result
            else:
                # Expired - remove
                del self.cache[key]
        
        self.misses += 1
        return None
    
    def put(
        self,
        query: str,
        profile: str,
        result: InjectionResult,
    ) -> None:
        """
        Store result in cache.
        
        Args:
            query: Input query
            profile: Security profile
            result: Detection result to cache
        """
        # Evict oldest if at capacity (simple FIFO for now)
        if len(self.cache) >= self.max_size:
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
        
        key = self._hash_query(query, profile)
        self.cache[key] = (result, datetime.now())
    
    def clear(self) -> None:
        """Clear all cached entries."""
        self.cache.clear()
        self.hits = 0
        self.misses = 0
    
    def stats(self) -> dict:
        """Get cache statistics."""
        total = self.hits + self.misses
        hit_rate = self.hits / total if total > 0 else 0.0
        
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate,
        }
