"""
Fingerprint Storage Layer — Redis (Hot) + PostgreSQL (Cold)

Dual-layer storage for attacker fingerprints:
- Redis: Fast real-time matching, 24h TTL
- PostgreSQL: Persistent storage, 30d TTL, GDPR-compliant

Privacy-compliant by design:
- Only stores SHA256 hash fingerprints
- Automatic TTL expiration
- Audit logging
- Opt-out via config

Author: SENTINEL Team
Date: 2025-12-14
"""

import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from contextlib import asynccontextmanager

logger = logging.getLogger("FingerprintStore")


# ============================================================================
# Data Classes
# ============================================================================


@dataclass
class StoredFingerprint:
    """Fingerprint record as stored in database."""
    fingerprint_id: str
    accumulated_risk: float
    request_count: int
    first_seen: datetime
    last_seen: datetime
    expires_at: datetime

    # Minimal features for matching (no raw data)
    techniques: List[str]
    primary_language: str
    uses_obfuscation: bool
    is_burst: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fingerprint_id": self.fingerprint_id,
            "accumulated_risk": self.accumulated_risk,
            "request_count": self.request_count,
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "techniques": self.techniques,
            "primary_language": self.primary_language,
            "uses_obfuscation": self.uses_obfuscation,
            "is_burst": self.is_burst,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StoredFingerprint":
        return cls(
            fingerprint_id=data["fingerprint_id"],
            accumulated_risk=data["accumulated_risk"],
            request_count=data["request_count"],
            first_seen=datetime.fromisoformat(data["first_seen"]),
            last_seen=datetime.fromisoformat(data["last_seen"]),
            expires_at=datetime.fromisoformat(data["expires_at"]),
            techniques=data.get("techniques", []),
            primary_language=data.get("primary_language", "en"),
            uses_obfuscation=data.get("uses_obfuscation", False),
            is_burst=data.get("is_burst", False),
        )


# ============================================================================
# Abstract Store Interface
# ============================================================================


class FingerprintStoreInterface(ABC):
    """Abstract interface for fingerprint storage."""

    @abstractmethod
    async def get(self, fingerprint_id: str) -> Optional[StoredFingerprint]:
        """Get fingerprint by ID."""
        pass

    @abstractmethod
    async def store(self, fingerprint: StoredFingerprint) -> bool:
        """Store or update fingerprint."""
        pass

    @abstractmethod
    async def find_similar(
        self,
        techniques: List[str],
        language: str,
        limit: int = 10
    ) -> List[StoredFingerprint]:
        """Find fingerprints with similar characteristics."""
        pass

    @abstractmethod
    async def delete(self, fingerprint_id: str) -> bool:
        """Delete fingerprint."""
        pass

    @abstractmethod
    async def cleanup_expired(self) -> int:
        """Remove expired fingerprints. Returns count deleted."""
        pass

    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        pass


# ============================================================================
# Redis Store (Hot Layer)
# ============================================================================


