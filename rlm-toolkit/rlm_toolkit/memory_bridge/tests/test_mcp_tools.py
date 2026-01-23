# Memory Bridge — MCP Tools Tests
"""Unit tests for MCP tools with real function calls."""

import tempfile
import os
import pytest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

from rlm_toolkit.memory_bridge.models import EntityType
from rlm_toolkit.memory_bridge.storage import StateStorage
from rlm_toolkit.memory_bridge.manager import MemoryBridgeManager
from rlm_toolkit.memory_bridge.mcp_tools import register_memory_bridge_tools


@pytest.fixture
def temp_db():
    """Create a temporary database file."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db_path = Path(path)
    yield db_path
    try:
        if db_path.exists():
            db_path.unlink(missing_ok=True)
    except (PermissionError, OSError):
        pass


@pytest.fixture
def manager(temp_db):
    """Create a manager instance with active session."""
    storage = StateStorage(db_path=temp_db)
    mgr = MemoryBridgeManager(storage=storage)
    mgr.start_session(session_id="test-session")
    return mgr


@pytest.fixture
def manager_no_session(temp_db):
    """Create a manager instance without active session."""
    storage = StateStorage(db_path=temp_db)
    return MemoryBridgeManager(storage=storage)


class MockServer:
    """Mock MCP Server that captures registered tools."""

    def __init__(self):
        self.tools = {}

    def tool(self, name: str, description: str):
        """Decorator that registers and returns the tool function."""
        def decorator(func):
            self.tools[name] = func
            return func
        return decorator


@pytest.fixture
def server_with_tools(manager):
    """Create a mock server with all tools registered."""
    server = MockServer()
    register_memory_bridge_tools(server, manager)
    return server


@pytest.fixture
def server_no_session(manager_no_session):
    """Create a mock server without active session."""
    server = MockServer()
    register_memory_bridge_tools(server, manager_no_session)
    return server


class TestMCPToolsRegistration:
    """Tests for tool registration."""

    def test_register_tools(self, server_with_tools):
        """Verify all tools are registered."""
        expected_tools = [
            "rlm_sync_state",
            "rlm_restore_state",
            "rlm_get_state",
            "rlm_update_goals",
            "rlm_record_decision",
            "rlm_add_hypothesis",
            "rlm_add_fact",
            "rlm_search_facts",
            "rlm_build_communities",
            "rlm_list_sessions",
        ]

        for tool in expected_tools:
            assert tool in server_with_tools.tools, f"Tool {tool} not registered"


class TestMCPToolsIntegration:
    """Integration tests using real tool functions."""

    @pytest.mark.asyncio
    async def test_sync_state_success(self, server_with_tools):
        """Test rlm_sync_state tool."""
        result = await server_with_tools.tools["rlm_sync_state"]()
        assert result["status"] == "success"
        assert result["version"] == 1
        assert "State synced" in result["message"]

    @pytest.mark.asyncio
    async def test_restore_state(self, server_with_tools, manager):
        """Test rlm_restore_state tool."""
        # First sync
        await server_with_tools.tools["rlm_sync_state"]()

        result = await server_with_tools.tools["rlm_restore_state"](
            session_id="test-session"
        )
        assert result["status"] == "success"
        assert result["session_id"] == "test-session"

    @pytest.mark.asyncio
    async def test_get_state(self, server_with_tools):
        """Test rlm_get_state tool."""
        result = await server_with_tools.tools["rlm_get_state"](max_tokens=500)
        assert result["status"] == "success"
        assert "compact_state" in result
        assert result["session_id"] == "test-session"

    @pytest.mark.asyncio
    async def test_update_goals(self, server_with_tools):
        """Test rlm_update_goals tool."""
        result = await server_with_tools.tools["rlm_update_goals"](
            description="Build Memory Bridge",
            progress=0.5,
        )
        assert result["status"] == "success"
        assert result["description"] == "Build Memory Bridge"
        assert result["progress"] == 0.5

    @pytest.mark.asyncio
    async def test_update_goals_without_progress(self, server_with_tools):
        """Test rlm_update_goals tool without progress."""
        result = await server_with_tools.tools["rlm_update_goals"](
            description="Another goal",
        )
        assert result["status"] == "success"
        assert result["progress"] == 0.0

    @pytest.mark.asyncio
    async def test_record_decision(self, server_with_tools):
        """Test rlm_record_decision tool."""
        result = await server_with_tools.tools["rlm_record_decision"](
            description="Use SQLite",
            rationale="Local-first, no server needed",
            alternatives=["PostgreSQL", "MongoDB"],
        )
        assert result["status"] == "success"
        assert result["description"] == "Use SQLite"

    @pytest.mark.asyncio
    async def test_add_hypothesis(self, server_with_tools):
        """Test rlm_add_hypothesis tool."""
        result = await server_with_tools.tools["rlm_add_hypothesis"](
            statement="SQLite will be fast enough",
        )
        assert result["status"] == "success"
        assert result["statement"] == "SQLite will be fast enough"
        assert result["hypothesis_status"] == "proposed"

    @pytest.mark.asyncio
    async def test_add_fact(self, server_with_tools):
        """Test rlm_add_fact tool."""
        result = await server_with_tools.tools["rlm_add_fact"](
            content="SQLite is the storage backend",
            entity_type="fact",
            confidence=0.95,
        )
        assert result["status"] == "success"
        assert result["entity_type"] == "fact"
        assert result["content"] == "SQLite is the storage backend"

    @pytest.mark.asyncio
    async def test_add_fact_with_custom_type(self, server_with_tools):
        """Test rlm_add_fact with custom type."""
        result = await server_with_tools.tools["rlm_add_fact"](
            content="Custom setting",
            entity_type="custom",
            custom_type_name="app_config",
        )
        assert result["status"] == "success"
        assert result["entity_type"] == "custom"

    @pytest.mark.asyncio
    async def test_add_fact_invalid_type(self, server_with_tools):
        """Test rlm_add_fact with invalid entity type falls back to OTHER."""
        result = await server_with_tools.tools["rlm_add_fact"](
            content="Unknown type fact",
            entity_type="invalid_type_xyz",
        )
        assert result["status"] == "success"
        assert result["entity_type"] == "other"

    @pytest.mark.asyncio
    async def test_search_facts(self, server_with_tools, manager):
        """Test rlm_search_facts tool."""
        # Add some facts first
        manager.add_fact("SQLite is fast", EntityType.FACT)
        manager.add_fact("PostgreSQL is powerful", EntityType.FACT)

        result = await server_with_tools.tools["rlm_search_facts"](
            query="SQLite database",
            top_k=10,
        )
        assert result["status"] == "success"
        assert result["query"] == "SQLite database"
        assert len(result["results"]) >= 1

    @pytest.mark.asyncio
    async def test_search_facts_with_weights(self, server_with_tools, manager):
        """Test rlm_search_facts with custom weights."""
        manager.add_fact("Test fact", EntityType.FACT)

        result = await server_with_tools.tools["rlm_search_facts"](
            query="test",
            top_k=5,
            semantic_weight=0.2,
            keyword_weight=0.6,
            recency_weight=0.2,
        )
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_build_communities(self, server_with_tools):
        """Test rlm_build_communities tool."""
        result = await server_with_tools.tools["rlm_build_communities"](
            min_cluster_size=3,
        )
        assert result["status"] == "success"
        assert "communities_count" in result

    @pytest.mark.asyncio
    async def test_list_sessions(self, server_with_tools):
        """Test rlm_list_sessions tool."""
        # Sync to save the session
        await server_with_tools.tools["rlm_sync_state"]()

        result = await server_with_tools.tools["rlm_list_sessions"]()
        assert result["status"] == "success"
        assert len(result["sessions"]) >= 1


class TestMCPToolsErrorHandling:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_sync_state_no_session(self, server_no_session):
        """Test error when no session exists."""
        result = await server_no_session.tools["rlm_sync_state"]()
        assert result["status"] == "error"
        assert "No active session" in result["message"]

    @pytest.mark.asyncio
    async def test_get_state_no_session(self, server_no_session):
        """Test get_state returns empty when no session."""
        result = await server_no_session.tools["rlm_get_state"]()
        assert result["status"] == "success"
        assert result["compact_state"] == ""
        assert result["session_id"] is None

    @pytest.mark.asyncio
    async def test_update_goals_no_session(self, server_no_session):
        """Test error when updating goals without session."""
        result = await server_no_session.tools["rlm_update_goals"](
            description="Test",
        )
        assert result["status"] == "error"
        assert "No active session" in result["message"]

    @pytest.mark.asyncio
    async def test_record_decision_no_session(self, server_no_session):
        """Test error when recording decision without session."""
        result = await server_no_session.tools["rlm_record_decision"](
            description="Test",
            rationale="Reason",
        )
        assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_add_hypothesis_no_session(self, server_no_session):
        """Test error when adding hypothesis without session."""
        result = await server_no_session.tools["rlm_add_hypothesis"](
            statement="Test",
        )
        assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_add_fact_no_session(self, server_no_session):
        """Test error when adding fact without session."""
        result = await server_no_session.tools["rlm_add_fact"](
            content="Test",
        )
        assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_search_facts_no_session(self, server_no_session):
        """Test search returns empty when no session."""
        result = await server_no_session.tools["rlm_search_facts"](
            query="test",
        )
        assert result["status"] == "success"
        assert result["results"] == []

    @pytest.mark.asyncio
    async def test_build_communities_no_session(self, server_no_session):
        """Test build_communities returns empty when no session."""
        result = await server_no_session.tools["rlm_build_communities"]()
        assert result["status"] == "success"
        assert result["communities_count"] == 0
