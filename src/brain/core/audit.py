"""
Immutable Audit Log for Sentinel

Provides tamper-evident logging for compliance and forensics.
Features:
- Cryptographic chaining (like blockchain)
- HMAC signatures per entry
- Append-only file persistence
- Periodic integrity verification
"""

import json
import hashlib
import hmac
import logging
import os
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum, IntEnum

logger = logging.getLogger("AuditLog")


class AuditLevel(IntEnum):
    """Audit log levels (higher = more severe)."""

    DEBUG = 10
    INFO = 20
    WARNING = 30
    CRITICAL = 40


# Map string names to levels
LEVEL_MAP = {
    "DEBUG": AuditLevel.DEBUG,
    "INFO": AuditLevel.INFO,
    "WARNING": AuditLevel.WARNING,
    "CRITICAL": AuditLevel.CRITICAL,
}


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
    """Single audit log entry with cryptographic chain and HMAC signature."""

    sequence: int
    timestamp: str
    event_type: str
    level: str  # CRITICAL, WARNING, INFO, DEBUG
    actor: str  # user_id, system, etc.
    resource: str  # endpoint, engine, etc.
    action: str
    details: Dict[str, Any]
    outcome: str  # success, failure, blocked
    previous_hash: str
    hash: str = ""
    signature: str = ""  # HMAC-SHA256 signature

    def calculate_hash(self) -> str:
        """Calculate SHA-256 hash of entry without hash/signature fields."""
        data = {
            "sequence": self.sequence,
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "actor": self.actor,
            "level": self.level,
            "resource": self.resource,
            "action": self.action,
            "details": self.details,
            "outcome": self.outcome,
            "previous_hash": self.previous_hash,
        }
        content = json.dumps(data, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()

    def calculate_signature(self, secret: bytes) -> str:
        """Calculate HMAC-SHA256 signature using secret key."""
        return hmac.new(secret, self.hash.encode(), hashlib.sha256).hexdigest()

    def verify_signature(self, secret: bytes) -> bool:
        """Verify HMAC signature matches."""
        expected = self.calculate_signature(secret)
        return hmac.compare_digest(self.signature, expected)


class AuditLog:
    """
    Immutable audit log with cryptographic chaining and HMAC signatures.

    Features:
    - Each entry contains hash of previous entry (blockchain-style)
    - HMAC-SHA256 signatures using secret key
    - Append-only file persistence
    - Automatic integrity verification
    """

    GENESIS_HASH = "0" * 64  # Initial hash for first entry
    DEFAULT_STORAGE = "/var/log/sentinel/audit.log"

    def __init__(self, storage_path: Optional[str] = None):
        self._entries: List[AuditEntry] = []
        self._sequence = 0
        self._tampered = False  # Integrity flag

        # Get log level from env
        level_name = os.getenv("AUDIT_LEVEL", "INFO").upper()
        self._level = LEVEL_MAP.get(level_name, AuditLevel.INFO)

        # Secret key for HMAC signatures (CRITICAL: keep secure!)
        secret_env = os.getenv("AUDIT_SECRET_KEY", "")
        if not secret_env:
            # Generate and log warning if no key provided
            secret_env = hashlib.sha256(
                f"sentinel-audit-{os.getpid()}".encode()
            ).hexdigest()
            logger.warning(
                "AUDIT_SECRET_KEY not set! Using generated key. "
                "Set env var for production!"
            )
        self._secret = secret_env.encode()

        # Storage path (default to /var/log/sentinel/)
        self._storage_path = storage_path or os.getenv(
            "AUDIT_STORAGE_PATH", self.DEFAULT_STORAGE
        )

        # Ensure storage directory exists
        storage_dir = os.path.dirname(self._storage_path)
        if storage_dir and not os.path.exists(storage_dir):
            try:
                os.makedirs(storage_dir, mode=0o700)
            except OSError:
                logger.warning(f"Cannot create audit dir: {storage_dir}")
                self._storage_path = None

        # Load existing entries
        if self._storage_path and os.path.exists(self._storage_path):
            self._load_from_storage()

        logger.info(
            f"Audit Log initialized (level={self._level.name}, "
            f"storage={self._storage_path})"
        )

    @property
    def level(self) -> AuditLevel:
        return self._level

    @level.setter
    def level(self, value: AuditLevel):
        self._level = value

    def set_level_by_name(self, name: str) -> bool:
        """Set level by name string."""
        lvl = LEVEL_MAP.get(name.upper())
        if lvl is None:
            return False
        self._level = lvl
        return True

    def log(
        self,
        event_type: AuditEventType,
        actor: str,
        resource: str,
        action: str,
        details: Dict[str, Any],
        outcome: str = "success",
        level: AuditLevel = AuditLevel.INFO,
    ) -> Optional[AuditEntry]:
        """
        Log an audit event with level filtering.

        Returns the created entry or None if filtered.
        """
        # Skip if below current level
        if level < self._level:
            return None

        self._sequence += 1

        if self._entries:
            previous_hash = self._entries[-1].hash
        else:
            previous_hash = self.GENESIS_HASH

        entry = AuditEntry(
            sequence=self._sequence,
            timestamp=datetime.utcnow().isoformat() + "Z",
            event_type=event_type.value,
            level=level.name,
            actor=actor,
            resource=resource,
            action=action,
            details=details,
            outcome=outcome,
            previous_hash=previous_hash,
        )

        # Calculate hash and HMAC signature
        entry.hash = entry.calculate_hash()
        entry.signature = entry.calculate_signature(self._secret)

        self._entries.append(entry)

        # Append-only persistence
        if self._storage_path:
            self._persist_entry(entry)

        logger.debug(f"Audit: {level.name} {event_type.value} by {actor}")

        return entry

    def log_critical(
        self,
        event_type: AuditEventType,
        actor: str,
        resource: str,
        action: str,
        details: Dict[str, Any],
        outcome: str = "success",
    ) -> Optional[AuditEntry]:
        """Log critical event."""
        return self.log(
            event_type, actor, resource, action, details, outcome, AuditLevel.CRITICAL
        )

    def log_warning(
        self,
        event_type: AuditEventType,
        actor: str,
        resource: str,
        action: str,
        details: Dict[str, Any],
        outcome: str = "success",
    ) -> Optional[AuditEntry]:
        """Log warning event."""
        return self.log(
            event_type, actor, resource, action, details, outcome, AuditLevel.WARNING
        )

    def log_info(
        self,
        event_type: AuditEventType,
        actor: str,
        resource: str,
        action: str,
        details: Dict[str, Any],
        outcome: str = "success",
    ) -> Optional[AuditEntry]:
        """Log info event."""
        return self.log(
            event_type, actor, resource, action, details, outcome, AuditLevel.INFO
        )

    def log_debug(
        self,
        event_type: AuditEventType,
        actor: str,
        resource: str,
        action: str,
        details: Dict[str, Any],
        outcome: str = "success",
    ) -> Optional[AuditEntry]:
        """Log debug event."""
        return self.log(
            event_type, actor, resource, action, details, outcome, AuditLevel.DEBUG
        )

    def verify_integrity(self) -> bool:
        """
        Verify the integrity of the audit log chain and HMAC signatures.

        Returns True if all entries are valid, chain is unbroken,
        and all HMAC signatures are valid.
        """
        if not self._entries:
            return True

        # Check first entry
        if self._entries[0].previous_hash != self.GENESIS_HASH:
            logger.critical("TAMPER DETECTED: invalid genesis hash!")
            self._tampered = True
            return False

        # Check each entry
        for i, entry in enumerate(self._entries):
            # Verify hash
            if entry.hash != entry.calculate_hash():
                logger.critical(f"TAMPER DETECTED at entry {i}: hash mismatch!")
                self._tampered = True
                return False

            # Verify HMAC signature
            if entry.signature and not entry.verify_signature(self._secret):
                logger.critical(f"TAMPER DETECTED at entry {i}: invalid signature!")
                self._tampered = True
                return False

            # Verify chain
            if i > 0:
                if entry.previous_hash != self._entries[i - 1].hash:
                    logger.critical(f"TAMPER DETECTED at entry {i}: broken chain!")
                    self._tampered = True
                    return False

        logger.info(f"Audit log integrity verified: {len(self._entries)} entries")
        return True

    @property
    def is_tampered(self) -> bool:
        """Check if tampering was ever detected."""
        return self._tampered

    def get_entries(
        self,
        event_type: Optional[AuditEventType] = None,
        actor: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Query audit entries with optional filters. Returns dicts."""
        result = []

        for entry in reversed(self._entries):
            if event_type and entry.event_type != event_type.value:
                continue
            if actor and entry.actor != actor:
                continue
            if since:
                entry_time = datetime.fromisoformat(entry.timestamp.rstrip("Z"))
                if entry_time < since:
                    continue

            result.append(asdict(entry))
            if len(result) >= limit:
                break

        return result

    def export(self, format: str = "json") -> str:
        """Export audit log."""
        if format == "json":
            return json.dumps([asdict(e) for e in self._entries], indent=2)
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

            logger.info(f"Loaded {len(self._entries)} audit entries from storage")
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
