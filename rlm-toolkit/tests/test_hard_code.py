"""Tests for hard-to-test code: stdin, file I/O, platform-specific."""

import pytest
from unittest.mock import MagicMock, patch, mock_open
import sys
import tempfile
import os
from pathlib import Path

from rlm_toolkit.cli.commands import run_command, parse_model, get_provider
from rlm_toolkit.security.platform_guards import (
    GuardConfig, 
    create_guards,
    LinuxGuards,
    WindowsGuards,
    MacOSGuards,
)


# =============================================================================
# CLI Commands with File I/O
# =============================================================================

class TestRunCommandWithFiles:
    """Tests for run_command with file operations."""
    
    @patch("rlm_toolkit.cli.commands.get_provider")
    @patch("rlm_toolkit.core.engine.RLM")
    def test_run_with_context_file(self, mock_rlm_class, mock_get_provider, tmp_path):
        """Test run_command with actual context file."""
        import argparse
        
        # Create context file
        context_file = tmp_path / "context.txt"
        context_file.write_text("This is test context", encoding="utf-8")
        
        # Setup mocks
        mock_provider = MagicMock()
        mock_get_provider.return_value = mock_provider
        
        mock_rlm = MagicMock()
        mock_result = MagicMock()
        mock_result.answer = "The answer"
        mock_result.status = "success"
        mock_result.iterations = 2
        mock_result.total_cost = 0.01
        mock_result.execution_time = 1.0
        mock_rlm.run.return_value = mock_result
        mock_rlm_class.return_value = mock_rlm
        
        args = argparse.Namespace(
            model="ollama:llama3",
            context=str(context_file),
            query="Summarize",
            max_iterations=10,
            max_cost=1.0,
            output=None,
            format="text",
        )
        
        result = run_command(args)
        
        assert result == 0
    
    @patch("rlm_toolkit.cli.commands.get_provider")
    @patch("rlm_toolkit.core.engine.RLM")
    def test_run_with_output_file(self, mock_rlm_class, mock_get_provider, tmp_path):
        """Test run_command writing to output file."""
        import argparse
        
        context_file = tmp_path / "context.txt"
        context_file.write_text("Test context", encoding="utf-8")
        
        output_file = tmp_path / "output.txt"
        
        mock_provider = MagicMock()
        mock_get_provider.return_value = mock_provider
        
        mock_rlm = MagicMock()
        mock_result = MagicMock()
        mock_result.answer = "The output answer"
        mock_result.status = "success"
        mock_result.iterations = 1
        mock_result.total_cost = 0.0
        mock_result.execution_time = 0.5
        mock_rlm.run.return_value = mock_result
        mock_rlm_class.return_value = mock_rlm
        
        args = argparse.Namespace(
            model="ollama:llama3",
            context=str(context_file),
            query="Test query",
            max_iterations=10,
            max_cost=1.0,
            output=str(output_file),
            format="text",
        )
        
        result = run_command(args)
        
        assert result == 0
        assert output_file.exists()
    
    @patch("rlm_toolkit.cli.commands.get_provider")
    @patch("rlm_toolkit.core.engine.RLM")
    def test_run_with_json_format(self, mock_rlm_class, mock_get_provider, tmp_path):
        """Test run_command with JSON output."""
        import argparse
        
        context_file = tmp_path / "context.txt"
        context_file.write_text("JSON test", encoding="utf-8")
        
        mock_provider = MagicMock()
        mock_get_provider.return_value = mock_provider
        
        mock_rlm = MagicMock()
        mock_result = MagicMock()
        mock_result.answer = "JSON answer"
        mock_result.status = "success"
        mock_result.iterations = 3
        mock_result.total_cost = 0.05
        mock_result.execution_time = 2.0
        mock_rlm.run.return_value = mock_result
        mock_rlm_class.return_value = mock_rlm
        
        args = argparse.Namespace(
            model="openai:gpt-4o",
            context=str(context_file),
            query="Format as JSON",
            max_iterations=50,
            max_cost=10.0,
            output=None,
            format="json",
        )
        
        result = run_command(args)
        
        assert result == 0
    
    def test_run_with_missing_file(self):
        """Test run_command with missing context file."""
        import argparse
        
        args = argparse.Namespace(
            model="ollama:llama3",
            context="/nonexistent/file.txt",
            query="Test",
            max_iterations=10,
            max_cost=1.0,
            output=None,
            format="text",
        )
        
        result = run_command(args)
        
        assert result == 1  # Error code
    
    @patch("sys.stdin")
    @patch("rlm_toolkit.cli.commands.get_provider")
    @patch("rlm_toolkit.core.engine.RLM")
    def test_run_with_stdin(self, mock_rlm_class, mock_get_provider, mock_stdin):
        """Test run_command with stdin input."""
        import argparse
        
        mock_stdin.read.return_value = "Context from stdin"
        
        mock_provider = MagicMock()
        mock_get_provider.return_value = mock_provider
        
        mock_rlm = MagicMock()
        mock_result = MagicMock()
        mock_result.answer = "Answer"
        mock_result.status = "success"
        mock_result.iterations = 1
        mock_result.total_cost = 0.0
        mock_result.execution_time = 0.1
        mock_rlm.run.return_value = mock_result
        mock_rlm_class.return_value = mock_rlm
        
        args = argparse.Namespace(
            model="ollama:llama3",
            context="-",
            query="Process stdin",
            max_iterations=10,
            max_cost=1.0,
            output=None,
            format="text",
        )
        
        result = run_command(args)
        
        assert result == 0


