"""
Pending Candidates Store - Temporary storage for fact candidates awaiting approval.

Stores extracted candidates with confidence < threshold for user review.
"""

import json
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, asdict


@dataclass
class PendingCandidate:
    """A fact candidate awaiting user approval."""

    id: str
    content: str
    source: str
    confidence: float
    domain: Optional[str] = None
    level: int = 1
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    created_at: str = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()


class PendingCandidatesStore:
    """SQLite-backed store for pending fact candidates."""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize SQLite database."""
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS pending_candidates (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    source TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    domain TEXT,
                    level INTEGER DEFAULT 1,
                    file_path TEXT,
                    line_number INTEGER,
                    created_at TEXT NOT NULL,
                    status TEXT DEFAULT 'pending'
                )
            """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_pending_status
                ON pending_candidates(status)
            """
            )
            conn.commit()
        finally:
            conn.close()

    def add(self, candidate: PendingCandidate) -> str:
        """Add a pending candidate."""
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO pending_candidates
                (id, content, source, confidence, domain, level, 
                 file_path, line_number, created_at, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
            """,
                (
                    candidate.id,
                    candidate.content,
                    candidate.source,
                    candidate.confidence,
                    candidate.domain,
                    candidate.level,
                    candidate.file_path,
                    candidate.line_number,
                    candidate.created_at,
                ),
            )
            conn.commit()
            return candidate.id
        finally:
            conn.close()

    def get_pending(self, limit: int = 50) -> list[PendingCandidate]:
        """Get pending candidates for review."""
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM pending_candidates
                WHERE status = 'pending'
                ORDER BY confidence DESC, created_at DESC
                LIMIT ?
            """,
                (limit,),
            )
            rows = cursor.fetchall()
            return [
                PendingCandidate(
                    id=row["id"],
                    content=row["content"],
                    source=row["source"],
                    confidence=row["confidence"],
                    domain=row["domain"],
                    level=row["level"],
                    file_path=row["file_path"],
                    line_number=row["line_number"],
                    created_at=row["created_at"],
                )
                for row in rows
            ]
        finally:
            conn.close()

    def approve(self, candidate_id: str) -> Optional[PendingCandidate]:
        """Mark candidate as approved and return it."""
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM pending_candidates
                WHERE id = ? AND status = 'pending'
            """,
                (candidate_id,),
            )
            row = cursor.fetchone()

            if not row:
                return None

            conn.execute(
                """
                UPDATE pending_candidates
                SET status = 'approved'
                WHERE id = ?
            """,
                (candidate_id,),
            )
            conn.commit()

            return PendingCandidate(
                id=row["id"],
                content=row["content"],
                source=row["source"],
                confidence=row["confidence"],
                domain=row["domain"],
                level=row["level"],
                file_path=row["file_path"],
                line_number=row["line_number"],
                created_at=row["created_at"],
            )
        finally:
            conn.close()

    def reject(self, candidate_id: str) -> bool:
        """Mark candidate as rejected."""
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.execute(
                """
                UPDATE pending_candidates
                SET status = 'rejected'
                WHERE id = ? AND status = 'pending'
            """,
                (candidate_id,),
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def approve_all(self) -> list[PendingCandidate]:
        """Approve all pending candidates."""
        pending = self.get_pending(limit=1000)
        approved = []
        for candidate in pending:
            result = self.approve(candidate.id)
            if result:
                approved.append(result)
        return approved

    def reject_all(self) -> int:
        """Reject all pending candidates."""
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.execute(
                """
                UPDATE pending_candidates
                SET status = 'rejected'
                WHERE status = 'pending'
            """
            )
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()

    def get_stats(self) -> dict:
        """Get statistics about pending candidates."""
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.execute(
                """
                SELECT 
                    status,
                    COUNT(*) as count
                FROM pending_candidates
                GROUP BY status
            """
            )
            stats = {row[0]: row[1] for row in cursor.fetchall()}
            return {
                "pending": stats.get("pending", 0),
                "approved": stats.get("approved", 0),
                "rejected": stats.get("rejected", 0),
                "total": sum(stats.values()),
            }
        finally:
            conn.close()

    def clear_processed(self) -> int:
        """Delete approved and rejected candidates."""
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.execute(
                """
                DELETE FROM pending_candidates
                WHERE status IN ('approved', 'rejected')
            """
            )
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()
