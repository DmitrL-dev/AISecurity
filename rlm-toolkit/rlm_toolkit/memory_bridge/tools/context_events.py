"""Anti-Amnesia context change tracking (v2.5).

Persistent SQLite-backed event log for cross-process
context change detection.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from ...storage.connection import safe_connection


class ContextEventTracker:
    """Track context changes via SQLite for Anti-Amnesia."""

    def __init__(
        self,
        db_path: Path,
        on_context_change: Optional[callable] = None,
    ):
        self.db_path = Path(db_path)
        self.on_context_change = on_context_change
        self._init_db()

    def _init_db(self):
        with safe_connection(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS context_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version INTEGER NOT NULL,
                    reason TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS context_state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """
            )
            conn.execute(
                """
                INSERT OR IGNORE INTO context_state
                (key, value) VALUES ('version', '0')
            """
            )
            conn.execute(
                """
                INSERT OR IGNORE INTO context_state
                (key, value) VALUES ('changed', 'false')
            """
            )

    def notify(self, reason: str):
        """Persist context change event."""
        try:
            with safe_connection(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT value FROM context_state " "WHERE key = 'version'"
                )
                row = cursor.fetchone()
                version = int(row[0]) + 1 if row else 1

                conn.execute(
                    "UPDATE context_state " "SET value = ? WHERE key = 'version'",
                    (str(version),),
                )
                conn.execute(
                    "UPDATE context_state "
                    "SET value = 'true' "
                    "WHERE key = 'changed'"
                )
                conn.execute(
                    "INSERT INTO context_events "
                    "(version, reason, timestamp) "
                    "VALUES (?, ?, ?)",
                    (
                        version,
                        reason,
                        datetime.now().isoformat(),
                    ),
                )
        except Exception:
            pass  # Don't break tools on notification failure

        if self.on_context_change:
            try:
                self.on_context_change(reason)
            except Exception:
                pass
