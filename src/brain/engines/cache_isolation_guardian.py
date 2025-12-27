"""
Cache Isolation Guardian Engine - KV Cache Security

Protects KV cache from cross-user leakage:
- Cache key isolation
- Tenant separation
- Prefix injection defense
- Cache poisoning detection

Addresses: OWASP ASI-05 (Improper Cache Isolation)
Research: kv_cache_security_deep_dive.md
Invention: Cache Isolation Guardian (#38)
"""

import hashlib
import hmac
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

from base_engine import Severity, Action  # Base classes

logger = logging.getLogger("CacheIsolationGuardian")


# ============================================================================
# Data Classes
# ============================================================================


class CacheViolationType(Enum):
    """Types of cache violations."""

    CROSS_TENANT = "cross_tenant_access"
    PREFIX_INJECTION = "prefix_injection"
    CACHE_POISONING = "cache_poisoning"
    UNAUTHORIZED_READ = "unauthorized_read"
    STALE_DATA = "stale_data"


@dataclass
class CacheEntry:
    """Represents a cached entry."""

    key: str
    value: str
    tenant_id: str
    session_id: str
    created_at: float
    expires_at: float
    signature: str = ""


@dataclass
class CacheGuardResult:
    """Result from cache guard analysis."""

    is_safe: bool
    allowed: bool
    violation: Optional[CacheViolationType] = None
    risk_score: float = 0.0
    explanation: str = ""
    latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "is_safe": self.is_safe,
            "allowed": self.allowed,
            "violation": self.violation.value if self.violation else None,
            "risk_score": self.risk_score,
            "explanation": self.explanation,
            "latency_ms": self.latency_ms,
        }


# ============================================================================
# Tenant Isolator
# ============================================================================


class TenantIsolator:
    """
    Ensures strict tenant isolation in cache.
    """

    def __init__(self):
        self._tenant_keys: Dict[str, Set[str]] = {}

    def register_key(self, tenant_id: str, key: str) -> None:
        """Register key for tenant."""
        if tenant_id not in self._tenant_keys:
            self._tenant_keys[tenant_id] = set()
        self._tenant_keys[tenant_id].add(key)

    def check_access(self, tenant_id: str, key: str) -> Tuple[bool, str]:
        """
        Check if tenant can access key.

        Returns:
            (allowed, reason)
        """
        # Check if key belongs to another tenant
        for other_tenant, keys in self._tenant_keys.items():
            if other_tenant != tenant_id and key in keys:
                return False, f"Key belongs to tenant {other_tenant}"

        return True, "Access allowed"

    def get_isolated_key(self, tenant_id: str, key: str) -> str:
        """Generate tenant-isolated cache key."""
        return f"{tenant_id}:{hashlib.sha256(key.encode()).hexdigest()[:16]}"


# ============================================================================
# Prefix Injection Detector
# ============================================================================


class PrefixInjectionDetector:
    """
    Detects prefix injection attacks in cache keys.
    """

    SUSPICIOUS_PATTERNS = [
        "../",
        "..\\",
        "::",
        "\x00",
        "%00",
        "{{",
        "}}",
    ]

    def detect(self, key: str) -> Tuple[bool, str]:
        """
        Detect prefix injection.

        Returns:
            (detected, pattern)
        """
        for pattern in self.SUSPICIOUS_PATTERNS:
            if pattern in key:
                return True, pattern

        # Check for tenant ID manipulation attempts
        if key.count(":") > 2:
            return True, "multiple_colons"

        return False, ""


# ============================================================================
# Cache Poisoning Detector
# ============================================================================


class CachePoisoningDetector:
    """
    Detects cache poisoning attempts.
    """

    def __init__(self, secret: bytes = b"default_secret"):
        self._secret = secret

    def sign_entry(self, entry: CacheEntry) -> str:
        """Generate signature for entry."""
        data = f"{entry.key}:{entry.value}:{entry.tenant_id}:{entry.session_id}"
        return hmac.new(self._secret, data.encode(), "sha256").hexdigest()[:16]

    def verify_entry(self, entry: CacheEntry) -> Tuple[bool, str]:
        """
        Verify entry integrity.

        Returns:
            (valid, reason)
        """
        expected = self.sign_entry(entry)
        if entry.signature and entry.signature != expected:
            return False, "Signature mismatch - possible tampering"
        return True, "Valid"


# ============================================================================
# Expiration Manager
# ============================================================================


class ExpirationManager:
    """
    Manages cache entry expiration.
    """

    def __init__(self, default_ttl: float = 3600):
        self._default_ttl = default_ttl

    def is_expired(self, entry: CacheEntry, current_time: float) -> bool:
        """Check if entry is expired."""
        return current_time > entry.expires_at

    def get_expiration(self, created_at: float, ttl: float = None) -> float:
        """Calculate expiration time."""
        return created_at + (ttl or self._default_ttl)


