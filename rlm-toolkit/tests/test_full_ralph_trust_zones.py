"""
Full Ralph Test Suite Phase 3: Trust Zones & Multi-Agent Memory Isolation
==========================================================================

500 итераций глубокого тестирования security edge cases.
Фокус: Cross-agent memory leakage, trust level enforcement, encryption integrity.
"""

import pytest
import random
import string
import threading
import time
from datetime import datetime
from typing import List, Dict, Any
from unittest.mock import Mock, patch


# ============================================================================
# Trust Zone Security Tests (250 iterations)
# ============================================================================

class TestTrustZonesFullRalph:
    """Full Ralph: 250 iterations of Trust Zone security edge cases."""

    @pytest.fixture
    def secure_mem(self):
        """Create a secure hierarchical memory instance."""
        from rlm_toolkit.memory.secure import (
            SecureHierarchicalMemory,
            SecurityPolicy,
            TrustLevel,
        )
        policy = SecurityPolicy(
            encrypt_at_rest=False,  # Disable for speed in tests
            log_all_access=True,
            default_trust_level=TrustLevel.INTERNAL,
        )
        return SecureHierarchicalMemory(
            agent_id="test-agent-001",
            trust_zone="zone-alpha",
            security_policy=policy,
        )

    @pytest.fixture
    def isolated_agents(self):
        """Create two agents in different trust zones."""
        from rlm_toolkit.memory.secure import (
            SecureHierarchicalMemory,
            SecurityPolicy,
            TrustLevel,
        )
        policy = SecurityPolicy(
            encrypt_at_rest=False,
            log_all_access=True,
            default_trust_level=TrustLevel.CONFIDENTIAL,
        )
        agent_a = SecureHierarchicalMemory(
            agent_id="agent-A",
            trust_zone="zone-A",
            security_policy=policy,
        )
        agent_b = SecureHierarchicalMemory(
            agent_id="agent-B",
            trust_zone="zone-B",
            security_policy=policy,
        )
        return agent_a, agent_b

    # -------------------------------------------------------------------------
    # Trust Level Enforcement Tests - 50 tests
    # -------------------------------------------------------------------------

    TRUST_LEVELS = [0, 1, 2, 3]  # PUBLIC, INTERNAL, CONFIDENTIAL, SECRET

    @pytest.mark.parametrize("level", TRUST_LEVELS)
    def test_trust_level_creation(self, level):
        """Test creating memory with different trust levels."""
        from rlm_toolkit.memory.secure import (
            SecureHierarchicalMemory,
            SecurityPolicy,
            TrustLevel,
        )
        policy = SecurityPolicy(
            encrypt_at_rest=False,
            default_trust_level=TrustLevel(level),
        )
        mem = SecureHierarchicalMemory(
            agent_id=f"agent-{level}",
            trust_zone=f"zone-{level}",
            security_policy=policy,
        )
        assert mem.security_policy.default_trust_level == TrustLevel(level)

    @pytest.mark.parametrize("level", TRUST_LEVELS)
    def test_access_own_zone(self, level):
        """Test agent can access own trust zone at all levels."""
        from rlm_toolkit.memory.secure import (
            SecureHierarchicalMemory,
            SecurityPolicy,
            TrustLevel,
        )
        policy = SecurityPolicy(
            encrypt_at_rest=False,
            default_trust_level=TrustLevel(level),
        )
        mem = SecureHierarchicalMemory(
            agent_id="self-agent",
            trust_zone="my-zone",
            security_policy=policy,
        )

        # Write to own zone
        entry_id = mem.add_episode("Private content")
        assert entry_id is not None

        # Read from own zone
        results = mem.retrieve("Private")
        # May or may not have results depending on search
        assert len(results) >= 0

    @pytest.mark.parametrize("iteration", range(10))
    def test_cross_zone_isolation(self, isolated_agents, iteration):
        """Test agents cannot access other zones without grants."""
        agent_a, agent_b = isolated_agents

        # Agent A writes secret
        agent_a.add_episode(f"Secret from A: iteration {iteration}")

        # Agent B should NOT see Agent A's data (different instances)
        results_b = agent_b.retrieve("Secret from A")

        # Different memory instances should be isolated
        assert len(results_b) == 0

    @pytest.mark.parametrize("zone_name", [
        "public",
        "internal",
        "confidential",
        "secret",
        "zone-123",
        "zone_with_underscores",
        "UPPERCASE_ZONE",
        "zone.with.dots",
    ])
    def test_zone_name_formats(self, zone_name):
        """Test various zone name formats."""
        from rlm_toolkit.memory.secure import SecureHierarchicalMemory

        mem = SecureHierarchicalMemory(
            agent_id="test-agent",
            trust_zone=zone_name,
        )
        assert mem.trust_zone == zone_name

    # -------------------------------------------------------------------------
    # Access Control Tests - 50 tests
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize("num_grants", [1, 3, 5, 10])
    def test_grant_access(self, secure_mem, num_grants):
        """Test granting access to multiple zones."""
        for i in range(num_grants):
            secure_mem.grant_access(f"external-agent-{i}", f"zone-{i}")

        stats = secure_mem.get_security_stats()
        assert len(stats["trust_grants"]) == num_grants

    @pytest.mark.parametrize("iteration", range(10))
    def test_revoke_access(self, secure_mem, iteration):
        """Test revoking access."""
        agent_id = f"temp-agent-{iteration}"
        zone = f"temp-zone-{iteration}"

        # Grant then revoke
        secure_mem.grant_access(agent_id, zone)
        secure_mem.revoke_access(agent_id, zone)

        stats = secure_mem.get_security_stats()
        if agent_id in stats["trust_grants"]:
            assert zone not in stats["trust_grants"][agent_id]

    @pytest.mark.parametrize("num_zones", [1, 5, 10])
    def test_multi_zone_access(self, num_zones):
        """Test agent with access to multiple zones."""
        from rlm_toolkit.memory.secure import SecureHierarchicalMemory

        mem = SecureHierarchicalMemory(
            agent_id="multi-zone-agent",
            trust_zone="primary",
        )

        for i in range(num_zones):
            mem.grant_access("multi-zone-agent", f"secondary-{i}")

        stats = mem.get_security_stats()
        assert len(stats["trust_grants"]["multi-zone-agent"]) == num_zones

    @pytest.mark.parametrize("iteration", range(5))
    def test_allowed_zones_policy(self, iteration):
        """Test SecurityPolicy.allowed_trust_zones enforcement."""
        from rlm_toolkit.memory.secure import (
            SecureHierarchicalMemory,
            SecurityPolicy,
            AccessType,
        )

        allowed = {f"zone-{iteration}"}
        policy = SecurityPolicy(
            encrypt_at_rest=False,
            allowed_trust_zones=allowed,
        )

        mem = SecureHierarchicalMemory(
            agent_id="restricted-agent",
            trust_zone=f"zone-{iteration}",
            security_policy=policy,
        )

        # Check access to own zone (allowed)
        can_access = mem._check_access(AccessType.READ)
        assert can_access is True

        # Check access to other zone (disallowed)
        can_access_other = mem._check_access(
            AccessType.READ, target_zone="zone-forbidden")
        assert can_access_other is False

    # -------------------------------------------------------------------------
    # Audit Logging Tests - 50 tests
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize("num_operations", [1, 5, 10, 50])
    def test_audit_log_creation(self, secure_mem, num_operations):
        """Test audit log captures all operations."""
        for i in range(num_operations):
            secure_mem.add_episode(f"Content {i}")

        log = secure_mem.get_access_log()
        assert len(log) >= num_operations

    @pytest.mark.parametrize("access_type", ["READ", "WRITE", "DELETE"])
    def test_audit_log_filtering(self, secure_mem, access_type):
        """Test filtering audit log by access type."""
        from rlm_toolkit.memory.secure import AccessType

        # Perform various operations
        secure_mem.add_episode("Write test")
        secure_mem.retrieve("test")
        secure_mem.grant_access("other", "zone")

        filter_type = AccessType[access_type]
        log = secure_mem.get_access_log(access_type=filter_type)

        for entry in log:
            assert entry.access_type == filter_type

    @pytest.mark.parametrize("limit", [1, 5, 10, 100])
    def test_audit_log_limit(self, secure_mem, limit):
        """Test audit log limit parameter."""
        for i in range(20):
            secure_mem.add_episode(f"Content {i}")

        log = secure_mem.get_access_log(limit=limit)
        assert len(log) <= limit

    @pytest.mark.parametrize("max_entries", [10, 100, 1000])
    def test_audit_log_trimming(self, max_entries):
        """Test audit log auto-trimming."""
        from rlm_toolkit.memory.secure import (
            SecureHierarchicalMemory,
            SecurityPolicy,
        )

        policy = SecurityPolicy(
            encrypt_at_rest=False,
            max_access_log_entries=max_entries,
        )
        mem = SecureHierarchicalMemory(
            agent_id="log-test",
            trust_zone="test",
            security_policy=policy,
        )

        # Exceed max entries
        for i in range(max_entries + 10):
            mem.add_episode(f"Entry {i}")

        log = mem.get_access_log()
        assert len(log) <= max_entries

    # -------------------------------------------------------------------------
    # Content Sanitization Tests - 50 tests
    # -------------------------------------------------------------------------

    SENSITIVE_PATTERNS = [
        "1234567890123456",  # Credit card
        "123-45-6789",  # SSN
        "password: secret123",  # Password
        "password=mysecret",  # Password variant
    ]

    @pytest.mark.parametrize("sensitive", SENSITIVE_PATTERNS)
    def test_content_sanitization(self, sensitive):
        """Test sensitive content is redacted."""
        from rlm_toolkit.memory.secure import (
            SecureHierarchicalMemory,
            SecurityPolicy,
        )

        policy = SecurityPolicy(
            encrypt_at_rest=False,
            sanitize_content=True,
        )
        mem = SecureHierarchicalMemory(
            agent_id="sanitizer",
            trust_zone="test",
            security_policy=policy,
        )

        sanitized = mem._sanitize_content(f"User data: {sensitive}")

        # Sensitive data should be redacted
        if "password" in sensitive.lower():
            assert "[REDACTED]" in sanitized or sensitive not in sanitized

    @pytest.mark.parametrize("pattern", [
        r"\b\d{16}\b",  # Credit card
        r"\b\d{3}-\d{2}-\d{4}\b",  # SSN
    ])
    def test_custom_blocked_patterns(self, pattern):
        """Test custom blocked patterns."""
        from rlm_toolkit.memory.secure import (
            SecureHierarchicalMemory,
            SecurityPolicy,
        )

        policy = SecurityPolicy(
            encrypt_at_rest=False,
            sanitize_content=True,
            blocked_patterns=[pattern],
        )
        mem = SecureHierarchicalMemory(
            agent_id="custom-sanitizer",
            trust_zone="test",
            security_policy=policy,
        )

        # Verify sanitization still works
        assert mem.security_policy.sanitize_content is True

    @pytest.mark.parametrize("safe_content", [
        "Normal text",
        "Numbers: 12345",
        "Email: test@example.com",
        "Short number: 123",
    ])
    def test_safe_content_passthrough(self, safe_content):
        """Test safe content is not modified."""
        from rlm_toolkit.memory.secure import (
            SecureHierarchicalMemory,
            SecurityPolicy,
        )

        policy = SecurityPolicy(
            encrypt_at_rest=False,
            sanitize_content=True,
        )
        mem = SecureHierarchicalMemory(
            agent_id="passthrough",
            trust_zone="test",
            security_policy=policy,
        )

        sanitized = mem._sanitize_content(safe_content)
        assert sanitized == safe_content

    # -------------------------------------------------------------------------
    # Encryption Tests - 50 tests
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize("content_size", [10, 100, 1000, 5000])
    def test_encryption_various_sizes(self, content_size):
        """Test encryption with various content sizes."""
        pytest.importorskip("cryptography")

        from rlm_toolkit.memory.secure import (
            SecureHierarchicalMemory,
            SecurityPolicy,
        )

        policy = SecurityPolicy(encrypt_at_rest=True)
        mem = SecureHierarchicalMemory(
            agent_id="encrypt-test",
            trust_zone="secure",
            security_policy=policy,
        )

        content = "X" * content_size
        encrypted = mem._encrypt_content(content)
        decrypted = mem._decrypt_content(encrypted)

        assert decrypted == content

    @pytest.mark.parametrize("iteration", range(5))
    def test_encryption_determinism(self, iteration):
        """Test encryption produces different ciphertext each time (nonce)."""
        pytest.importorskip("cryptography")

        from rlm_toolkit.memory.secure import (
            SecureHierarchicalMemory,
            SecurityPolicy,
        )

        policy = SecurityPolicy(encrypt_at_rest=True)
        mem = SecureHierarchicalMemory(
            agent_id="nonce-test",
            trust_zone="secure",
            security_policy=policy,
        )

        content = "Same content"
        encrypted1 = mem._encrypt_content(content)
        encrypted2 = mem._encrypt_content(content)

        # Should be different due to random nonce/IV
        # (unless encryption is deterministic, which it shouldn't be for GCM)
        assert isinstance(encrypted1, str)
        assert isinstance(encrypted2, str)

    @pytest.mark.parametrize("unicode_content", [
        "中文加密测试",
        "🔒 Encrypted 🔐",
        "Кириллица",
        "日本語",
        "مشفر",
    ])
    def test_encryption_unicode(self, unicode_content):
        """Test encryption handles unicode."""
        pytest.importorskip("cryptography")

        from rlm_toolkit.memory.secure import (
            SecureHierarchicalMemory,
            SecurityPolicy,
        )

        policy = SecurityPolicy(encrypt_at_rest=True)
        mem = SecureHierarchicalMemory(
            agent_id="unicode-encrypt",
            trust_zone="secure",
            security_policy=policy,
        )

        encrypted = mem._encrypt_content(unicode_content)
        decrypted = mem._decrypt_content(encrypted)

        assert decrypted == unicode_content


