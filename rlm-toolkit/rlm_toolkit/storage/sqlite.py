"""
SQLite Storage for Crystal Persistence.

Provides persistent storage for indexed crystals with freshness tracking.
"""

import json
import sqlite3
import time
import logging
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from ..freshness import FreshnessMetadata

logger = logging.getLogger("rlm_storage")


class CrystalStorage:
    """
    SQLite-based storage for crystals.

    Stores crystals in .rlm/crystals.db for instant loading.

    Example:
        >>> storage = CrystalStorage(Path("/project/.rlm"))
        >>> storage.save_crystal(crystal, freshness)
        >>> crystal = storage.load_crystal("/path/to/file.py")
    """

    SCHEMA = """
    CREATE TABLE IF NOT EXISTS crystals (
        path TEXT PRIMARY KEY,
        name TEXT,
        content BLOB,
        primitives_count INTEGER,
        token_count INTEGER,
        indexed_at REAL,
        source_mtime REAL,
        source_hash TEXT,
        last_validated REAL,
        human_confirmed INTEGER DEFAULT 0
    );
    
    CREATE TABLE IF NOT EXISTS metadata (
        key TEXT PRIMARY KEY,
        value TEXT
    );
    
    CREATE INDEX IF NOT EXISTS idx_mtime ON crystals(source_mtime);
    CREATE INDEX IF NOT EXISTS idx_indexed ON crystals(indexed_at);
    """

    def __init__(self, rlm_dir: Path):
        """
        Initialize storage.

        Args:
            rlm_dir: Path to .rlm directory
        """
        self.rlm_dir = Path(rlm_dir)
        self.rlm_dir.mkdir(parents=True, exist_ok=True)

        self.db_path = self.rlm_dir / "crystals.db"
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(self.SCHEMA)
            conn.commit()

    def _get_conn(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def save_crystal(
        self,
        crystal,
        freshness: FreshnessMetadata,
    ) -> None:
        """Save crystal to database."""
        # Serialize crystal
        content = self._serialize_crystal(crystal)

        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO crystals 
                (path, name, content, primitives_count, token_count,
                 indexed_at, source_mtime, source_hash, last_validated, human_confirmed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    crystal.path,
                    crystal.name,
                    content,
                    len(crystal.primitives),
                    getattr(crystal, "token_count", 0),
                    freshness.indexed_at,
                    freshness.source_mtime,
                    freshness.source_hash,
                    freshness.last_validated,
                    int(freshness.human_confirmed),
                ),
            )
            conn.commit()

    def load_crystal(self, path: str) -> Optional[Dict[str, Any]]:
        """Load crystal from database."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM crystals WHERE path = ?", (path,)
            ).fetchone()

            if row is None:
                return None

            return self._deserialize_row(row)

    def load_all(self) -> Iterator[Dict[str, Any]]:
        """Load all crystals."""
        with self._get_conn() as conn:
            for row in conn.execute("SELECT * FROM crystals"):
                yield self._deserialize_row(row)

    def delete_crystal(self, path: str) -> bool:
        """Delete crystal from database."""
        with self._get_conn() as conn:
            cursor = conn.execute("DELETE FROM crystals WHERE path = ?", (path,))
            conn.commit()
            return cursor.rowcount > 0

    def has_crystal(self, path: str) -> bool:
        """Check if crystal exists."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM crystals WHERE path = ?", (path,)
            ).fetchone()
            return row is not None

    def get_stale_crystals(self, ttl_hours: int = 24) -> List[str]:
        """Get paths of stale crystals."""
        threshold = time.time() - (ttl_hours * 3600)

        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT path FROM crystals WHERE indexed_at < ?", (threshold,)
            ).fetchall()
            return [row["path"] for row in rows]

    def get_modified_files(self, project_root: Path) -> List[str]:
        """Find files modified since indexing."""
        modified = []

        with self._get_conn() as conn:
            for row in conn.execute("SELECT path, source_mtime FROM crystals"):
                file_path = Path(row["path"])
                if file_path.exists():
                    if file_path.stat().st_mtime != row["source_mtime"]:
                        modified.append(row["path"])
                else:
                    modified.append(row["path"])  # Deleted

        return modified

    def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        with self._get_conn() as conn:
            stats = {}

            row = conn.execute(
                "SELECT COUNT(*) as count, SUM(token_count) as tokens FROM crystals"
            ).fetchone()

            stats["total_crystals"] = row["count"] or 0
            stats["total_tokens"] = row["tokens"] or 0

            row = conn.execute(
                "SELECT MIN(indexed_at) as oldest, MAX(indexed_at) as newest FROM crystals"
            ).fetchone()

            if row["oldest"]:
                stats["oldest_hours"] = (time.time() - row["oldest"]) / 3600
                stats["newest_hours"] = (time.time() - row["newest"]) / 3600

            stats["db_size_mb"] = self.db_path.stat().st_size / (1024 * 1024)

            return stats

    def set_metadata(self, key: str, value: Any) -> None:
        """Set metadata value."""
        with self._get_conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
                (key, json.dumps(value)),
            )
            conn.commit()

    def get_metadata(self, key: str) -> Optional[Any]:
        """Get metadata value."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT value FROM metadata WHERE key = ?", (key,)
            ).fetchone()

            if row:
                return json.loads(row["value"])
            return None

    def mark_validated(self, path: str) -> None:
        """Mark crystal as validated now."""
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE crystals SET last_validated = ? WHERE path = ?",
                (time.time(), path),
            )
            conn.commit()

    def confirm_current(self, path: str) -> None:
        """Human confirmed crystal as current."""
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE crystals SET human_confirmed = 1, last_validated = ? WHERE path = ?",
                (time.time(), path),
            )
            conn.commit()

    def clear(self) -> int:
        """Clear all crystals."""
        with self._get_conn() as conn:
            cursor = conn.execute("DELETE FROM crystals")
            conn.commit()
            return cursor.rowcount

    def _serialize_crystal(self, crystal) -> bytes:
        """Serialize crystal to bytes."""
        data = {
            "path": crystal.path,
            "name": crystal.name,
            "token_count": getattr(crystal, "token_count", 0),
            "content_hash": getattr(crystal, "content_hash", ""),
            "primitives": [
                {
                    "ptype": p.ptype,
                    "name": p.name,
                    "value": p.value,
                    "source_line": p.source_line,
                    "confidence": p.confidence,
                }
                for p in crystal.primitives
            ],
        }
        return json.dumps(data).encode("utf-8")

    def _deserialize_row(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Deserialize database row."""
        content = json.loads(row["content"])

        return {
            "crystal": content,
            "freshness": FreshnessMetadata(
                indexed_at=row["indexed_at"],
                source_mtime=row["source_mtime"],
                source_hash=row["source_hash"],
                last_validated=row["last_validated"],
                human_confirmed=bool(row["human_confirmed"]),
            ),
        }


def get_storage(project_root) -> CrystalStorage:
    """Get storage for a project."""
    project_root = Path(project_root)
    rlm_dir = project_root / ".rlm"
    return CrystalStorage(rlm_dir)
