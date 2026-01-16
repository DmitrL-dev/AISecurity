"""Unit tests for platform guards module."""

import pytest
import platform
import time

from rlm_toolkit.security.platform_guards import (
    GuardConfig,
    PlatformGuards,
    WindowsGuards,
    create_guards,
)


class TestGuardConfig:
    """Tests for GuardConfig."""
    
    def test_default_config(self):
        """Test default configuration."""
        config = GuardConfig()
        
        assert config.timeout_seconds == 30.0
        assert config.memory_mb == 512
        assert config.cpu_percent == 80
    
    def test_custom_config(self):
        """Test custom configuration."""
        config = GuardConfig(
            timeout_seconds=60.0,
            memory_mb=1024,
            cpu_percent=50,
        )
        
        assert config.timeout_seconds == 60.0
        assert config.memory_mb == 1024
        assert config.cpu_percent == 50


class TestGetPlatformGuards:
    """Tests for create_guards factory."""
    
    def test_returns_guards(self):
        """Test factory returns platform-appropriate guards."""
        guards = create_guards()
        
        assert guards is not None
        assert isinstance(guards, PlatformGuards)
    
    def test_platform_name(self):
        """Test correct platform name."""
        guards = create_guards()
        
        current = platform.system().lower()
        assert guards.platform_name.lower() in ["windows", "linux", "darwin", "macos"]
    
    def test_capabilities(self):
        """Test capabilities are returned."""
        guards = create_guards()
        caps = guards.capabilities
        
        assert isinstance(caps, dict)
        # Different platforms have different timeout keys
        assert "memory_limit" in caps


class TestWindowsGuards:
    """Tests for WindowsGuards."""
    
    def test_creation(self):
        """Test guards creation."""
        guards = WindowsGuards()
        
        assert guards.platform_name == "Windows"
    
    def test_capabilities(self):
        """Test Windows capabilities."""
        guards = WindowsGuards()
        caps = guards.capabilities
        
        assert caps["thread_timeout"] is True
        # Windows has limited memory support
        assert "memory_limit" in caps
    
    def test_set_memory_limit(self):
        """Test memory limit (may not be supported)."""
        guards = WindowsGuards()
        result = guards.set_memory_limit(512)
        
        # Should return False on Windows (not supported)
        assert isinstance(result, bool)
    
    def test_set_cpu_limit(self):
        """Test CPU limit."""
        guards = WindowsGuards()
        result = guards.set_cpu_limit(80)
        
        assert isinstance(result, bool)
    
    def test_execute_with_timeout_success(self):
        """Test successful execution within timeout."""
        guards = WindowsGuards()
        
        def quick_func():
            return 42
        
        success, result = guards.execute_with_timeout(quick_func, timeout=5.0)
        
        assert success is True
        assert result == 42
    
    def test_execute_with_timeout_timeout(self):
        """Test timeout is enforced."""
        guards = WindowsGuards()
        
        def slow_func():
            time.sleep(10)
            return "done"
        
        success, result = guards.execute_with_timeout(slow_func, timeout=0.1)
        
        # Should timeout
        assert success is False
    
    def test_execute_with_args(self):
        """Test execution with arguments."""
        guards = WindowsGuards()
        
        def add(a, b):
            return a + b
        
        success, result = guards.execute_with_timeout(add, 5.0, 2, 3)
        
        assert success is True
        assert result == 5
    
    def test_execute_with_kwargs(self):
        """Test execution with keyword arguments."""
        guards = WindowsGuards()
        
        def greet(name, greeting="Hello"):
            return f"{greeting}, {name}!"
        
        success, result = guards.execute_with_timeout(
            greet, 5.0, "World", greeting="Hi"
        )
        
        assert success is True
        assert result == "Hi, World!"


class TestPlatformGuardsInterface:
    """Tests for PlatformGuards interface."""
    
    def test_all_methods_exist(self):
        """Test all required methods exist."""
        guards = create_guards()
        
        assert hasattr(guards, "set_memory_limit")
        assert hasattr(guards, "set_cpu_limit")
        assert hasattr(guards, "execute_with_timeout")
        assert hasattr(guards, "platform_name")
        assert hasattr(guards, "capabilities")
    
    def test_methods_are_callable(self):
        """Test methods are callable."""
        guards = create_guards()
        
        assert callable(guards.set_memory_limit)
        assert callable(guards.set_cpu_limit)
        assert callable(guards.execute_with_timeout)
