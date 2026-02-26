"""
Hot Reload Configuration for Sentinel

Enables runtime configuration updates without restart.
Uses file watching and in-memory caching.
"""

import os
import json
import logging
import threading
from typing import Any, Callable, Dict, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger("HotReload")


@dataclass
class ConfigState:
    """Current configuration state."""
    data: Dict[str, Any]
    loaded_at: datetime
    source: str


class HotReloadConfig:
    """
    Configuration manager with hot reload support.

    Usage:
        config = HotReloadConfig("/path/to/config.json")
        config.start_watching()

        value = config.get("key", default="value")

        # Register callback for changes
        config.on_change("key", lambda new_val: print(f"Changed: {new_val}"))
    """

    def __init__(self, config_path: Optional[str] = None, poll_interval: int = 5):
        self._config_path = config_path
        self._poll_interval = poll_interval
        self._state: Optional[ConfigState] = None
        self._callbacks: Dict[str, list] = {}
        self._watch_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.RLock()

        if config_path:
            self.load()

    def load(self) -> bool:
        """Load configuration from file."""
        if not self._config_path:
            return False

        try:
            with open(self._config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            old_state = self._state
            self._state = ConfigState(
                data=data,
                loaded_at=datetime.now(),
                source=self._config_path
            )

            logger.info(f"Loaded config from {self._config_path}")

            # Trigger callbacks for changed values
            if old_state:
                self._trigger_callbacks(old_state.data, data)

            return True

        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return False

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        with self._lock:
            if not self._state:
                return default

            # Support nested keys with dot notation
            keys = key.split(".")
            value = self._state.data

            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default

            return value

    def set(self, key: str, value: Any) -> None:
        """Set configuration value (in memory only)."""
        with self._lock:
            if not self._state:
                self._state = ConfigState(
                    data={},
                    loaded_at=datetime.now(),
                    source="memory"
                )

            keys = key.split(".")
            target = self._state.data

            for k in keys[:-1]:
                if k not in target:
                    target[k] = {}
                target = target[k]

            old_value = target.get(keys[-1])
            target[keys[-1]] = value

            if old_value != value and key in self._callbacks:
                for callback in self._callbacks[key]:
                    callback(value)

    def on_change(self, key: str, callback: Callable[[Any], None]) -> None:
        """Register callback for configuration changes."""
        if key not in self._callbacks:
            self._callbacks[key] = []
        self._callbacks[key].append(callback)

    def start_watching(self) -> None:
        """Start background file watcher."""
        if self._watch_thread and self._watch_thread.is_alive():
            return

        self._stop_event.clear()
        self._watch_thread = threading.Thread(
            target=self._watch_loop,
            daemon=True
        )
        self._watch_thread.start()
        logger.info(
            f"Started config watcher (interval: {self._poll_interval}s)")

    def stop_watching(self) -> None:
        """Stop background file watcher."""
        self._stop_event.set()
        if self._watch_thread:
            self._watch_thread.join(timeout=self._poll_interval + 1)
        logger.info("Stopped config watcher")

    def _watch_loop(self) -> None:
        """Background loop to watch for file changes."""
        last_mtime = 0

        while not self._stop_event.is_set():
            try:
                if self._config_path and os.path.exists(self._config_path):
                    mtime = os.path.getmtime(self._config_path)
                    if mtime > last_mtime:
                        if last_mtime > 0:  # Don't reload on first check
                            logger.info("Config file changed, reloading...")
                            with self._lock:
                                self.load()
                        last_mtime = mtime
            except Exception as e:
                logger.error(f"Watch error: {e}")

            self._stop_event.wait(self._poll_interval)

    def _trigger_callbacks(self, old: dict, new: dict, prefix: str = "") -> None:
        """Trigger callbacks for changed values."""
        all_keys = set(old.keys()) | set(new.keys())

        for key in all_keys:
            full_key = f"{prefix}.{key}" if prefix else key
            old_val = old.get(key)
            new_val = new.get(key)

            if old_val != new_val:
                if full_key in self._callbacks:
                    for callback in self._callbacks[full_key]:
                        try:
                            callback(new_val)
                        except Exception as e:
                            logger.error(f"Callback error for {full_key}: {e}")

                # Recurse for nested dicts
                if isinstance(old_val, dict) and isinstance(new_val, dict):
                    self._trigger_callbacks(old_val, new_val, full_key)


# Singleton
_config: Optional[HotReloadConfig] = None


def get_hot_config(config_path: Optional[str] = None) -> HotReloadConfig:
    """Get singleton hot reload config."""
    global _config
    if _config is None:
        path = config_path or os.getenv("SENTINEL_CONFIG_PATH")
        _config = HotReloadConfig(path)
    return _config
