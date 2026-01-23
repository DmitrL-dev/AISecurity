# Memory Bridge — Storage Layer
"""
SQLite-based storage with blob-level AES-256-GCM encryption.
Implements NFR-02 Security requirements from SDD.
"""

from __future__ import annotations

import hashlib
import os
import secrets
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from .models import CognitiveStateVector


class AuditAction(Enum):
    """Audit log action types."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    RESTORE = "restore"


@dataclass
class StateRecord:
    """A stored state record with metadata."""
    session_id: str
    version: int
    timestamp: datetime
    checksum: str
    data: bytes  # encrypted


@dataclass
class AuditLogEntry:
    """An audit log entry for tracking state changes."""
    id: int
    session_id: str
    action: AuditAction
    version: Optional[int]
    timestamp: datetime
    details: Optional[str]


class StateStorage:
    """SQLite-based storage for cognitive state with AES-256-GCM encryption."""

    DEFAULT_DB_PATH = Path.home() / ".rlm" / "memory_bridge.db"
    DEFAULT_TTL_DAYS = 90

    def __init__(
        self,
        db_path: Optional[Path] = None,
        encryption_key: Optional[str] = None,
        ttl_days: int = DEFAULT_TTL_DAYS,
    ):
        """
        Initialize storage.

        Args:
            db_path: Path to SQLite database (default: ~/.rlm/memory_bridge.db)
            encryption_key: AES key from RLM_ENCRYPTION_KEY env var
            ttl_days: Days to keep old versions
        """
        self.db_path = db_path or self.DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.ttl_days = ttl_days

        # Get encryption key from env if not provided
        self._encryption_key = encryption_key or os.environ.get(
            "RLM_ENCRYPTION_KEY")

        # Encryption backends (prefer AES-256-GCM, fallback to Fernet)
        self._aesgcm = None
        self._fernet = None
        self._use_gcm = False

        if self._encryption_key:
            self._init_encryption()

        # Initialize database
        self._init_db()

    def _init_encryption(self) -> None:
        """Initialize AES-256-GCM encryption (preferred) or Fernet fallback."""
        try:
            # Try AES-256-GCM first (NFR-02 requirement)
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            # Derive 256-bit key from password
            key_bytes = hashlib.sha256(self._encryption_key.encode()).digest()
            self._aesgcm = AESGCM(key_bytes)
            self._use_gcm = True
        except ImportError:
            # Fallback to Fernet (AES-128-CBC)
            try:
                from cryptography.fernet import Fernet
                key_bytes = hashlib.sha256(
                    self._encryption_key.encode()).digest()
                import base64
                fernet_key = base64.urlsafe_b64encode(key_bytes)
                self._fernet = Fernet(fernet_key)
                self._use_gcm = False
            except ImportError:
                # No encryption available
                pass

    def _init_db(self) -> None:
        """Create database tables if not exist."""
        with sqlite3.connect(self.db_path) as conn:
            # States table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS states (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    timestamp TEXT NOT NULL,
                    checksum TEXT NOT NULL,
                    data BLOB NOT NULL,
                    nonce BLOB,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(session_id, version)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_session_id ON states(session_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp ON states(timestamp)
            """)

            # Audit log table (AC-04.4, NFR-02)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    version INTEGER,
                    timestamp TEXT NOT NULL,
                    details TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_session ON audit_log(session_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp)
            """)
            conn.commit()

    def _encrypt(self, data: bytes) -> Tuple[bytes, Optional[bytes]]:
        """
        Encrypt data using AES-256-GCM (preferred) or Fernet fallback.

        Returns:
            Tuple of (encrypted_data, nonce). Nonce is None for Fernet.
        """
        if self._use_gcm and self._aesgcm:
            # AES-256-GCM with 96-bit nonce
            nonce = secrets.token_bytes(12)  # 96-bit nonce for GCM
            encrypted = self._aesgcm.encrypt(nonce, data, None)
            return encrypted, nonce
        elif self._fernet:
            # Fernet fallback (nonce embedded in ciphertext)
            return self._fernet.encrypt(data), None
        return data, None

    def _decrypt(self, data: bytes, nonce: Optional[bytes] = None) -> bytes:
        """
        Decrypt data using AES-256-GCM or Fernet fallback.

        Args:
            data: Encrypted data
            nonce: Nonce for GCM mode (None for Fernet)
        """
        if self._use_gcm and self._aesgcm and nonce:
            return self._aesgcm.decrypt(nonce, data, None)
        elif self._fernet:
            return self._fernet.decrypt(data)
        return data

    def _compute_checksum(self, data: bytes) -> str:
        """Compute SHA-256 checksum."""
        return hashlib.sha256(data).hexdigest()

    def _log_audit(
        self,
        conn: sqlite3.Connection,
        session_id: str,
        action: AuditAction,
        version: Optional[int] = None,
        details: Optional[str] = None,
    ) -> None:
        """Log an action to the audit table (AC-04.4)."""
        conn.execute(
            """
            INSERT INTO audit_log (session_id, action, version, timestamp, details)
            VALUES (?, ?, ?, ?, ?)
            """,
            (session_id, action.value, version,
             datetime.now().isoformat(), details),
        )

    def save_state(self, state: CognitiveStateVector) -> int:
        """
        Save state to storage with audit logging.

        Returns:
            New version number.
        """
        json_data = state.to_json().encode("utf-8")
        checksum = self._compute_checksum(json_data)
        encrypted_data, nonce = self._encrypt(json_data)

        with sqlite3.connect(self.db_path) as conn:
            # Determine if this is create or update
            cursor = conn.execute(
                "SELECT COUNT(*) FROM states WHERE session_id = ?",
                (state.session_id,),
            )
            is_new = cursor.fetchone()[0] == 0
            action = AuditAction.CREATE if is_new else AuditAction.UPDATE

            # Insert state
            conn.execute(
                """
                INSERT INTO states (session_id, version, timestamp, checksum, data, nonce)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    state.session_id,
                    state.version,
                    state.timestamp.isoformat(),
                    checksum,
                    encrypted_data,
                    nonce,
                ),
            )

            # Audit log (AC-04.4)
            self._log_audit(
                conn,
                state.session_id,
                action,
                state.version,
                f"Saved state with {len(state.facts)} facts"
            )

            conn.commit()
            return state.version

    def load_state(
        self,
        session_id: str,
        version: Optional[int] = None,
        log_restore: bool = False,
    ) -> Optional[CognitiveStateVector]:
        """
        Load state from storage.

        Args:
            session_id: Session to load
            version: Specific version (default: latest)
            log_restore: Log a RESTORE action to audit log

        Returns:
            State or None if not found.
        """
        with sqlite3.connect(self.db_path) as conn:
            if version is not None:
                cursor = conn.execute(
                    "SELECT data, checksum, nonce FROM states WHERE session_id = ? AND version = ?",
                    (session_id, version),
                )
            else:
                cursor = conn.execute(
                    "SELECT data, checksum, nonce FROM states WHERE session_id = ? ORDER BY version DESC LIMIT 1",
                    (session_id,),
                )

            row = cursor.fetchone()
            if not row:
                return None

            encrypted_data, stored_checksum, nonce = row
            decrypted_data = self._decrypt(encrypted_data, nonce)

            # Verify checksum
            computed_checksum = self._compute_checksum(decrypted_data)
            if computed_checksum != stored_checksum:
                raise ValueError(f"Checksum mismatch for session {session_id}")

            state = CognitiveStateVector.from_json(
                decrypted_data.decode("utf-8"))

            # Audit log restore action if requested
            if log_restore:
                self._log_audit(
                    conn,
                    session_id,
                    AuditAction.RESTORE,
                    state.version,
                    "Restored state from storage"
                )
                conn.commit()

            return state

    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all sessions with metadata."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT session_id, MAX(version) as latest_version, MAX(timestamp) as last_updated
                FROM states
                GROUP BY session_id
                ORDER BY last_updated DESC
                """
            )
            return [
                {
                    "session_id": row[0],
                    "latest_version": row[1],
                    "last_updated": row[2],
                }
                for row in cursor.fetchall()
            ]

    def get_versions(self, session_id: str) -> List[int]:
        """Get all versions for a session."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT version FROM states WHERE session_id = ? ORDER BY version DESC",
                (session_id,),
            )
            return [row[0] for row in cursor.fetchall()]

    def cleanup_expired(self, keep_latest: int = 3) -> int:
        """
        Cleanup old versions beyond TTL.

        Args:
            keep_latest: Always keep N latest versions per session

        Returns:
            Number of records deleted.
        """
        cutoff = (datetime.now() - timedelta(days=self.ttl_days)).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            # Delete old versions, keeping latest N per session
            cursor = conn.execute(
                """
                DELETE FROM states
                WHERE id NOT IN (
                    SELECT id FROM (
                        SELECT id, ROW_NUMBER() OVER (
                            PARTITION BY session_id ORDER BY version DESC
                        ) as rn
                        FROM states
                    ) WHERE rn <= ?
                )
                AND timestamp < ?
                """,
                (keep_latest, cutoff),
            )
            deleted = cursor.rowcount
            conn.commit()
            return deleted

    def delete_session(self, session_id: str) -> int:
        """
        Delete a session and all its versions (AC-06.4).

        Args:
            session_id: Session ID to delete

        Returns:
            Number of records deleted.
        """
        with sqlite3.connect(self.db_path) as conn:
            # Get count before deleting
            cursor = conn.execute(
                "SELECT COUNT(*) FROM states WHERE session_id = ?",
                (session_id,),
            )
            count = cursor.fetchone()[0]

            if count > 0:
                # Delete all versions
                conn.execute(
                    "DELETE FROM states WHERE session_id = ?",
                    (session_id,),
                )

                # Audit log (AC-04.4)
                self._log_audit(
                    conn,
                    session_id,
                    AuditAction.DELETE,
                    None,
                    f"Deleted session with {count} versions"
                )

                conn.commit()

            return count

    def get_audit_log(
        self,
        session_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get audit log entries.

        Args:
            session_id: Filter by session ID (None for all)
            limit: Maximum entries to return

        Returns:
            List of audit log entries.
        """
        with sqlite3.connect(self.db_path) as conn:
            if session_id:
                cursor = conn.execute(
                    """
                    SELECT id, session_id, action, version, timestamp, details
                    FROM audit_log
                    WHERE session_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                    """,
                    (session_id, limit),
                )
            else:
                cursor = conn.execute(
                    """
                    SELECT id, session_id, action, version, timestamp, details
                    FROM audit_log
                    ORDER BY timestamp DESC
                    LIMIT ?
                    """,
                    (limit,),
                )

            return [
                {
                    "id": row[0],
                    "session_id": row[1],
                    "action": row[2],
                    "version": row[3],
                    "timestamp": row[4],
                    "details": row[5],
                }
                for row in cursor.fetchall()
            ]
