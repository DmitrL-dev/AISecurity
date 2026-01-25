"""
File Watcher - Auto-extract facts on file changes.

Watches project files and triggers extraction when changes occur.
Uses debouncing to avoid excessive updates.
"""

import asyncio
from pathlib import Path
from time import time
from typing import Callable, Optional, Set

try:
    from watchfiles import awatch, Change

    WATCHFILES_AVAILABLE = True
except ImportError:
    WATCHFILES_AVAILABLE = False
    awatch = None
    Change = None


class FileWatcher:
    """Watch files for changes and trigger extraction."""

    def __init__(
        self,
        project_root: Path,
        on_change: Callable[[Path], None],
        patterns: list[str] = None,
        debounce_ms: int = 1000,
    ):
        self.project_root = Path(project_root)
        self.on_change = on_change
        self.patterns = patterns or [
            "**/*.md",
            "**/*.py",
            "**/*.ts",
            "**/*.json",
        ]
        self.debounce_ms = debounce_ms

        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._last_change: dict[Path, float] = {}
        self._pending: Set[Path] = set()

    @property
    def is_running(self) -> bool:
        return self._running

    async def start(self) -> bool:
        """Start watching for file changes."""
        if not WATCHFILES_AVAILABLE:
            return False

        if self._running:
            return True

        self._running = True
        self._task = asyncio.create_task(self._watch_loop())
        return True

    async def stop(self) -> None:
        """Stop watching."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _watch_loop(self) -> None:
        """Main watch loop."""
        if not awatch:
            return

        try:
            async for changes in awatch(
                self.project_root,
                recursive=True,
                step=100,  # Check every 100ms
            ):
                if not self._running:
                    break

                for change_type, path_str in changes:
                    path = Path(path_str)

                    # Filter by patterns
                    if not self._matches_pattern(path):
                        continue

                    # Skip common non-relevant changes
                    if self._should_skip(path):
                        continue

                    # Debounce
                    now = time()
                    last = self._last_change.get(path, 0)
                    if (now - last) * 1000 < self.debounce_ms:
                        self._pending.add(path)
                        continue

                    self._last_change[path] = now

                    # Trigger callback
                    try:
                        self.on_change(path)
                    except Exception:
                        pass  # Don't crash watcher on callback error

                # Process pending (debounced) changes
                await self._process_pending()

        except asyncio.CancelledError:
            pass

    async def _process_pending(self) -> None:
        """Process pending debounced changes."""
        if not self._pending:
            return

        now = time()
        processed = set()

        for path in self._pending:
            last = self._last_change.get(path, 0)
            if (now - last) * 1000 >= self.debounce_ms:
                self._last_change[path] = now
                try:
                    self.on_change(path)
                except Exception:
                    pass
                processed.add(path)

        self._pending -= processed

    def _matches_pattern(self, path: Path) -> bool:
        """Check if path matches any pattern."""
        import fnmatch

        rel_path = str(path.relative_to(self.project_root))

        for pattern in self.patterns:
            if fnmatch.fnmatch(rel_path, pattern):
                return True

        return False

    def _should_skip(self, path: Path) -> bool:
        """Check if path should be skipped."""
        skip_parts = {
            ".git",
            "__pycache__",
            "node_modules",
            ".venv",
            "venv",
            "dist",
            "build",
            ".pytest_cache",
            ".mypy_cache",
        }

        return any(part in path.parts for part in skip_parts)


# MCP tool wrapper functions
_active_watcher: Optional[FileWatcher] = None


async def start_watcher(
    project_root: Path,
    on_change: Callable[[Path], None],
    patterns: list[str] = None,
    debounce_ms: int = 1000,
) -> dict:
    """Start file watcher."""
    global _active_watcher

    if not WATCHFILES_AVAILABLE:
        return {
            "status": "error",
            "message": "watchfiles not installed. " "Run: pip install watchfiles",
        }

    if _active_watcher and _active_watcher.is_running:
        return {
            "status": "error",
            "message": "Watcher already running. Stop it first.",
        }

    _active_watcher = FileWatcher(
        project_root=project_root,
        on_change=on_change,
        patterns=patterns,
        debounce_ms=debounce_ms,
    )

    success = await _active_watcher.start()

    return {
        "status": "success" if success else "error",
        "message": "Watcher started" if success else "Failed to start",
        "patterns": _active_watcher.patterns,
        "debounce_ms": debounce_ms,
    }


async def stop_watcher() -> dict:
    """Stop file watcher."""
    global _active_watcher

    if not _active_watcher or not _active_watcher.is_running:
        return {
            "status": "success",
            "message": "No watcher running",
        }

    await _active_watcher.stop()
    _active_watcher = None

    return {
        "status": "success",
        "message": "Watcher stopped",
    }


def get_watcher_status() -> dict:
    """Get watcher status."""
    if not _active_watcher:
        return {
            "status": "stopped",
            "watchfiles_available": WATCHFILES_AVAILABLE,
        }

    return {
        "status": "running" if _active_watcher.is_running else "stopped",
        "patterns": _active_watcher.patterns,
        "debounce_ms": _active_watcher.debounce_ms,
        "watchfiles_available": WATCHFILES_AVAILABLE,
    }
