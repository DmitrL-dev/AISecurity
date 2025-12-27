"""
Unit tests for Cache Isolation Guardian.
"""

import pytest
import time
from cache_isolation_guardian import (
    CacheIsolationGuardian,
    TenantIsolator,
    PrefixInjectionDetector,
    CachePoisoningDetector,
    CacheEntry,
    CacheViolationType,
)


class TestTenantIsolator:
    """Tests for tenant isolation."""

    def test_own_key_allowed(self):
        """Tenant can access own key."""
        isolator = TenantIsolator()
        isolator.register_key("tenant1", "key1")

        allowed, reason = isolator.check_access("tenant1", "key1")

        assert allowed is True

    def test_other_tenant_blocked(self):
        """Other tenant is blocked."""
        isolator = TenantIsolator()
        isolator.register_key("tenant1", "key1")

        allowed, reason = isolator.check_access("tenant2", "key1")

        assert allowed is False

    def test_isolated_key_unique(self):
        """Isolated keys are unique per tenant."""
        isolator = TenantIsolator()

        key1 = isolator.get_isolated_key("tenant1", "secret")
        key2 = isolator.get_isolated_key("tenant2", "secret")

        assert key1 != key2


class TestPrefixInjectionDetector:
    """Tests for prefix injection detection."""

    def test_clean_key_passes(self):
        """Clean key passes."""
        detector = PrefixInjectionDetector()

        detected, pattern = detector.detect("user:cache:data")

        assert detected is False

    def test_path_traversal_detected(self):
        """Path traversal is detected."""
        detector = PrefixInjectionDetector()

        detected, pattern = detector.detect("../../../etc/passwd")

        assert detected is True
        assert pattern == "../"

    def test_null_byte_detected(self):
        """Null byte is detected."""
        detector = PrefixInjectionDetector()

        detected, pattern = detector.detect("key\x00injection")

        assert detected is True


class TestCachePoisoningDetector:
    """Tests for cache poisoning detection."""

    def test_valid_entry_passes(self):
        """Valid entry passes verification."""
        detector = CachePoisoningDetector()

        entry = CacheEntry(
            key="test",
            value="data",
            tenant_id="t1",
            session_id="s1",
            created_at=time.time(),
            expires_at=time.time() + 3600,
        )
        entry.signature = detector.sign_entry(entry)

        valid, reason = detector.verify_entry(entry)

        assert valid is True

    def test_tampered_entry_fails(self):
        """Tampered entry fails verification."""
        detector = CachePoisoningDetector()

        entry = CacheEntry(
            key="test",
            value="data",
            tenant_id="t1",
            session_id="s1",
            created_at=time.time(),
            expires_at=time.time() + 3600,
            signature="fake_signature",
        )

        valid, reason = detector.verify_entry(entry)

        assert valid is False


class TestCacheIsolationGuardian:
    """Integration tests."""

    def test_valid_access_allowed(self):
        """Valid access is allowed."""
        guardian = CacheIsolationGuardian()

        result = guardian.validate_access("tenant1", "mykey")

        assert result.is_safe is True
        assert result.allowed is True

    def test_injection_blocked(self):
        """Injection is blocked."""
        guardian = CacheIsolationGuardian()

        result = guardian.validate_access("tenant1", "../secret")

        assert result.is_safe is False
        assert result.violation == CacheViolationType.PREFIX_INJECTION

    def test_safe_set_and_get(self):
        """Safe set and get work."""
        guardian = CacheIsolationGuardian()

        success = guardian.safe_set("tenant1", "key1", "value1")
        value = guardian.safe_get("tenant1", "key1")

        assert success is True
        assert value == "value1"

    def test_cross_tenant_blocked(self):
        """Cross-tenant access is blocked."""
        guardian = CacheIsolationGuardian()

        guardian.safe_set("tenant1", "secret", "data")
        value = guardian.safe_get("tenant2", "secret")

        # Should be None because tenant2 can't access tenant1's key
        # Or it would be separate isolated key
        assert value is None or value != "data"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