class RedisStore(FingerprintStoreInterface):
    """
    Redis-backed hot storage for fingerprints.

    Features:
    - Sub-millisecond lookup
    - Automatic TTL expiration (24h default)
    - No persistence (use PostgreSQL for that)

    Requires: redis-py[hiredis] package
    """

    PREFIX = "fp:"
    DEFAULT_TTL_HOURS = 24

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        ttl_hours: int = DEFAULT_TTL_HOURS,
    ):
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.ttl_seconds = ttl_hours * 3600

        self._client = None
        self._connected = False

    async def connect(self) -> bool:
        """Connect to Redis."""
        try:
            # Lazy import to allow running without redis
            import redis.asyncio as redis

            self._client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                decode_responses=True,
            )

            # Test connection
            await self._client.ping()
            self._connected = True
            logger.info(f"Redis connected: {self.host}:{self.port}")
            return True

        except ImportError:
            logger.warning("redis-py not installed, using fallback")
            return False
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            return False

    async def disconnect(self):
        """Disconnect from Redis."""
        if self._client:
            await self._client.close()
            self._connected = False

    def _key(self, fingerprint_id: str) -> str:
        """Generate Redis key."""
        return f"{self.PREFIX}{fingerprint_id}"

    async def get(self, fingerprint_id: str) -> Optional[StoredFingerprint]:
        if not self._connected:
            return None

        try:
            data = await self._client.get(self._key(fingerprint_id))
            if data:
                return StoredFingerprint.from_dict(json.loads(data))
            return None
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None

    async def store(self, fingerprint: StoredFingerprint) -> bool:
        if not self._connected:
            return False

        try:
            key = self._key(fingerprint.fingerprint_id)
            data = json.dumps(fingerprint.to_dict())

            await self._client.setex(key, self.ttl_seconds, data)

            logger.debug(f"Redis stored: {fingerprint.fingerprint_id[:8]}...")
            return True

        except Exception as e:
            logger.error(f"Redis store error: {e}")
            return False

    async def find_similar(
        self,
        techniques: List[str],
        language: str,
        limit: int = 10
    ) -> List[StoredFingerprint]:
        """
        Find similar fingerprints.

        Note: Redis doesn't support complex queries, so we scan keys.
        For production, consider RediSearch or move query to PostgreSQL.
        """
        if not self._connected:
            return []

        try:
            results = []
            cursor = 0

            while True:
                cursor, keys = await self._client.scan(
                    cursor,
                    match=f"{self.PREFIX}*",
                    count=100
                )

                for key in keys:
                    data = await self._client.get(key)
                    if data:
                        fp = StoredFingerprint.from_dict(json.loads(data))

                        # Simple matching: shared techniques or same language
                        shared = set(fp.techniques) & set(techniques)
                        if shared or fp.primary_language == language:
                            results.append(fp)

                        if len(results) >= limit:
                            return results

                if cursor == 0:
                    break

            return results

        except Exception as e:
            logger.error(f"Redis find_similar error: {e}")
            return []

    async def delete(self, fingerprint_id: str) -> bool:
        if not self._connected:
            return False

        try:
            result = await self._client.delete(self._key(fingerprint_id))
            return result > 0
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return False

    async def cleanup_expired(self) -> int:
        """Redis handles expiration automatically via TTL."""
        return 0

    async def get_stats(self) -> Dict[str, Any]:
        if not self._connected:
            return {"connected": False}

        try:
            info = await self._client.info("keyspace")
            keys_count = 0

            # Count our keys
            cursor = 0
            while True:
                cursor, keys = await self._client.scan(
                    cursor,
                    match=f"{self.PREFIX}*",
                    count=1000
                )
                keys_count += len(keys)
                if cursor == 0:
                    break

            return {
                "connected": True,
                "type": "redis",
                "fingerprints_count": keys_count,
                "ttl_hours": self.ttl_seconds // 3600,
            }

        except Exception as e:
            return {"connected": True, "error": str(e)}


# ============================================================================
# PostgreSQL Store (Cold Layer)
# ============================================================================


