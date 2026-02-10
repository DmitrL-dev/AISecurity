"""
SENTINEL Shield v2.0 — Plugin Loader

Discovers and loads custom detection engine plugins
from a specified directory.

Plugin contract:
- File: <name>.py in plugins directory
- Class: must extend BaseEngine
- Class name: must end with 'Engine'

Example plugin (plugins/my_custom_engine.py):

    from engines.base import BaseEngine, EngineResult, ThreatMatch

    class MyCustomEngine(BaseEngine):
        def __init__(self):
            super().__init__("my_custom", weight=0.8)

        def analyze(self, text: str) -> EngineResult:
            # Custom detection logic
            return EngineResult(engine_name=self.name)
"""

import sys
import importlib
import importlib.util
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("shield.plugins")


def discover_plugins(
    directory: str,
) -> list[dict]:
    """
    Discover plugin files in directory.

    Returns list of dicts with name, path, module.
    Does not instantiate engines yet.
    """
    plugin_dir = Path(directory)
    if not plugin_dir.exists():
        logger.info(f"Plugin dir not found: {plugin_dir}")
        return []

    plugins = []
    for f in sorted(plugin_dir.glob("*.py")):
        if f.name.startswith("_"):
            continue
        plugins.append(
            {
                "name": f.stem,
                "path": str(f),
                "loaded": False,
                "error": None,
            }
        )

    logger.info(f"Discovered {len(plugins)} plugin(s) " f"in {plugin_dir}")
    return plugins


def load_plugin(plugin_path: str) -> Optional[object]:
    """
    Load a single plugin and return engine instance.

    Looks for a class ending with 'Engine' that
    extends BaseEngine.
    """
    from engines.base import BaseEngine

    path = Path(plugin_path)
    if not path.exists():
        logger.error(f"Plugin not found: {path}")
        return None

    module_name = f"shield_plugin_{path.stem}"

    try:
        spec = importlib.util.spec_from_file_location(module_name, str(path))
        if spec is None or spec.loader is None:
            logger.error(f"Cannot create spec for {path}")
            return None

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        # Find engine class
        for attr_name in dir(module):
            if not attr_name.endswith("Engine"):
                continue
            cls = getattr(module, attr_name)
            if (
                isinstance(cls, type)
                and issubclass(cls, BaseEngine)
                and cls is not BaseEngine
            ):
                engine = cls()
                logger.info(
                    f"Loaded plugin engine: "
                    f"{engine.name} "
                    f"(weight={engine.weight}) "
                    f"from {path.name}"
                )
                return engine

        logger.warning(f"No BaseEngine subclass found " f"in {path.name}")
        return None

    except Exception as e:
        logger.error(f"Plugin load error ({path.name}): {e}")
        return None


def load_all_plugins(
    directory: str,
) -> list[object]:
    """
    Load all plugins from directory.

    Returns list of engine instances.
    """
    plugins = discover_plugins(directory)
    engines = []

    for p in plugins:
        engine = load_plugin(p["path"])
        if engine:
            engines.append(engine)

    logger.info(f"Loaded {len(engines)}/{len(plugins)} " f"plugin engines")
    return engines
