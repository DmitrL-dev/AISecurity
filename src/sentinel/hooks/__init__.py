"""
SENTINEL Hooks — Hook system package.
"""

from sentinel.hooks.spec import (
    hookspec,
    hookimpl, 
    SentinelHookSpec,
)
from sentinel.hooks.manager import PluginManager

__all__ = [
    "hookspec",
    "hookimpl",
    "SentinelHookSpec",
    "PluginManager",
]
