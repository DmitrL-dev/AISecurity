# Context Events — Persistent Anti-Amnesia Tracking (v2.5)
"""
Standalone module for persistent context change tracking.
Can be imported from any Python process (including VS Code inline scripts).

Usage:
    from rlm_toolkit.context_events import notify_context_change
    notify_context_change("discover_project", project_root="/path/to/project")
"""

from pathlib import Path
import sqlite3
from datetime import datetime
from typing import Optional
import os


def get_context_events_db(project_root: Optional[Path] = None) -> Path:
    """Get path to context_events.db for a project."""
    if project_root is None:
        project_root = Path(os.getenv("RLM_PROJECT_ROOT", os.getcwd()))
    return Path(project_root) / ".rlm" / "memory" / "context_events.db"


def _init_db(db_path: Path):
    """Initialize context events database."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS context_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version INTEGER NOT NULL,
                reason TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS context_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        conn.execute("""
            INSERT OR IGNORE INTO context_state (key, value) VALUES ('version', '0')
        """)
        conn.execute("""
            INSERT OR IGNORE INTO context_state (key, value) VALUES ('changed', 'false')
        """)
        conn.commit()
    finally:
        conn.close()


def notify_context_change(
    reason: str,
    project_root: Optional[Path] = None,
) -> int:
    """
    Notify that context has changed (v2.5 Anti-Amnesia).

    Args:
        reason: Description of what changed (e.g., "discover_project")
        project_root: Project root path (defaults to RLM_PROJECT_ROOT env)

    Returns:
        New context version number
    """
    db_path = get_context_events_db(project_root)
    _init_db(db_path)

    conn = sqlite3.connect(str(db_path))
    try:
        # Increment version
        cursor = conn.execute(
            "SELECT value FROM context_state WHERE key = 'version'"
        )
        row = cursor.fetchone()
        version = int(row[0]) + 1 if row else 1

        # Update state
        conn.execute(
            "UPDATE context_state SET value = ? WHERE key = 'version'",
            (str(version),)
        )
        conn.execute(
            "UPDATE context_state SET value = 'true' WHERE key = 'changed'"
        )
        # Log event
        conn.execute(
            "INSERT INTO context_events (version, reason, timestamp) VALUES (?, ?, ?)",
            (version, reason, datetime.now().isoformat())
        )
        conn.commit()
        return version
    finally:
        conn.close()


def get_context_status(
    project_root: Optional[Path] = None,
) -> dict:
    """
    Get current context status.

    Returns:
        dict with version, changed, recent_events
    """
    db_path = get_context_events_db(project_root)

    if not db_path.exists():
        return {"version": 0, "changed": False, "recent_events": []}

    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.execute("SELECT key, value FROM context_state")
        state = dict(cursor.fetchall())

        cursor = conn.execute(
            "SELECT reason, timestamp FROM context_events ORDER BY id DESC LIMIT 5"
        )
        recent = [{"reason": r[0], "timestamp": r[1]}
                  for r in cursor.fetchall()]

        return {
            "version": int(state.get("version", 0)),
            "changed": state.get("changed", "false") == "true",
            "recent_events": recent,
        }
    finally:
        conn.close()


def mark_context_read(project_root: Optional[Path] = None):
    """Mark context as read (reset changed flag)."""
    db_path = get_context_events_db(project_root)

    if not db_path.exists():
        return

    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(
            "UPDATE context_state SET value = 'false' WHERE key = 'changed'"
        )
        conn.commit()
    finally:
        conn.close()
