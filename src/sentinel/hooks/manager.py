"""
Plugin Manager — discovers and manages SENTINEL plugins.

Handles:
- Built-in plugin loading
- Entry point discovery (pip installed plugins)
- Local plugin loading (sentinel_plugins.py)
- Hook invocation
"""

import logging
from typing import List, Optional, Dict, Any, Type
import importlib.metadata

from sentinel.hooks.spec import SentinelHookSpec, PLUGGY_AVAILABLE

if PLUGGY_AVAILABLE:
    import pluggy

logger = logging.getLogger(__name__)


class PluginManager:
    """
    Manages plugin discovery, loading, and hook invocation.
    
    Discovers plugins from:
    1. Built-in plugins (core engines)
    2. Entry points (pip installed packages)
    3. Local plugins (sentinel_plugins.py in cwd)
    
    Usage:
        >>> pm = PluginManager()
        >>> pm.load_plugins()
        >>> engines = pm.hook.sentinel_register_engines()
    """
    
    ENTRY_POINT_GROUP = "sentinel.plugins"
    
    def __init__(self):
        if PLUGGY_AVAILABLE:
            self._pm = pluggy.PluginManager("sentinel")
            self._pm.add_hookspecs(SentinelHookSpec)
        else:
            self._pm = None
            logger.warning(
                "pluggy not installed, plugin system disabled. "
                "Install with: pip install pluggy"
            )
        
        self._plugins: Dict[str, Any] = {}
        self._loaded = False
    
    @property
    def hook(self):
        """Access hooks for invocation."""
        if self._pm:
            return self._pm.hook
        return _DummyHook()
    
    def load_plugins(self) -> None:
        """Load all plugins from all sources."""
        if self._loaded:
            return
        
        self._load_builtin_plugins()
        self._load_entrypoint_plugins()
        self._load_local_plugins()
        
        self._loaded = True
        logger.info(f"Loaded {len(self._plugins)} plugins")
    
    def _load_builtin_plugins(self) -> None:
        """Load built-in plugins."""
        try:
            from sentinel.engines import BuiltinPlugin
            self.register(BuiltinPlugin(), "builtin")
        except ImportError:
            logger.debug("No builtin engines plugin found")
    
    def _load_entrypoint_plugins(self) -> None:
        """Load plugins registered via entry points."""
        if not PLUGGY_AVAILABLE:
            return
        
        try:
            # Python 3.10+ way
            eps = importlib.metadata.entry_points(
                group=self.ENTRY_POINT_GROUP
            )
            for ep in eps:
                try:
                    plugin = ep.load()
                    self.register(plugin, ep.name)
                    logger.info(f"Loaded plugin: {ep.name}")
                except Exception as e:
                    logger.error(f"Failed to load plugin {ep.name}: {e}")
        except Exception as e:
            logger.debug(f"Entry point loading skipped: {e}")
    
    def _load_local_plugins(self) -> None:
        """Load local plugins from sentinel_plugins.py in cwd."""
        import sys
        import os
        
        # Check for sentinel_plugins.py in current directory
        plugins_file = os.path.join(os.getcwd(), "sentinel_plugins.py")
        if os.path.exists(plugins_file):
            try:
                import importlib.util
                spec = importlib.util.spec_from_file_location(
                    "sentinel_plugins", plugins_file
                )
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # Look for Plugin classes
                    for name in dir(module):
                        obj = getattr(module, name)
                        if (
                            isinstance(obj, type) and
                            name.endswith("Plugin")
                        ):
                            self.register(obj(), f"local.{name}")
                    
                    logger.info(f"Loaded local plugins from {plugins_file}")
            except Exception as e:
                logger.error(f"Failed to load local plugins: {e}")
    
    def register(self, plugin: Any, name: str) -> None:
        """Register a plugin."""
        if name in self._plugins:
            logger.warning(f"Plugin {name} already registered, skipping")
            return
        
        self._plugins[name] = plugin
        
        if self._pm:
            self._pm.register(plugin, name)
    
    def unregister(self, name: str) -> None:
        """Unregister a plugin."""
        if name in self._plugins:
            plugin = self._plugins.pop(name)
            if self._pm:
                self._pm.unregister(plugin)
    
    def list_plugins(self) -> List[str]:
        """List registered plugin names."""
        return list(self._plugins.keys())
    
    def get_plugin(self, name: str) -> Optional[Any]:
        """Get plugin by name."""
        return self._plugins.get(name)


class _DummyHook:
    """Dummy hook object when pluggy not available."""
    
    def __getattr__(self, name):
        def dummy_hook(*args, **kwargs):
            return []
        return dummy_hook


# Global plugin manager instance
_plugin_manager: Optional[PluginManager] = None


def get_plugin_manager() -> PluginManager:
    """Get or create global plugin manager."""
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager()
        _plugin_manager.load_plugins()
    return _plugin_manager
