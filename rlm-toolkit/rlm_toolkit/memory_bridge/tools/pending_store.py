"""Pending fact candidates SQLite store.

Extracted from mcp_tools_v2.py InlinePendingStore.
Uses thread-safe connections.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from ...storage.connection import get_connection, safe_connection


class InlinePendingStore:
    """Minimal SQLite store for pending fact candidates."""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with safe_connection(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS pending_candidates (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    source TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    domain TEXT,
                    level INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL,
                    status TEXT DEFAULT 'pending'
                )
            """
            )

    def add(
        self,
        candidate_id,
        content,
        source,
        confidence,
        domain,
        level,
    ):
        with safe_connection(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO pending_candidates
                (id, content, source, confidence, domain,
                 level, created_at, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
            """,
                (
                    candidate_id,
                    content,
                    source,
                    confidence,
                    domain,
                    level,
                    datetime.now().isoformat(),
                ),
            )

    def get_pending(self, limit=50):
        with safe_connection(self.db_path, row_factory=sqlite3.Row) as conn:
            cursor = conn.execute(
                """
                SELECT * FROM pending_candidates
                WHERE status = 'pending'
                ORDER BY confidence DESC LIMIT ?
            """,
                (limit,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def approve_all(self):
        with safe_connection(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM pending_candidates
                WHERE status = 'pending'
            """
            )
            pending = [dict(row) for row in cursor.fetchall()]
            conn.execute(
                """
                UPDATE pending_candidates
                SET status = 'approved'
                WHERE status = 'pending'
            """
            )
            return pending

    def get_stats(self):
        with safe_connection(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT status, COUNT(*)
                FROM pending_candidates GROUP BY status
            """
            )
            stats = {row[0]: row[1] for row in cursor.fetchall()}
            return {
                "pending": stats.get("pending", 0),
                "approved": stats.get("approved", 0),
                "rejected": stats.get("rejected", 0),
            }
