"""
E2E Tests for Memory Bridge MCP Integration.

Tests the full MCP tool registration and execution flow.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from rlm_toolkit.memory_bridge.v2.hierarchical import (
    HierarchicalMemoryStore,
    MemoryLevel,
)
from rlm_toolkit.memory_bridge.mcp_tools_v2 import register_memory_bridge_v2_tools


class TestMCPToolRegistration:
    """Test MCP tool registration."""

    @pytest.fixture
    def mock_server(self):
        """Create a mock MCP server."""
        server = MagicMock()
        server.tool = MagicMock(return_value=lambda f: f)
        return server

    @pytest.fixture
    def store(self, tmp_path):
        """Create a temporary store."""
        db_path = tmp_path / "e2e_test.db"
        return HierarchicalMemoryStore(db_path=db_path)

    def test_registers_17_tools(self, mock_server, store):
        """Verify all 18 MCP tools are registered."""
        components = register_memory_bridge_v2_tools(mock_server, store)

        assert mock_server.tool.call_count == 18
        assert "store" in components
        assert "router" in components
        assert "orchestrator" in components
        assert "context_builder" in components

    def test_tool_names(self, mock_server, store):
        """Verify correct tool names are registered."""
        register_memory_bridge_v2_tools(mock_server, store)

        tool_calls = mock_server.tool.call_args_list
        tool_names = [call.kwargs.get("name") for call in tool_calls]

        expected_tools = [
            "rlm_discover_project",
            "rlm_route_context",
            "rlm_extract_facts",
            "rlm_approve_fact",
            "rlm_add_hierarchical_fact",
            "rlm_get_causal_chain",
            "rlm_record_causal_decision",
            "rlm_set_ttl",
            "rlm_get_stale_facts",
            "rlm_index_embeddings",
            "rlm_get_hierarchy_stats",
            "rlm_get_facts_by_domain",
            "rlm_list_domains",
            "rlm_refresh_fact",
            "rlm_delete_fact",
            "rlm_enterprise_context",
            "rlm_install_git_hooks",
        ]

        for expected in expected_tools:
            assert expected in tool_names, f"Missing tool: {expected}"


class TestEnterpriseContextE2E:
    """E2E tests for rlm_enterprise_context."""

    @pytest.fixture
    def setup_e2e(self, tmp_path):
        """Set up full E2E environment."""
        db_path = tmp_path / "e2e.db"
        store = HierarchicalMemoryStore(db_path=db_path)

        mock_server = MagicMock()
        registered_tools = {}

        def tool_decorator(**kwargs):
            def wrapper(func):
                registered_tools[kwargs.get("name")] = func
                return func

            return wrapper

        mock_server.tool = tool_decorator

        components = register_memory_bridge_v2_tools(
            mock_server, store, project_root=tmp_path
        )

        # Create project structure
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'e2e-test'")
        (tmp_path / "src").mkdir()

        return {
            "store": store,
            "components": components,
            "tools": registered_tools,
            "tmp_path": tmp_path,
        }

    @pytest.mark.asyncio
    async def test_enterprise_context_auto_mode(self, setup_e2e):
        """Test rlm_enterprise_context with auto mode."""
        tools = setup_e2e["tools"]
        store = setup_e2e["store"]

        # Add some facts
        store.add_fact("Test project", level=MemoryLevel.L0_PROJECT)

        # Get the tool
        enterprise_context = tools.get("rlm_enterprise_context")
        assert enterprise_context is not None

        # Call it
        result = await enterprise_context(
            query="How does the project work?",
            mode="auto",
            max_tokens=2000,
        )

        assert result["status"] == "success"
        assert "context" in result
        assert result["facts_count"] >= 0

    @pytest.mark.asyncio
    async def test_enterprise_context_discovery_mode(self, setup_e2e):
        """Test rlm_enterprise_context with discovery mode."""
        tools = setup_e2e["tools"]

        enterprise_context = tools.get("rlm_enterprise_context")

        result = await enterprise_context(
            query="Initial discovery",
            mode="discovery",
        )

        assert result["status"] == "success"
        # discovery_performed comes from context builder
        assert "discovery_performed" in result


class TestGitHooksE2E:
    """E2E tests for git hooks installation."""

    @pytest.fixture
    def setup_git(self, tmp_path):
        """Set up git environment."""
        db_path = tmp_path / "git_test.db"
        store = HierarchicalMemoryStore(db_path=db_path)

        mock_server = MagicMock()
        registered_tools = {}

        def tool_decorator(**kwargs):
            def wrapper(func):
                registered_tools[kwargs.get("name")] = func
                return func

            return wrapper

        mock_server.tool = tool_decorator

        # Create .git directory
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        register_memory_bridge_v2_tools(mock_server, store, project_root=tmp_path)

        return {
            "tools": registered_tools,
            "tmp_path": tmp_path,
            "git_dir": git_dir,
        }

    @pytest.mark.asyncio
    async def test_install_git_hooks(self, setup_git):
        """Test git hook installation."""
        tools = setup_git["tools"]
        git_dir = setup_git["git_dir"]

        install_hooks = tools.get("rlm_install_git_hooks")
        assert install_hooks is not None

        result = await install_hooks(hook_type="post-commit")

        assert result["status"] == "success"
        assert "hook_path" in result

        # Verify hook file exists
        hook_path = git_dir / "hooks" / "post-commit"
        assert hook_path.exists()

        # Verify content
        content = hook_path.read_text()
        assert "Memory Bridge" in content

    @pytest.mark.asyncio
    async def test_install_hooks_no_git(self, tmp_path):
        """Test error when no .git directory."""
        db_path = tmp_path / "no_git.db"
        store = HierarchicalMemoryStore(db_path=db_path)

        mock_server = MagicMock()
        registered_tools = {}

        def tool_decorator(**kwargs):
            def wrapper(func):
                registered_tools[kwargs.get("name")] = func
                return func

            return wrapper

        mock_server.tool = tool_decorator

        register_memory_bridge_v2_tools(mock_server, store, project_root=tmp_path)

        install_hooks = registered_tools.get("rlm_install_git_hooks")
        result = await install_hooks(hook_type="post-commit")

        assert result["status"] == "error"
        assert "Not a git" in result["message"]


class TestHierarchyStatsE2E:
    """E2E tests for hierarchy stats tool."""

    @pytest.fixture
    def setup_stats(self, tmp_path):
        """Set up stats environment."""
        db_path = tmp_path / "stats.db"
        store = HierarchicalMemoryStore(db_path=db_path)

        mock_server = MagicMock()
        registered_tools = {}

        def tool_decorator(**kwargs):
            def wrapper(func):
                registered_tools[kwargs.get("name")] = func
                return func

            return wrapper

        mock_server.tool = tool_decorator

        register_memory_bridge_v2_tools(mock_server, store, project_root=tmp_path)

        return {"store": store, "tools": registered_tools}

    @pytest.mark.asyncio
    async def test_get_hierarchy_stats(self, setup_stats):
        """Test hierarchy stats retrieval."""
        store = setup_stats["store"]
        tools = setup_stats["tools"]

        # Add facts
        store.add_fact("L0 fact", level=MemoryLevel.L0_PROJECT)
        store.add_fact("L1 fact", level=MemoryLevel.L1_DOMAIN, domain="test")
        store.add_fact("L2 fact", level=MemoryLevel.L2_MODULE, domain="test")

        get_stats = tools.get("rlm_get_hierarchy_stats")
        result = await get_stats()

        assert result["status"] == "success"
        # Response uses 'memory_store' key, not 'stats'
        assert result["memory_store"]["total_facts"] == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
