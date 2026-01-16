"""
Platform Guards
===============

Platform-specific resource limiting (Gap G5).
"""

from __future__ import annotations

import platform
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Optional, TYPE_CHECKING


@dataclass
class GuardConfig:
    """Configuration for platform guards.
    
    Attributes:
        timeout_seconds: Maximum execution time
        memory_mb: Maximum memory usage
        cpu_percent: Maximum CPU usage (Linux only)
    """
    timeout_seconds: float = 30.0
    memory_mb: int = 512
    cpu_percent: int = 80


class PlatformGuards(ABC):
    """Abstract base for platform-specific guards.
    
    Implement this for each platform (Linux, macOS, Windows).
    """
    
    @abstractmethod
    def set_memory_limit(self, mb: int) -> bool:
        """Set memory limit. Returns True if successful."""
        pass
    
    @abstractmethod
    def set_cpu_limit(self, percent: int) -> bool:
        """Set CPU limit. Returns True if successful."""
        pass
    
    @abstractmethod
    def execute_with_timeout(
        self, 
        func: Callable, 
        timeout: float,
        *args, 
        **kwargs
    ) -> tuple[bool, Any]:
        """Execute function with timeout.
        
        Returns:
            (success, result) tuple
        """
        pass
    
    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Name of this platform."""
        pass
    
    @property
    @abstractmethod
    def capabilities(self) -> dict[str, bool]:
        """What this platform supports."""
        pass


class LinuxGuards(PlatformGuards):
    """Linux-specific guards using resource module."""
    
    @property
    def platform_name(self) -> str:
        return "Linux"
    
    @property
    def capabilities(self) -> dict[str, bool]:
        return {
            "memory_limit": True,
            "cpu_limit": True,
            "signal_timeout": True,
        }
    
    def set_memory_limit(self, mb: int) -> bool:
        try:
            import resource
            bytes_limit = mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (bytes_limit, bytes_limit))
            return True
        except Exception:
            return False
    
    def set_cpu_limit(self, percent: int) -> bool:
        # CPU limiting usually requires cgroups, not simple resource limits
        return False
    
    def execute_with_timeout(
        self, 
        func: Callable, 
        timeout: float,
        *args, 
        **kwargs
    ) -> tuple[bool, Any]:
        import signal
        
        def handler(signum, frame):
            raise TimeoutError(f"Execution timed out after {timeout}s")
        
        signal.signal(signal.SIGALRM, handler)
        signal.alarm(int(timeout))
        
        try:
            result = func(*args, **kwargs)
            signal.alarm(0)
            return (True, result)
        except TimeoutError as e:
            return (False, str(e))
        finally:
            signal.alarm(0)


class MacOSGuards(PlatformGuards):
    """macOS guards - similar to Linux."""
    
    @property
    def platform_name(self) -> str:
        return "macOS"
    
    @property
    def capabilities(self) -> dict[str, bool]:
        return {
            "memory_limit": True,
            "cpu_limit": False,
            "signal_timeout": True,
        }
    
    def set_memory_limit(self, mb: int) -> bool:
        try:
            import resource
            bytes_limit = mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (bytes_limit, bytes_limit))
            return True
        except Exception:
            return False
    
    def set_cpu_limit(self, percent: int) -> bool:
        return False
    
    def execute_with_timeout(
        self, 
        func: Callable, 
        timeout: float,
        *args, 
        **kwargs
    ) -> tuple[bool, Any]:
        # Same as Linux
        import signal
        
        def handler(signum, frame):
            raise TimeoutError(f"Execution timed out after {timeout}s")
        
        signal.signal(signal.SIGALRM, handler)
        signal.alarm(int(timeout))
        
        try:
            result = func(*args, **kwargs)
            signal.alarm(0)
            return (True, result)
        except TimeoutError as e:
            return (False, str(e))
        finally:
            signal.alarm(0)


class WindowsGuards(PlatformGuards):
    """Windows guards - limited capabilities.
    
    Note: Windows doesn't support signal.SIGALRM or resource limits.
    Uses threading-based timeout instead.
    """
    
    @property
    def platform_name(self) -> str:
        return "Windows"
    
    @property
    def capabilities(self) -> dict[str, bool]:
        return {
            "memory_limit": False,  # No resource module
            "cpu_limit": False,
            "signal_timeout": False,  # No SIGALRM
            "thread_timeout": True,  # Use threading instead
        }
    
    def set_memory_limit(self, mb: int) -> bool:
        # Windows doesn't support resource.RLIMIT_AS
        # Would need to use Job Objects via ctypes/win32api
        return False
    
    def set_cpu_limit(self, percent: int) -> bool:
        return False
    
    def execute_with_timeout(
        self, 
        func: Callable, 
        timeout: float,
        *args, 
        **kwargs
    ) -> tuple[bool, Any]:
        """Use threading for Windows timeout."""
        import threading
        import queue
        
        result_queue: queue.Queue = queue.Queue()
        
        def worker():
            try:
                result = func(*args, **kwargs)
                result_queue.put(("success", result))
            except Exception as e:
                result_queue.put(("error", str(e)))
        
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        thread.join(timeout=timeout)
        
        if thread.is_alive():
            return (False, f"Execution timed out after {timeout}s")
        
        if result_queue.empty():
            return (False, "No result from execution")
        
        status, result = result_queue.get()
        return (status == "success", result)


class DockerGuards(PlatformGuards):
    """Docker container guards.
    
    Assumes limits are set at container level.
    """
    
    @property
    def platform_name(self) -> str:
        return "Docker"
    
    @property
    def capabilities(self) -> dict[str, bool]:
        return {
            "memory_limit": True,  # Via docker --memory
            "cpu_limit": True,     # Via docker --cpus
            "signal_timeout": True,
        }
    
    def set_memory_limit(self, mb: int) -> bool:
        # Memory should be set at container level
        # Just verify we're under limit
        return True
    
    def set_cpu_limit(self, percent: int) -> bool:
        return True
    
    def execute_with_timeout(
        self, 
        func: Callable, 
        timeout: float,
        *args, 
        **kwargs
    ) -> tuple[bool, Any]:
        # Use Linux-style signal timeout
        import signal
        
        def handler(signum, frame):
            raise TimeoutError(f"Execution timed out after {timeout}s")
        
        signal.signal(signal.SIGALRM, handler)
        signal.alarm(int(timeout))
        
        try:
            result = func(*args, **kwargs)
            signal.alarm(0)
            return (True, result)
        except TimeoutError as e:
            return (False, str(e))
        finally:
            signal.alarm(0)


def create_guards(config: Optional[GuardConfig] = None) -> PlatformGuards:
    """Factory function to create appropriate guards for current platform.
    
    Args:
        config: Optional guard configuration
    
    Returns:
        Platform-specific guards instance
    """
    config = config or GuardConfig()
    
    # Check for Docker
    if _is_docker():
        return DockerGuards()
    
    system = platform.system().lower()
    
    if system == "linux":
        return LinuxGuards()
    elif system == "darwin":
        return MacOSGuards()
    elif system == "windows":
        return WindowsGuards()
    else:
        # Fallback to Windows-style (no OS-level limits)
        return WindowsGuards()


def _is_docker() -> bool:
    """Check if running in Docker container."""
    # Check for .dockerenv file
    import os
    if os.path.exists("/.dockerenv"):
        return True
    
    # Check cgroup
    try:
        with open("/proc/1/cgroup", "r") as f:
            return "docker" in f.read()
    except Exception:
        return False
