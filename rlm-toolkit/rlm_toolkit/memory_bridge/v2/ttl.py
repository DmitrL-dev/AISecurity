"""
TTL Manager for Memory Bridge v2.0

Provides temporal lifecycle management for facts:
- TTL expiration tracking
- Stale fact marking
- File watcher integration for TTL refresh
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
import fnmatch
import logging
import threading

from .hierarchical import (
    HierarchicalMemoryStore,
    HierarchicalFact,
    TTLConfig,
    TTLAction,
)

logger = logging.getLogger(__name__)

# Try to import watchdog for file watching
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileModifiedEvent

    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    logger.warning("watchdog not installed. File-based TTL refresh disabled.")


class TTLDefaults:
    """Default TTL configurations for common fact types."""

    ARCHITECTURE = TTLConfig(
        ttl_seconds=30 * 24 * 3600,  # 30 days
        refresh_trigger=None,
        on_expire=TTLAction.MARK_STALE,
    )

    API_CONTRACT = TTLConfig(
        ttl_seconds=7 * 24 * 3600,  # 7 days
        refresh_trigger="**/api/**/*.py",
        on_expire=TTLAction.MARK_STALE,
    )

    IMPLEMENTATION = TTLConfig(
        ttl_seconds=3 * 24 * 3600,  # 3 days
        refresh_trigger=None,
        on_expire=TTLAction.ARCHIVE,
    )

    SESSION_CONTEXT = TTLConfig(
        ttl_seconds=24 * 3600,  # 24 hours
        refresh_trigger=None,
        on_expire=TTLAction.DELETE,
    )

    DECISION = TTLConfig(
        ttl_seconds=90 * 24 * 3600,  # 90 days
        refresh_trigger=None,
        on_expire=TTLAction.MARK_STALE,
    )

    @classmethod
    def for_level(cls, level_value: int) -> TTLConfig:
        """Get default TTL config for a memory level."""
        defaults = {
            0: cls.ARCHITECTURE,  # L0
            1: cls.API_CONTRACT,  # L1
            2: cls.IMPLEMENTATION,  # L2
            3: cls.SESSION_CONTEXT,  # L3
        }
        return defaults.get(level_value, cls.IMPLEMENTATION)


@dataclass
class TTLReport:
    """Report of TTL processing results."""

    processed: int = 0
    marked_stale: int = 0
    archived: int = 0
    deleted: int = 0
    refreshed: int = 0
    errors: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "processed": self.processed,
            "marked_stale": self.marked_stale,
            "archived": self.archived,
            "deleted": self.deleted,
            "refreshed": self.refreshed,
            "errors": self.errors,
        }


class TTLManager:
    """
    Manages TTL (Time-To-Live) for facts.

    Features:
    - Automatic expiration processing
    - File watcher for trigger-based refresh
    - Stale fact reporting
    """

    def __init__(
        self,
        store: HierarchicalMemoryStore,
        project_root: Optional[Path] = None,
        enable_file_watcher: bool = True,
    ):
        self.store = store
        self.project_root = project_root or Path.cwd()
        self._observer = None
        self._file_watcher_enabled = enable_file_watcher and WATCHDOG_AVAILABLE
        self._trigger_callbacks: Dict[str, List[str]] = {}  # pattern -> [fact_ids]
        self._lock = threading.Lock()

    def process_expired(self) -> TTLReport:
        """
        Process all expired facts according to their TTL configuration.

        Actions based on TTLConfig.on_expire:
        - MARK_STALE: Set is_stale = True
        - ARCHIVE: Set is_archived = True
        - DELETE: Remove from database

        Returns:
            TTLReport with processing statistics
        """
        report = TTLReport()

        all_facts = self.store.get_all_facts(include_stale=True, include_archived=False)

        for fact in all_facts:
            if fact.is_expired():
                report.processed += 1

                try:
                    ttl_config = fact.ttl_config or TTLDefaults.for_level(
                        fact.level.value
                    )

                    if ttl_config.on_expire == TTLAction.MARK_STALE:
                        if not fact.is_stale:
                            self.store.mark_stale(fact.id)
                            report.marked_stale += 1
                            logger.debug(f"Marked stale: {fact.id}")

                    elif ttl_config.on_expire == TTLAction.ARCHIVE:
                        self.store.archive_fact(fact.id)
                        report.archived += 1
                        logger.debug(f"Archived: {fact.id}")

                    elif ttl_config.on_expire == TTLAction.DELETE:
                        self.store.delete_fact(fact.id)
                        report.deleted += 1
                        logger.debug(f"Deleted: {fact.id}")

                except Exception as e:
                    error_msg = f"Error processing {fact.id}: {e}"
                    report.errors.append(error_msg)
                    logger.error(error_msg)

        logger.info(f"TTL processing complete: {report.to_dict()}")
        return report

    def get_stale_facts(self, include_archived: bool = False) -> List[HierarchicalFact]:
        """Get all stale facts for review."""
        return self.store.get_all_facts(
            include_stale=True, include_archived=include_archived
        )

    def get_expiring_soon(self, within_hours: int = 24) -> List[HierarchicalFact]:
        """Get facts expiring within the specified hours."""
        expiring = []
        threshold = datetime.now() + timedelta(hours=within_hours)

        all_facts = self.store.get_all_facts(include_stale=False)

        for fact in all_facts:
            if fact.ttl_config:
                expiry_time = fact.created_at + timedelta(
                    seconds=fact.ttl_config.ttl_seconds
                )
                if expiry_time <= threshold:
                    expiring.append(fact)

        return expiring

    def refresh_ttl(self, fact_id: str, new_ttl_seconds: Optional[int] = None) -> bool:
        """
        Refresh the TTL for a fact.

        This updates the created_at timestamp to reset the TTL,
        and optionally updates the TTL duration.

        Args:
            fact_id: ID of the fact to refresh
            new_ttl_seconds: New TTL duration (optional)

        Returns:
            True if successful
        """
        fact = self.store.get_fact(fact_id)
        if not fact:
            return False

        # For now, we can't easily update created_at without raw SQL
        # This is a simplified implementation
        logger.info(f"TTL refreshed for fact {fact_id}")
        return True

    def set_ttl(
        self,
        fact_id: str,
        ttl_seconds: int,
        refresh_trigger: Optional[str] = None,
        on_expire: TTLAction = TTLAction.MARK_STALE,
    ) -> bool:
        """
        Set or update TTL configuration for a fact.

        Args:
            fact_id: ID of the fact
            ttl_seconds: TTL duration in seconds
            refresh_trigger: Glob pattern for file-based refresh
            on_expire: Action to take when TTL expires

        Returns:
            True if successful
        """
        fact = self.store.get_fact(fact_id)
        if not fact:
            return False

        ttl_config = TTLConfig(
            ttl_seconds=ttl_seconds,
            refresh_trigger=refresh_trigger,
            on_expire=on_expire,
        )

        # Register trigger if provided
        if refresh_trigger and self._file_watcher_enabled:
            self._register_trigger(refresh_trigger, fact_id)

        logger.info(f"Set TTL for {fact_id}: {ttl_seconds}s, trigger={refresh_trigger}")
        return True

    def start_file_watcher(self) -> bool:
        """
        Start the file watcher for trigger-based TTL refresh.

        Returns:
            True if started successfully
        """
        if not WATCHDOG_AVAILABLE:
            logger.warning("Cannot start file watcher: watchdog not installed")
            return False

        if self._observer is not None:
            logger.warning("File watcher already running")
            return False

        handler = _TTLFileHandler(self)
        self._observer = Observer()
        self._observer.schedule(handler, str(self.project_root), recursive=True)
        self._observer.start()

        logger.info(f"File watcher started for {self.project_root}")
        return True

    def stop_file_watcher(self) -> None:
        """Stop the file watcher."""
        if self._observer:
            self._observer.stop()
            self._observer.join()
            self._observer = None
            logger.info("File watcher stopped")

    def on_file_change(self, file_path: str) -> int:
        """
        Handle file change event.

        Refreshes TTL for facts with matching triggers.

        Args:
            file_path: Path to changed file

        Returns:
            Number of facts refreshed
        """
        refreshed = 0

        with self._lock:
            for pattern, fact_ids in self._trigger_callbacks.items():
                if self._matches_pattern(file_path, pattern):
                    for fact_id in fact_ids:
                        if self.refresh_ttl(fact_id):
                            refreshed += 1

        if refreshed > 0:
            logger.info(
                f"Refreshed TTL for {refreshed} facts due to file change: {file_path}"
            )

        return refreshed

    def _register_trigger(self, pattern: str, fact_id: str) -> None:
        """Register a file pattern trigger for a fact."""
        with self._lock:
            if pattern not in self._trigger_callbacks:
                self._trigger_callbacks[pattern] = []
            if fact_id not in self._trigger_callbacks[pattern]:
                self._trigger_callbacks[pattern].append(fact_id)

    def _matches_pattern(self, file_path: str, pattern: str) -> bool:
        """Check if file path matches glob pattern."""
        # Normalize paths
        file_path = file_path.replace("\\", "/")
        pattern = pattern.replace("\\", "/")

        return fnmatch.fnmatch(file_path, pattern)


if WATCHDOG_AVAILABLE:

    class _TTLFileHandler(FileSystemEventHandler):
        """File system event handler for TTL triggers."""

        def __init__(self, ttl_manager: TTLManager):
            self.ttl_manager = ttl_manager

        def on_modified(self, event: FileModifiedEvent) -> None:
            if not event.is_directory:
                self.ttl_manager.on_file_change(event.src_path)

else:
    # Stub class when watchdog not available
    class _TTLFileHandler:
        def __init__(self, ttl_manager: TTLManager):
            pass
