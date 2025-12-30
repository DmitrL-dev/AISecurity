"""
SENTINEL Engines Package — Built-in detection engines.
"""

from typing import List, Type

# Engine imports will be added as engines are migrated
# from sentinel.engines.injection import InjectionDetector
# from sentinel.engines.pii import PIIDetector

__all__ = [
    "BuiltinPlugin",
    "list_engines",
]


class BuiltinPlugin:
    """
    Built-in engines plugin.
    
    Registers all 200+ SENTINEL engines with the plugin manager.
    """
    
    def sentinel_register_engines(self) -> List[Type]:
        """Register all built-in engines."""
        engines = []
        
        # TODO: Import and register all 200 engines
        # engines.append(InjectionDetector)
        # engines.append(PIIDetector)
        # ...
        
        return engines


def list_engines() -> List[str]:
    """List all available engine names."""
    # TODO: Return list of all engine names
    return []