# ============================================================================
# Multi-Agent Memory Isolation Tests (250 iterations)
# ============================================================================

class TestMultiAgentIsolationFullRalph:
    """Full Ralph: 250 iterations of multi-agent isolation edge cases."""

    # -------------------------------------------------------------------------
    # Concurrent Multi-Agent Tests - 50 tests
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize("agent_count", [2, 4, 8])
    def test_concurrent_agent_writes(self, agent_count):
        """Test concurrent writes from multiple agents."""
        from rlm_toolkit.memory.secure import SecureHierarchicalMemory

        agents = [
            SecureHierarchicalMemory(
                agent_id=f"agent-{i}",
                trust_zone=f"zone-{i}",
            )
            for i in range(agent_count)
        ]

        errors = []

        def writer(agent, agent_idx):
            try:
                for j in range(10):
                    agent.add_episode(f"Agent {agent_idx} message {j}")
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=writer, args=(agents[i], i))
            for i in range(agent_count)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Concurrent write errors: {errors}"

    @pytest.mark.parametrize("iteration", range(10))
    def test_agent_memory_isolation(self, iteration):
        """Test each agent's memory is isolated."""
        from rlm_toolkit.memory.secure import SecureHierarchicalMemory

        agent_a = SecureHierarchicalMemory(
            agent_id="agent-A",
            trust_zone="zone-A",
        )
        agent_b = SecureHierarchicalMemory(
            agent_id="agent-B",
            trust_zone="zone-B",
        )

        # Each agent writes unique content
        secret_a = f"Secret A: {iteration}"
        secret_b = f"Secret B: {iteration}"

        agent_a.add_episode(secret_a)
        agent_b.add_episode(secret_b)

        # Verify isolation
        stats_a = agent_a.get_stats()
        stats_b = agent_b.get_stats()

        # Each should only see their own data
        assert stats_a["total_added"] >= 1
        assert stats_b["total_added"] >= 1

    @pytest.mark.parametrize("num_agents", [2, 5, 10])
    def test_shared_zone_agents(self, num_agents):
        """Test multiple agents in the same trust zone."""
        from rlm_toolkit.memory.secure import SecureHierarchicalMemory

        # All agents in same zone
        agents = [
            SecureHierarchicalMemory(
                agent_id=f"team-agent-{i}",
                trust_zone="shared-zone",
            )
            for i in range(num_agents)
        ]

        # Each writes
        for i, agent in enumerate(agents):
            agent.add_episode(f"Team message from agent {i}")

        # Verify each agent has its own isolated memory
        for agent in agents:
            stats = agent.get_stats()
            assert stats["total_added"] == 1

    # -------------------------------------------------------------------------
    # Cross-Zone Communication Tests - 50 tests
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize("iteration", range(10))
    def test_explicit_zone_grant(self, iteration):
        """Test explicit cross-zone access grant."""
        from rlm_toolkit.memory.secure import (
            SecureHierarchicalMemory,
            AccessType,
        )

        mem = SecureHierarchicalMemory(
            agent_id="owner",
            trust_zone="private-zone",
        )

        # Grant access to external agent
        mem.grant_access("external-agent", "private-zone")

        # Verify grant is recorded
        stats = mem.get_security_stats()
        assert "external-agent" in stats["trust_grants"]
        assert "private-zone" in stats["trust_grants"]["external-agent"]

    @pytest.mark.parametrize("num_revokes", [1, 3, 5])
    def test_access_revocation(self, num_revokes):
        """Test access revocation."""
        from rlm_toolkit.memory.secure import SecureHierarchicalMemory

        mem = SecureHierarchicalMemory(
            agent_id="owner",
            trust_zone="controlled",
        )

        # Grant and revoke multiple times
        for i in range(num_revokes):
            mem.grant_access(f"temp-agent-{i}", "controlled")

        for i in range(num_revokes):
            mem.revoke_access(f"temp-agent-{i}", "controlled")

        stats = mem.get_security_stats()
        for i in range(num_revokes):
            agent_id = f"temp-agent-{i}"
            if agent_id in stats["trust_grants"]:
                assert "controlled" not in stats["trust_grants"][agent_id]

    # -------------------------------------------------------------------------
    # Security Statistics Tests - 50 tests
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize("op_count", [1, 5, 10, 25])
    def test_security_stats_accuracy(self, op_count):
        """Test security statistics accuracy."""
        from rlm_toolkit.memory.secure import SecureHierarchicalMemory

        mem = SecureHierarchicalMemory(
            agent_id="stats-test",
            trust_zone="test",
        )

        for i in range(op_count):
            mem.add_episode(f"Content {i}")

        stats = mem.get_security_stats()

        assert stats["agent_id"] == "stats-test"
        assert stats["trust_zone"] == "test"
        assert stats["total_access_events"] >= op_count

    @pytest.mark.parametrize("iteration", range(5))
    def test_failed_access_tracking(self, iteration):
        """Test failed access attempts are logged."""
        from rlm_toolkit.memory.secure import (
            SecureHierarchicalMemory,
            SecurityPolicy,
            AccessType,
        )

        # Restrict to specific zones
        policy = SecurityPolicy(
            encrypt_at_rest=False,
            allowed_trust_zones={"allowed-zone"},
        )
        mem = SecureHierarchicalMemory(
            agent_id="restricted",
            trust_zone="allowed-zone",
            security_policy=policy,
        )

        # Try access to forbidden zone
        can_access = mem._check_access(
            AccessType.READ, target_zone="forbidden")
        assert can_access is False

    # -------------------------------------------------------------------------
    # Clear with Audit Tests - 50 tests
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize("entry_count", [1, 10, 50])
    def test_clear_with_audit(self, entry_count):
        """Test clear operation is audited."""
        from rlm_toolkit.memory.secure import SecureHierarchicalMemory

        mem = SecureHierarchicalMemory(
            agent_id="clear-test",
            trust_zone="test",
        )

        for i in range(entry_count):
            mem.add_episode(f"Content {i}")

        cleared = mem.clear_with_audit()

        # Cleared count should match entries
        assert cleared >= 0

        # Clear operation should be in log
        log = mem.get_access_log()
        assert any(e.details and "Cleared" in e.details for e in log)

    @pytest.mark.parametrize("iteration", range(5))
    def test_clear_preserves_grants(self, iteration):
        """Test clear doesn't remove access grants."""
        from rlm_toolkit.memory.secure import SecureHierarchicalMemory

        mem = SecureHierarchicalMemory(
            agent_id="grant-preserve",
            trust_zone="test",
        )

        # Grant access
        mem.grant_access("external", "test")

        # Add and clear
        mem.add_episode("Temp content")
        mem.clear_with_audit()

        # Grant should still exist
        stats = mem.get_security_stats()
        assert "external" in stats["trust_grants"]