# ============================================================================
# Main Engine
# ============================================================================


class CacheIsolationGuardian:
    """
    Cache Isolation Guardian - KV Cache Security

    Comprehensive cache protection:
    - Tenant isolation
    - Prefix injection defense
    - Poisoning detection
    - Expiration management

    Invention #38 from research.
    Addresses OWASP ASI-05.
    """

    def __init__(self, secret: bytes = b"cache_secret"):
        self.tenant_isolator = TenantIsolator()
        self.injection_detector = PrefixInjectionDetector()
        self.poisoning_detector = CachePoisoningDetector(secret)
        self.expiration_manager = ExpirationManager()

        self._cache: Dict[str, CacheEntry] = {}

        logger.info("CacheIsolationGuardian initialized")

    def validate_access(
        self,
        tenant_id: str,
        key: str,
        operation: str = "read",
    ) -> CacheGuardResult:
        """
        Validate cache access.

        Args:
            tenant_id: Requesting tenant
            key: Cache key
            operation: read/write

        Returns:
            CacheGuardResult
        """
        start = time.time()

        # Check prefix injection
        injection, pattern = self.injection_detector.detect(key)
        if injection:
            logger.warning(f"Prefix injection detected: {pattern}")
            return CacheGuardResult(
                is_safe=False,
                allowed=False,
                violation=CacheViolationType.PREFIX_INJECTION,
                risk_score=0.9,
                explanation=f"Injection pattern: {pattern}",
                latency_ms=(time.time() - start) * 1000,
            )

        # Check tenant isolation
        allowed, reason = self.tenant_isolator.check_access(tenant_id, key)
        if not allowed:
            logger.warning(f"Cross-tenant access blocked: {reason}")
            return CacheGuardResult(
                is_safe=False,
                allowed=False,
                violation=CacheViolationType.CROSS_TENANT,
                risk_score=0.95,
                explanation=reason,
                latency_ms=(time.time() - start) * 1000,
            )

        # Check entry integrity if exists
        isolated_key = self.tenant_isolator.get_isolated_key(tenant_id, key)
        if isolated_key in self._cache:
            entry = self._cache[isolated_key]

            # Check expiration
            if self.expiration_manager.is_expired(entry, time.time()):
                return CacheGuardResult(
                    is_safe=False,
                    allowed=False,
                    violation=CacheViolationType.STALE_DATA,
                    risk_score=0.3,
                    explanation="Cache entry expired",
                    latency_ms=(time.time() - start) * 1000,
                )

            # Verify integrity
            valid, int_reason = self.poisoning_detector.verify_entry(entry)
            if not valid:
                return CacheGuardResult(
                    is_safe=False,
                    allowed=False,
                    violation=CacheViolationType.CACHE_POISONING,
                    risk_score=0.95,
                    explanation=int_reason,
                    latency_ms=(time.time() - start) * 1000,
                )

        return CacheGuardResult(
            is_safe=True,
            allowed=True,
            explanation="Access validated",
            latency_ms=(time.time() - start) * 1000,
        )

    def safe_set(
        self,
        tenant_id: str,
        key: str,
        value: str,
        session_id: str = "default",
        ttl: float = None,
    ) -> bool:
        """Safely set cache entry."""
        # Validate first
        result = self.validate_access(tenant_id, key, "write")
        if not result.allowed:
            return False

        now = time.time()
        isolated_key = self.tenant_isolator.get_isolated_key(tenant_id, key)

        entry = CacheEntry(
            key=key,
            value=value,
            tenant_id=tenant_id,
            session_id=session_id,
            created_at=now,
            expires_at=self.expiration_manager.get_expiration(now, ttl),
        )
        entry.signature = self.poisoning_detector.sign_entry(entry)

        self._cache[isolated_key] = entry
        self.tenant_isolator.register_key(tenant_id, key)

        return True

    def safe_get(
        self,
        tenant_id: str,
        key: str,
    ) -> Optional[str]:
        """Safely get cache entry."""
        result = self.validate_access(tenant_id, key, "read")
        if not result.allowed:
            return None

        isolated_key = self.tenant_isolator.get_isolated_key(tenant_id, key)
        entry = self._cache.get(isolated_key)

        return entry.value if entry else None


# ============================================================================
# Convenience
# ============================================================================

_default_guardian: Optional[CacheIsolationGuardian] = None


def get_guardian() -> CacheIsolationGuardian:
    global _default_guardian
    if _default_guardian is None:
        _default_guardian = CacheIsolationGuardian()
    return _default_guardian
