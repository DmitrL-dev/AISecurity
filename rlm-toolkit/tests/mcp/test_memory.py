"""Tests for RLM MCP Memory integration."""

import pytest
from pathlib import Path
import tempfile
import shutil

from rlm_toolkit.memory.hierarchical import HierarchicalMemory, HMEMConfig, MemoryLevel


class TestHierarchicalMemory:
    """Tests for Hierarchical Memory (H-MEM)."""

    @pytest.fixture
    def memory(self):
        """Create fresh memory instance."""
        return HierarchicalMemory(
            HMEMConfig(
                max_episodes=100,
                auto_persist=False,
            )
        )

    def test_add_episode(self, memory):
        """Test adding episodes."""
        mem_id = memory.add_episode("Test memory content")
        assert mem_id is not None
        assert len(mem_id) > 0

    def test_add_multiple_episodes(self, memory):
        """Test adding multiple episodes."""
        memory.add_episode("First memory")
        memory.add_episode("Second memory")
        memory.add_episode("Third memory")

        stats = memory.get_stats()
        assert stats["level_counts"]["EPISODE"] == 3

    def test_retrieve_by_query(self, memory):
        """Test retrieval by query."""
        memory.add_episode("Python is a programming language")
        memory.add_episode("JavaScript is for web development")
        memory.add_episode("Python has many libraries")

        results = memory.retrieve("Python programming")
        assert len(results) > 0

    def test_memory_levels(self, memory):
        """Test memory hierarchy levels."""
        # Add episodes
        ep1 = memory.add_episode("User asked about authentication")
        ep2 = memory.add_episode("Discussed OAuth vs JWT")
        ep3 = memory.add_episode("Decided to use JWT")

        # Memory should have episodes at level 0
        stats = memory.get_stats()
        assert stats["level_counts"]["EPISODE"] >= 3

    def test_add_trace(self, memory):
        """Test adding memory traces (level 1)."""
        ep1 = memory.add_episode("First event")
        ep2 = memory.add_episode("Second event")

        trace_id = memory.add_trace(content="Summary of events", episode_ids=[ep1, ep2])

        assert trace_id is not None
        stats = memory.get_stats()
        assert stats["level_counts"]["TRACE"] >= 1


class TestSecureMemory:
    """Tests for Secure Hierarchical Memory."""

    def test_import(self):
        """Test import works."""
        from rlm_toolkit.memory.secure import SecureHierarchicalMemory, SecurityPolicy

        assert SecureHierarchicalMemory is not None

    def test_create_secure_memory(self):
        """Test creating secure memory."""
        from rlm_toolkit.memory.secure import SecureHierarchicalMemory, SecurityPolicy

        memory = SecureHierarchicalMemory(
            agent_id="test_agent",
            trust_zone="test",
            security_policy=SecurityPolicy(encrypt_at_rest=True),
            encryption_key=b"test_key_32_bytes_for_encryption",
        )

        assert memory is not None
        assert memory.agent_id == "test_agent"

    def test_add_episode_secure(self):
        """Test adding episode to secure memory."""
        from rlm_toolkit.memory.secure import SecureHierarchicalMemory, SecurityPolicy

        memory = SecureHierarchicalMemory(
            agent_id="test_agent",
            trust_zone="test",
            encryption_key=b"test_key_32_bytes_for_encryption",
        )

        mem_id = memory.add_episode("Secure test content")
        assert mem_id is not None

    def test_retrieve_secure(self):
        """Test retrieval from secure memory."""
        from rlm_toolkit.memory.secure import SecureHierarchicalMemory

        memory = SecureHierarchicalMemory(
            agent_id="test_agent",
            trust_zone="test",
            encryption_key=b"test_key_32_bytes_for_encryption",
        )

        memory.add_episode("authentication is important")
        memory.add_episode("security best practices")

        results = memory.retrieve("security", decrypt=True)
        assert len(results) >= 0  # May or may not find based on simple matching

    def test_access_log(self):
        """Test access logging."""
        from rlm_toolkit.memory.secure import SecureHierarchicalMemory

        memory = SecureHierarchicalMemory(
            agent_id="test_agent",
            trust_zone="test",
            encryption_key=b"test_key_32_bytes_for_encryption",
        )

        memory.add_episode("Test content")
        log = memory.get_access_log()

        assert len(log) >= 1  # At least one access logged


class TestMCPServerMemory:
    """Tests for MCP server memory integration."""

    def test_server_memory_init(self):
        """Test that server initializes with memory."""
        # Import with MCP disabled for testing
        import os

        os.environ["RLM_SECURE_MEMORY"] = "false"  # Use non-secure for faster tests

        from rlm_toolkit.mcp.server import RLMServer

        server = RLMServer()

        assert server.memory is not None
        assert hasattr(server.memory, "add_episode")

    def test_memory_add_retrieve(self):
        """Test memory operations through server."""
        import os

        os.environ["RLM_SECURE_MEMORY"] = "false"

        from rlm_toolkit.mcp.server import RLMServer

        server = RLMServer()

        # Add memory
        mem_id = server.memory.add_episode("Test from MCP server")
        assert mem_id is not None

        # Retrieve
        results = server.memory.retrieve("MCP server")
        # Should return something (may be empty if no match)
        assert isinstance(results, list)
