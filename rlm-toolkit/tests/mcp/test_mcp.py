"""Tests for RLM MCP Server."""

import pytest
from pathlib import Path
import tempfile
import os

from rlm_toolkit.mcp.contexts import ContextManager
from rlm_toolkit.mcp.providers import ProviderRouter, Provider
from rlm_toolkit.mcp.server import RLMServer


class TestContextManager:
    """Tests for ContextManager."""
    
    def test_init(self):
        """Test context manager initialization."""
        cm = ContextManager()
        assert cm.contexts == {}
        assert cm.storage_dir is not None
    
    @pytest.mark.asyncio
    async def test_load_file(self, tmp_path):
        """Test loading a single file."""
        # Create test file
        test_file = tmp_path / "test.py"
        test_file.write_text("def hello():\n    print('Hello, World!')\n")
        
        cm = ContextManager(storage_dir=str(tmp_path / ".rlm"))
        result = await cm.load(str(test_file))
        
        assert result["name"] == "test.py"
        assert result["file_count"] == 1
        assert result["token_count"] > 0
    
    @pytest.mark.asyncio
    async def test_load_directory(self, tmp_path):
        """Test loading a directory."""
        # Create test files
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("print('main')")
        (tmp_path / "src" / "utils.py").write_text("print('utils')")
        
        cm = ContextManager(storage_dir=str(tmp_path / ".rlm"))
        result = await cm.load(str(tmp_path / "src"))
        
        assert result["name"] == "src"
        assert result["file_count"] == 2
    
    def test_get_context(self):
        """Test getting a context."""
        cm = ContextManager()
        cm.contexts["test"] = {"name": "test", "content": "hello"}
        
        result = cm.get("test")
        assert result["name"] == "test"
        
        result = cm.get("nonexistent")
        assert result is None
    
    def test_list_all(self):
        """Test listing all contexts."""
        cm = ContextManager()
        cm.contexts["ctx1"] = {"name": "ctx1", "content": "a"}
        cm.contexts["ctx2"] = {"name": "ctx2", "content": "b"}
        
        result = cm.list_all()
        assert len(result) == 2
        # Content should not be in result
        for ctx in result:
            assert "content" not in ctx


class TestProviderRouter:
    """Tests for ProviderRouter."""
    
    def test_init(self):
        """Test provider router initialization."""
        router = ProviderRouter()
        assert isinstance(router.available_providers, dict)
    
    def test_get_provider_default(self):
        """Test getting default provider."""
        router = ProviderRouter()
        provider = router.get_provider()
        # May be None if no providers available
        assert provider is None or isinstance(provider, Provider)
    
    def test_get_status(self):
        """Test getting router status."""
        router = ProviderRouter()
        status = router.get_status()
        
        assert "available_providers" in status
        assert "default_provider" in status


class TestRLMServer:
    """Tests for RLMServer."""
    
    def test_init(self):
        """Test server initialization."""
        server = RLMServer()
        assert server.context_manager is not None
        assert server.provider_router is not None
    
    def test_keyword_search(self):
        """Test keyword search."""
        server = RLMServer()
        content = """
This line contains hello word
Another line with world
Hello is here too
goodbye line
"""
        
        results = server._keyword_search(content, "hello")
        assert len(results) > 0
        # "hello" should appear in top results
        assert any("hello" in r["content"].lower() for r in results)
    
    def test_keyword_search_no_match(self):
        """Test keyword search with no matches."""
        server = RLMServer()
        content = "This is a test document."
        
        results = server._keyword_search(content, "nonexistent xyz")
        # May return empty or low-score results
        assert isinstance(results, list)


class TestMCPIntegration:
    """Integration tests for MCP server."""
    
    @pytest.mark.asyncio
    async def test_load_and_query(self, tmp_path):
        """Test loading a context and querying it."""
        # Create test file
        test_file = tmp_path / "sample.py"
        test_file.write_text("""
class UserService:
    def get_user(self, user_id):
        '''Get user by ID.'''
        return self.db.find(user_id)
    
    def create_user(self, name, email):
        '''Create a new user.'''
        return self.db.insert({'name': name, 'email': email})
""")
        
        server = RLMServer()
        server.context_manager = ContextManager(storage_dir=str(tmp_path / ".rlm"))
        
        # Load context
        result = await server.context_manager.load(str(test_file), "sample")
        assert result["name"] == "sample"
        
        # Query
        context = server.context_manager.get("sample")
        results = server._keyword_search(context["content"], "user")
        
        assert len(results) > 0
        assert any("user" in r["content"].lower() for r in results)
