"""
Immutable Audit Log for Sentinel

Provides tamper-evident logging for compliance and forensics.
Uses cryptographic chaining (like blockchain) to ensure integrity.
"""

import json
import hashlib
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum

logger = logging.getLogger("AuditLog")


class AuditEventType(str, Enum):
    """Types of audit events."""
    REQUEST_RECEIVED = "request_received"
    REQUEST_ALLOWED = "request_allowed"
    REQUEST_BLOCKED = "request_blocked"
    THREAT_DETECTED = "threat_detected"
    AUTH_SUCCESS = "auth_success"
    AUTH_FAILURE = "auth_failure"
    CONFIG_CHANGE = "config_change"
    ENGINE_ERROR = "engine_error"
    ADMIN_ACTION = "admin_action"


@dataclass
class AuditEntry:
    """Single audit log entry with cryptographic chain."""
    sequence: int
    timestamp: str
    event_type: str
    actor: str  # user_id, system, etc.
    resource: str  # endpoint, engine, etc.
    action: str
    details: Dict[str, Any]
    outcome: str  # success, failure, blocked
    previous_hash: str
    hash: str = ""

    def calculate_hash(self) -> str:
        """Calculate SHA-256 hash of entry without hash field."""
        data = {
            "sequence": self.sequence,
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "actor": self.actor,
            "resource": self.resource,
            "action": self.action,
            "details": self.details,
            "outcome": self.outcome,
            "previous_hash": self.previous_hash,
        }
        content = json.dumps(data, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()


class AuditLog:
    """
    Immutable audit log with cryptographic chaining.

    Each entry contains hash of previous entry, making
    tampering detectable (like blockchain).
    """

    GENESIS_HASH = "0" * 64  # Initial hash for first entry

    def __init__(self, storage_path: Optional[str] = None):
        self._entries: List[AuditEntry] = []
        self._storage_path = storage_path
        self._sequence = 0

        if storage_path:
            self._load_from_storage()

        logger.info("Audit Log initialized")

    def log(
        self,
        event_type: AuditEventType,
        actor: str,
        resource: str,
        action: str,
        details: Dict[str, Any],
        outcome: str = "success"
    ) -> AuditEntry:
        """
        Log an audit event.

        Returns the created entry.
        """
        self._sequence += 1

        previous_hash = (
            self._entries[-1].hash if self._entries
            else self.GENESIS_HASH
        )

        entry = AuditEntry(
            sequence=self._sequence,
            timestamp=datetime.utcnow().isoformat() + "Z",
            event_type=event_type.value,
            actor=actor,
            resource=resource,
            action=action,
            details=details,
            outcome=outcome,
            previous_hash=previous_hash,
        )

        entry.hash = entry.calculate_hash()
        self._entries.append(entry)

        if self._storage_path:
            self._persist_entry(entry)

        logger.debug(f"Audit: {event_type.value} by {actor} on {resource}")

        return entry

    def verify_integrity(self) -> bool:
        """
        Verify the integrity of the audit log chain.

        Returns True if all entries are valid and chain is unbroken.
        """
        if not self._entries:
            return True

        # Check first entry
        if self._entries[0].previous_hash != self.GENESIS_HASH:
            logger.error("Audit log integrity failed: invalid genesis")
            return False

        # Check each entry
        for i, entry in enumerate(self._entries):
            # Verify hash
            if entry.hash != entry.calculate_hash():
                logger.error(
                    f"Audit log integrity failed at entry {i}: hash mismatch")
                return False

            # Verify chain
            if i > 0:
                if entry.previous_hash != self._entries[i-1].hash:
                    logger.error(
                        f"Audit log integrity failed at entry {i}: broken chain")
                    return False

        logger.info(
            f"Audit log integrity verified: {len(self._entries)} entries")
        return True

    def get_entries(
        self,
        event_type: Optional[AuditEventType] = None,
        actor: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[AuditEntry]:
        """Query audit entries with optional filters."""
        result = []

        for entry in reversed(self._entries):
            if event_type and entry.event_type != event_type.value:
                continue
            if actor and entry.actor != actor:
                continue
            if since:
                entry_time = datetime.fromisoformat(
                    entry.timestamp.rstrip("Z"))
                if entry_time < since:
                    continue

            result.append(entry)
            if len(result) >= limit:
                break

        return result

    def export(self, format: str = "json") -> str:
        """Export audit log."""
        if format == "json":
            return json.dumps(
                [asdict(e) for e in self._entries],
                indent=2
            )
        raise ValueError(f"Unknown format: {format}")

    def _persist_entry(self, entry: AuditEntry):
        """Append entry to storage file."""
        with open(self._storage_path, "a") as f:
            f.write(json.dumps(asdict(entry)) + "\n")

    def _load_from_storage(self):
        """Load entries from storage file."""
        try:
            with open(self._storage_path, "r") as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        entry = AuditEntry(**data)
                        self._entries.append(entry)
                        self._sequence = max(self._sequence, entry.sequence)

            logger.info(
                f"Loaded {len(self._entries)} audit entries from storage")
        except FileNotFoundError:
            logger.info("No existing audit log found, starting fresh")


# Singleton
_audit_log: Optional[AuditLog] = None


def get_audit_log(storage_path: Optional[str] = None) -> AuditLog:
    """Get or create singleton audit log."""
    global _audit_log
    if _audit_log is None:
        _audit_log = AuditLog(storage_path)
    return _audit_log
