"""
SENTINEL Engines Package — Built-in detection engines.
"""

from typing import List, Type
import logging

logger = logging.getLogger(__name__)

__all__ = [
    "BuiltinPlugin",
    "list_engines",
    "get_engine",
]


class BuiltinPlugin:
    """
    Built-in engines plugin.

    Registers all 200+ SENTINEL engines with the plugin manager.
    Uses adapter pattern for backwards compatibility.
    """

    def sentinel_register_engines(self) -> List[Type]:
        """Register all built-in engines."""
        engines = []

        # Try to adapt legacy engines
        try:
            from sentinel.engines.adapter import adapt_all_engines

            adapted = adapt_all_engines()
            engines.extend(adapted)
            logger.info(f"Registered {len(adapted)} adapted engines")
        except ImportError as e:
            logger.debug(f"Adapter not available: {e}")

        # Add native framework engines
        try:
            from sentinel.engines.example_injection import ExampleInjectionEngine

            engines.append(ExampleInjectionEngine)
        except ImportError:
            pass

        return engines


def list_engines() -> List[str]:
    """List all available engine names."""
    from sentinel.core.engine import list_engines as core_list

    return core_list()


def get_engine(name: str):
    """Get engine class by name."""
    from sentinel.core.engine import get_engine as core_get

    return core_get(name)