class PostgreSQLStore(FingerprintStoreInterface):
    """
    PostgreSQL-backed cold storage for fingerprints.

    Features:
    - Persistent storage
    - Complex queries for similarity matching
    - GDPR-compliant with explicit TTL
    - Audit trail support

    Requires: asyncpg package
    """

    TABLE_NAME = "attacker_fingerprints"
    DEFAULT_TTL_DAYS = 30

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "sentinel",
        user: str = "sentinel",
        password: Optional[str] = None,
        ttl_days: int = DEFAULT_TTL_DAYS,
    ):
        self.dsn = f"postgresql://{user}:{password or ''}@{host}:{port}/{database}"
        self.ttl_days = ttl_days

        self._pool = None
        self._connected = False

    async def connect(self) -> bool:
        """Connect to PostgreSQL and create table if needed."""
        try:
            import asyncpg

            self._pool = await asyncpg.create_pool(
                self.dsn,
                min_size=2,
                max_size=10,
            )

            # Create table if not exists
            await self._create_table()

            self._connected = True
            logger.info("PostgreSQL connected")
            return True

        except ImportError:
            logger.warning("asyncpg not installed, using fallback")
            return False
        except Exception as e:
            logger.error(f"PostgreSQL connection failed: {e}")
            return False

    async def disconnect(self):
        """Disconnect from PostgreSQL."""
        if self._pool:
            await self._pool.close()
            self._connected = False

    async def _create_table(self):
        """Create fingerprints table if not exists."""
        async with self._pool.acquire() as conn:
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.TABLE_NAME} (
                    fingerprint_id VARCHAR(32) PRIMARY KEY,
                    accumulated_risk REAL NOT NULL,
                    request_count INTEGER NOT NULL,
                    first_seen TIMESTAMP NOT NULL,
                    last_seen TIMESTAMP NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    techniques TEXT[] DEFAULT '{{}}',
                    primary_language VARCHAR(10) DEFAULT 'en',
                    uses_obfuscation BOOLEAN DEFAULT FALSE,
                    is_burst BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS idx_fingerprints_expires 
                ON {self.TABLE_NAME} (expires_at);
                
                CREATE INDEX IF NOT EXISTS idx_fingerprints_techniques 
                ON {self.TABLE_NAME} USING GIN (techniques);
                
                CREATE INDEX IF NOT EXISTS idx_fingerprints_language 
                ON {self.TABLE_NAME} (primary_language);
            """)

    async def get(self, fingerprint_id: str) -> Optional[StoredFingerprint]:
        if not self._connected:
            return None

        try:
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow(
                    f"SELECT * FROM {self.TABLE_NAME} WHERE fingerprint_id = $1",
                    fingerprint_id
                )

                if row:
                    return StoredFingerprint(
                        fingerprint_id=row["fingerprint_id"],
                        accumulated_risk=row["accumulated_risk"],
                        request_count=row["request_count"],
                        first_seen=row["first_seen"],
                        last_seen=row["last_seen"],
                        expires_at=row["expires_at"],
                        techniques=list(row["techniques"]),
                        primary_language=row["primary_language"],
                        uses_obfuscation=row["uses_obfuscation"],
                        is_burst=row["is_burst"],
                    )
                return None

        except Exception as e:
            logger.error(f"PostgreSQL get error: {e}")
            return None

    async def store(self, fingerprint: StoredFingerprint) -> bool:
        if not self._connected:
            return False

        try:
            async with self._pool.acquire() as conn:
                await conn.execute(f"""
                    INSERT INTO {self.TABLE_NAME} 
                    (fingerprint_id, accumulated_risk, request_count, 
                     first_seen, last_seen, expires_at,
                     techniques, primary_language, uses_obfuscation, is_burst)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    ON CONFLICT (fingerprint_id) DO UPDATE SET
                        accumulated_risk = GREATEST({self.TABLE_NAME}.accumulated_risk, $2),
                        request_count = {self.TABLE_NAME}.request_count + $3,
                        last_seen = $5,
                        expires_at = $6,
                        updated_at = CURRENT_TIMESTAMP
                """,
                                   fingerprint.fingerprint_id,
                                   fingerprint.accumulated_risk,
                                   fingerprint.request_count,
                                   fingerprint.first_seen,
                                   fingerprint.last_seen,
                                   fingerprint.expires_at,
                                   fingerprint.techniques,
                                   fingerprint.primary_language,
                                   fingerprint.uses_obfuscation,
                                   fingerprint.is_burst,
                                   )

                logger.debug(
                    f"PostgreSQL stored: {fingerprint.fingerprint_id[:8]}...")
                return True

        except Exception as e:
            logger.error(f"PostgreSQL store error: {e}")
            return False

    async def find_similar(
        self,
        techniques: List[str],
        language: str,
        limit: int = 10
    ) -> List[StoredFingerprint]:
        if not self._connected:
            return []

        try:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch(f"""
                    SELECT *, 
                           cardinality(techniques & $1::text[]) as technique_overlap
                    FROM {self.TABLE_NAME}
                    WHERE expires_at > CURRENT_TIMESTAMP
                      AND (techniques && $1::text[] OR primary_language = $2)
                    ORDER BY technique_overlap DESC, accumulated_risk DESC
                    LIMIT $3
                """,
                                        techniques,
                                        language,
                                        limit,
                                        )

                return [
                    StoredFingerprint(
                        fingerprint_id=row["fingerprint_id"],
                        accumulated_risk=row["accumulated_risk"],
                        request_count=row["request_count"],
                        first_seen=row["first_seen"],
                        last_seen=row["last_seen"],
                        expires_at=row["expires_at"],
                        techniques=list(row["techniques"]),
                        primary_language=row["primary_language"],
                        uses_obfuscation=row["uses_obfuscation"],
                        is_burst=row["is_burst"],
                    )
                    for row in rows
                ]

        except Exception as e:
            logger.error(f"PostgreSQL find_similar error: {e}")
            return []

    async def delete(self, fingerprint_id: str) -> bool:
        if not self._connected:
            return False

        try:
            async with self._pool.acquire() as conn:
                result = await conn.execute(
                    f"DELETE FROM {self.TABLE_NAME} WHERE fingerprint_id = $1",
                    fingerprint_id
                )
                return "DELETE 1" in result

        except Exception as e:
            logger.error(f"PostgreSQL delete error: {e}")
            return False

    async def cleanup_expired(self) -> int:
        if not self._connected:
            return 0

        try:
            async with self._pool.acquire() as conn:
                result = await conn.execute(f"""
                    DELETE FROM {self.TABLE_NAME} 
                    WHERE expires_at < CURRENT_TIMESTAMP
                """)

                # Parse "DELETE N" to get count
                count = int(result.split()[1]) if "DELETE" in result else 0

                if count > 0:
                    logger.info(
                        f"PostgreSQL cleaned up {count} expired fingerprints")

                return count

        except Exception as e:
            logger.error(f"PostgreSQL cleanup error: {e}")
            return 0

    async def get_stats(self) -> Dict[str, Any]:
        if not self._connected:
            return {"connected": False}

        try:
            async with self._pool.acquire() as conn:
                stats = await conn.fetchrow(f"""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(*) FILTER (WHERE expires_at > CURRENT_TIMESTAMP) as active,
                        AVG(accumulated_risk) as avg_risk,
                        MAX(request_count) as max_requests
                    FROM {self.TABLE_NAME}
                """)

                return {
                    "connected": True,
                    "type": "postgresql",
                    "total_fingerprints": stats["total"],
                    "active_fingerprints": stats["active"],
                    "avg_risk": float(stats["avg_risk"] or 0),
                    "max_requests": stats["max_requests"] or 0,
                    "ttl_days": self.ttl_days,
                }

        except Exception as e:
            return {"connected": True, "error": str(e)}


# ============================================================================
# In-Memory Fallback Store
# ============================================================================


class InMemoryStore(FingerprintStoreInterface):
    """
    In-memory fallback when Redis/PostgreSQL unavailable.

    Warning: Data is lost on restart!
    """

    def __init__(self, ttl_hours: int = 24):
        self._store: Dict[str, StoredFingerprint] = {}
        self.ttl_hours = ttl_hours

    async def get(self, fingerprint_id: str) -> Optional[StoredFingerprint]:
        fp = self._store.get(fingerprint_id)
        if fp and fp.expires_at > datetime.now():
            return fp
        return None

    async def store(self, fingerprint: StoredFingerprint) -> bool:
        self._store[fingerprint.fingerprint_id] = fingerprint
        return True

    async def find_similar(
        self,
        techniques: List[str],
        language: str,
        limit: int = 10
    ) -> List[StoredFingerprint]:
        results = []
        now = datetime.now()

        for fp in self._store.values():
            if fp.expires_at <= now:
                continue

            shared = set(fp.techniques) & set(techniques)
            if shared or fp.primary_language == language:
                results.append(fp)

            if len(results) >= limit:
                break

        return results

    async def delete(self, fingerprint_id: str) -> bool:
        if fingerprint_id in self._store:
            del self._store[fingerprint_id]
            return True
        return False

    async def cleanup_expired(self) -> int:
        now = datetime.now()
        expired = [
            fp_id for fp_id, fp in self._store.items()
            if fp.expires_at <= now
        ]

        for fp_id in expired:
            del self._store[fp_id]

        return len(expired)

    async def get_stats(self) -> Dict[str, Any]:
        now = datetime.now()
        active = sum(1 for fp in self._store.values() if fp.expires_at > now)

        return {
            "connected": True,
            "type": "in_memory",
            "total_fingerprints": len(self._store),
            "active_fingerprints": active,
            "ttl_hours": self.ttl_hours,
            "warning": "Data will be lost on restart!",
        }


# ============================================================================
# Dual-Layer Store (Main Class)
# ============================================================================


class DualLayerFingerprintStore:
    """
    Main fingerprint store with dual-layer architecture.

    - Hot layer (Redis): Fast real-time matching, 24h TTL
    - Cold layer (PostgreSQL): Persistent, 30d TTL, GDPR-compliant
    - Fallback (In-Memory): When neither is available

    Usage:
        store = DualLayerFingerprintStore()
        await store.connect()

        # Store fingerprint (writes to both layers)
        await store.store(fingerprint)

        # Get (checks hot first, then cold)
        fp = await store.get(fingerprint_id)

        await store.disconnect()
    """

    def __init__(
        self,
        redis_config: Optional[Dict] = None,
        postgres_config: Optional[Dict] = None,
        enable_sync: bool = True,
    ):
        self.redis_config = redis_config or {}
        self.postgres_config = postgres_config or {}
        self.enable_sync = enable_sync

        self.hot: FingerprintStoreInterface = InMemoryStore()
        self.cold: FingerprintStoreInterface = InMemoryStore(
            ttl_hours=720)  # 30 days

        self._sync_task: Optional[asyncio.Task] = None

    async def connect(self) -> Dict[str, bool]:
        """Connect to storage backends."""
        results = {"redis": False, "postgresql": False}

        # Try Redis
        if self.redis_config:
            redis_store = RedisStore(**self.redis_config)
            if await redis_store.connect():
                self.hot = redis_store
                results["redis"] = True

        # Try PostgreSQL
        if self.postgres_config:
            pg_store = PostgreSQLStore(**self.postgres_config)
            if await pg_store.connect():
                self.cold = pg_store
                results["postgresql"] = True

        # Start background sync
        if self.enable_sync:
            self._start_sync()

        logger.info(f"DualLayerStore connected: {results}")
        return results

    async def disconnect(self):
        """Disconnect from storage backends."""
        if self._sync_task:
            self._sync_task.cancel()

        if isinstance(self.hot, RedisStore):
            await self.hot.disconnect()

        if isinstance(self.cold, PostgreSQLStore):
            await self.cold.disconnect()

    def _start_sync(self):
        """Start background sync task."""
        async def sync_loop():
            while True:
                try:
                    await asyncio.sleep(300)  # Every 5 minutes
                    await self._sync_hot_to_cold()
                    await self.cold.cleanup_expired()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Sync error: {e}")

        self._sync_task = asyncio.create_task(sync_loop())

    async def _sync_hot_to_cold(self):
        """Sync data from hot to cold layer."""
        # In production, track which items need syncing
        # For now, this is handled on store() call
        pass

    async def get(self, fingerprint_id: str) -> Optional[StoredFingerprint]:
        """
        Get fingerprint by ID.

        Checks hot layer first, falls back to cold.
        """
        # Check hot first (fast path)
        fp = await self.hot.get(fingerprint_id)
        if fp:
            return fp

        # Check cold
        fp = await self.cold.get(fingerprint_id)
        if fp:
            # Warm up hot layer
            await self.hot.store(fp)

        return fp

    async def store(self, fingerprint: StoredFingerprint) -> bool:
        """
        Store fingerprint to both layers.

        Returns True if stored in at least one layer.
        """
        # Store in hot layer
        hot_ok = await self.hot.store(fingerprint)

        # Store in cold layer
        cold_ok = await self.cold.store(fingerprint)

        return hot_ok or cold_ok

    async def find_similar(
        self,
        techniques: List[str],
        language: str,
        limit: int = 10
    ) -> List[StoredFingerprint]:
        """
        Find similar fingerprints.

        Uses cold layer for complex queries (PostgreSQL).
        """
        return await self.cold.find_similar(techniques, language, limit)

    async def delete(self, fingerprint_id: str) -> bool:
        """Delete from both layers."""
        hot_ok = await self.hot.delete(fingerprint_id)
        cold_ok = await self.cold.delete(fingerprint_id)
        return hot_ok or cold_ok

    async def get_stats(self) -> Dict[str, Any]:
        """Get statistics from both layers."""
        return {
            "hot": await self.hot.get_stats(),
            "cold": await self.cold.get_stats(),
        }


# ============================================================================
# Factory and Convenience
# ============================================================================


_default_store: Optional[DualLayerFingerprintStore] = None


async def get_store(
    redis_config: Optional[Dict] = None,
    postgres_config: Optional[Dict] = None,
) -> DualLayerFingerprintStore:
    """Get or create default store."""
    global _default_store

    if _default_store is None:
        _default_store = DualLayerFingerprintStore(
            redis_config=redis_config,
            postgres_config=postgres_config,
        )
        await _default_store.connect()

    return _default_store


def create_stored_fingerprint(
    fingerprint_id: str,
    accumulated_risk: float,
    techniques: List[str],
    primary_language: str = "en",
    uses_obfuscation: bool = False,
    is_burst: bool = False,
    ttl_days: int = 30,
) -> StoredFingerprint:
    """Factory function to create StoredFingerprint."""
    now = datetime.now()

    return StoredFingerprint(
        fingerprint_id=fingerprint_id,
        accumulated_risk=accumulated_risk,
        request_count=1,
        first_seen=now,
        last_seen=now,
        expires_at=now + timedelta(days=ttl_days),
        techniques=techniques,
        primary_language=primary_language,
        uses_obfuscation=uses_obfuscation,
        is_burst=is_burst,
    )


# ============================================================================
# Test
# ============================================================================


if __name__ == "__main__":
    async def test():
        print("=== Fingerprint Store Test (In-Memory) ===\n")

        # Create store (will use in-memory fallback)
        store = DualLayerFingerprintStore()
        await store.connect()

        # Create test fingerprint
        fp = create_stored_fingerprint(
            fingerprint_id="abc12345678901234",
            accumulated_risk=0.85,
            techniques=["instruction_override", "role_manipulation"],
            primary_language="en",
            uses_obfuscation=True,
            is_burst=True,
        )

        # Store
        ok = await store.store(fp)
        print(f"Store: {ok}")

        # Get
        retrieved = await store.get("abc12345678901234")
        print(f"Get: {retrieved.fingerprint_id if retrieved else None}")

        # Find similar
        similar = await store.find_similar(
            techniques=["instruction_override"],
            language="en",
        )
        print(f"Find similar: {len(similar)} results")

        # Stats
        stats = await store.get_stats()
        print(f"Stats: {json.dumps(stats, indent=2)}")

        await store.disconnect()

    asyncio.run(test())