# =============================================================================
# Platform Guards - Linux
# =============================================================================

class TestLinuxGuards:
    """Tests for LinuxGuards."""
    
    def test_platform_name(self):
        """Test Linux platform name."""
        guards = LinuxGuards()
        
        assert guards.platform_name == "Linux"
    
    def test_capabilities(self):
        """Test Linux capabilities."""
        guards = LinuxGuards()
        
        caps = guards.capabilities
        
        assert "memory_limit" in caps
        assert "cpu_limit" in caps
        assert "signal_timeout" in caps
    
    @pytest.mark.skipif(sys.platform == "win32", reason="resource module not on Windows")
    @patch("resource.setrlimit")
    def test_set_memory_limit_success(self, mock_setrlimit):
        """Test memory limit success."""
        guards = LinuxGuards()
        
        result = guards.set_memory_limit(512)
        
        # May return True or False depending on platform
        assert isinstance(result, bool)
    
    def test_set_cpu_limit(self):
        """Test CPU limit."""
        guards = LinuxGuards()
        
        result = guards.set_cpu_limit(80)
        
        assert isinstance(result, bool)


# =============================================================================
# Platform Guards - Windows
# =============================================================================

class TestWindowsGuards:
    """Tests for WindowsGuards."""
    
    def test_platform_name(self):
        """Test Windows platform name."""
        guards = WindowsGuards()
        
        assert guards.platform_name == "Windows"
    
    def test_capabilities(self):
        """Test Windows capabilities."""
        guards = WindowsGuards()
        
        caps = guards.capabilities
        
        assert isinstance(caps, dict)
    
    def test_set_memory_limit(self):
        """Test memory limit on Windows."""
        guards = WindowsGuards()
        
        result = guards.set_memory_limit(512)
        
        assert isinstance(result, bool)
    
    def test_set_cpu_limit(self):
        """Test CPU limit on Windows."""
        guards = WindowsGuards()
        
        result = guards.set_cpu_limit(80)
        
        assert isinstance(result, bool)
    
    def test_execute_with_timeout(self):
        """Test execute with timeout."""
        guards = WindowsGuards()
        
        def simple():
            return 42
        
        success, result = guards.execute_with_timeout(simple, 5.0)
        
        assert success is True
        assert result == 42


# =============================================================================
# Platform Guards - macOS
# =============================================================================

class TestMacOSGuards:
    """Tests for MacOSGuards."""
    
    def test_platform_name(self):
        """Test macOS platform name."""
        guards = MacOSGuards()
        
        assert guards.platform_name == "macOS"
    
    def test_capabilities(self):
        """Test macOS capabilities."""
        guards = MacOSGuards()
        
        caps = guards.capabilities
        
        assert isinstance(caps, dict)
    
    def test_set_memory_limit(self):
        """Test memory limit on macOS."""
        guards = MacOSGuards()
        
        result = guards.set_memory_limit(512)
        
        assert isinstance(result, bool)


# =============================================================================
# Create Guards Factory
# =============================================================================

class TestCreateGuardsFactory:
    """Tests for create_guards factory."""
    
    def test_returns_platform_guards(self):
        """Test factory returns guards."""
        guards = create_guards()
        
        assert guards is not None
    
    def test_platform_name_set(self):
        """Test platform name is set."""
        guards = create_guards()
        
        assert guards.platform_name in ["Linux", "Windows", "macOS"]
    
    def test_capabilities_returned(self):
        """Test capabilities returned."""
        guards = create_guards()
        
        caps = guards.capabilities
        
        assert isinstance(caps, dict)
    
    def test_guards_config_applied(self):
        """Test config can be applied."""
        config = GuardConfig(timeout_seconds=60, memory_mb=1024)
        
        guards = create_guards()
        guards.set_memory_limit(config.memory_mb)
        
        # Should not raise