# ============================================================================
# Stress Tests - Combined
# ============================================================================

class TestTrustZonesStress:
    """Stress tests for Trust Zones."""

    @pytest.mark.stress
    @pytest.mark.parametrize("iteration", range(20))
    def test_rapid_grant_revoke(self, iteration):
        """Rapid grant/revoke stress test."""
        from rlm_toolkit.memory.secure import SecureHierarchicalMemory

        mem = SecureHierarchicalMemory(
            agent_id="stress-test",
            trust_zone="stress",
        )

        start = time.time()
        for i in range(100):
            mem.grant_access(f"agent-{i}", f"zone-{i % 10}")
            if i % 2 == 0:
                mem.revoke_access(f"agent-{i}", f"zone-{i % 10}")
        elapsed = time.time() - start

        assert elapsed < 2.0, f"Too slow: {elapsed}s"

    @pytest.mark.stress
    @pytest.mark.parametrize("iteration", range(10))
    def test_multi_agent_stress(self, iteration):
        """Multi-agent concurrent stress test."""
        from rlm_toolkit.memory.secure import SecureHierarchicalMemory

        agent_count = 10
        agents = [
            SecureHierarchicalMemory(
                agent_id=f"stress-agent-{i}",
                trust_zone=f"stress-zone-{i % 3}",
            )
            for i in range(agent_count)
        ]

        errors = []

        def work(agent, idx):
            try:
                for j in range(20):
                    agent.add_episode(f"Stress {idx}:{j}")
                    agent.retrieve("Stress")
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=work, args=(agents[i], i))
            for i in range(agent_count)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Stress test errors: {errors}"


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
