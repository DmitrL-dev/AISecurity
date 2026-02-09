"""
Thread-Safe SQLite Connection Factory.

Centralizes SQLite connection management for RLM Toolkit.
All modules should use get_connection() instead of direct sqlite3.connect().

This module enables:
- Thread-safe connections via check_same_thread=False
- WAL mode for concurrent readers + single writer
- Consistent PRAGMA configuration
- Future: connection pooling for Context Ring async operations

Security note: check_same_thread=False is safe when combined with
WAL mode, as SQLite handles its own internal locking. This is required
for background processors (TTL, FileWatcher, Dream Consolidator)
that access the database from non-main threads.
"""

import sqlite3
import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, Union

logger = logging.getLogger("rlm_storage.connection")


def get_connection(
    db_path: Union[str, Path],
    row_factory: Optional[type] = None,
    wal_mode: bool = True,
) -> sqlite3.Connection:
    """
    Create a thread-safe SQLite connection.

    Args:
        db_path: Path to SQLite database or ":memory:"
        row_factory: Optional row factory (e.g. sqlite3.Row)
        wal_mode: Enable WAL mode for concurrent access (default: True)

    Returns:
        Configured sqlite3.Connection instance
    """
    conn = sqlite3.connect(
        str(db_path) if isinstance(db_path, Path) else db_path,
        check_same_thread=False,
    )

    if row_factory:
        conn.row_factory = row_factory

    # Enable WAL mode for concurrent read access
    # (required for Context Ring background pre-fetch)
    if wal_mode and str(db_path) != ":memory:":
        try:
            conn.execute("PRAGMA journal_mode=WAL")
        except sqlite3.OperationalError:
            pass  # Already in WAL or read-only

    # Optimize for typical RLM workloads
    conn.execute("PRAGMA busy_timeout=5000")  # 5s retry on lock

    return conn


@contextmanager
def safe_connection(
    db_path: Union[str, Path],
    row_factory: Optional[type] = None,
):
    """
    Context manager for thread-safe SQLite connections.

    Drop-in replacement for `with sqlite3.connect(path) as conn:`.

    Example:
        # Before:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(...)

        # After:
        from rlm_toolkit.storage.connection import safe_connection
        with safe_connection(self.db_path) as conn:
            conn.execute(...)
    """
    conn = get_connection(db_path, row_factory=row_factory)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
