"""
Atomic Operation Enforcer Engine - TOCTOU Defense

Defends against Time-of-Check to Time-of-Use attacks:
- Operation atomicity enforcement
- State consistency validation
- Race condition detection
- Transaction isolation

Addresses: OWASP ASI-04 (Race Conditions in AI)
Research: toctou_defense_deep_dive.md
Invention: Atomic Operation Enforcer (#41)
"""

import threading
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Optional, Set

from base_engine import Severity, Action  # Base classes

logger = logging.getLogger("AtomicOperationEnforcer")


# ============================================================================
# Data Classes
# ============================================================================


class ViolationType(Enum):
    """Types of atomicity violations."""

    RACE_CONDITION = "race_condition"
    STALE_STATE = "stale_state"
    CONCURRENT_MODIFICATION = "concurrent_modification"
    TIMEOUT = "timeout"


class OperationState(Enum):
    """Operation states."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class AtomicResult:
    """Result from atomic operation."""

    success: bool
    result: Any = None
    violation: Optional[ViolationType] = None
    operation_id: str = ""
    duration_ms: float = 0.0
    explanation: str = ""

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "violation": self.violation.value if self.violation else None,
            "operation_id": self.operation_id,
            "duration_ms": self.duration_ms,
            "explanation": self.explanation,
        }


# ============================================================================
# Lock Manager
# ============================================================================


class LockManager:
    """
    Manages locks for atomic operations.
    """

    def __init__(self, timeout: float = 5.0):
        self._locks: Dict[str, threading.RLock] = {}
        self._lock_owners: Dict[str, str] = {}
        self._master_lock = threading.Lock()
        self.timeout = timeout

    def acquire(self, resource: str, owner: str) -> bool:
        """Acquire lock for resource."""
        with self._master_lock:
            if resource not in self._locks:
                self._locks[resource] = threading.RLock()

        acquired = self._locks[resource].acquire(timeout=self.timeout)
        if acquired:
            self._lock_owners[resource] = owner
        return acquired

    def release(self, resource: str, owner: str) -> bool:
        """Release lock for resource."""
        if resource not in self._locks:
            return False

        if self._lock_owners.get(resource) != owner:
            return False

        try:
            self._locks[resource].release()
            self._lock_owners.pop(resource, None)
            return True
        except RuntimeError:
            return False

    def is_locked(self, resource: str) -> bool:
        """Check if resource is locked."""
        return resource in self._lock_owners


# ============================================================================
# State Validator
# ============================================================================


class StateValidator:
    """
    Validates state consistency.
    """

    def __init__(self):
        self._state_versions: Dict[str, int] = {}
        self._state_values: Dict[str, Any] = {}
        self._lock = threading.Lock()

    def get_version(self, key: str) -> int:
        """Get current version of state."""
        return self._state_versions.get(key, 0)

    def set_state(self, key: str, value: Any) -> int:
        """Set state and increment version."""
        with self._lock:
            self._state_versions[key] = self._state_versions.get(key, 0) + 1
            self._state_values[key] = value
            return self._state_versions[key]

    def validate_version(self, key: str, expected: int) -> bool:
        """Validate state version hasn't changed."""
        return self._state_versions.get(key, 0) == expected

    def get_state(self, key: str) -> Any:
        """Get current state."""
        return self._state_values.get(key)


# ============================================================================
# Transaction Manager
# ============================================================================


@dataclass
class Transaction:
    """Represents an atomic transaction."""

    tx_id: str
    resources: Set[str] = field(default_factory=set)
    state: OperationState = OperationState.PENDING
    started_at: float = 0.0
    completed_at: float = 0.0
    rollback_actions: list = field(default_factory=list)


class TransactionManager:
    """
    Manages atomic transactions.
    """

    def __init__(self, lock_manager: LockManager):
        self._transactions: Dict[str, Transaction] = {}
        self._lock_manager = lock_manager
        self._lock = threading.Lock()

    def begin(self, resources: Set[str]) -> Optional[Transaction]:
        """Begin new transaction."""
        tx_id = str(uuid.uuid4())[:8]

        # Acquire all locks
        acquired = []
        for resource in sorted(resources):
            if self._lock_manager.acquire(resource, tx_id):
                acquired.append(resource)
            else:
                # Rollback acquired locks
                for r in acquired:
                    self._lock_manager.release(r, tx_id)
                return None

        tx = Transaction(
            tx_id=tx_id,
            resources=resources,
            state=OperationState.IN_PROGRESS,
            started_at=time.time(),
        )

        with self._lock:
            self._transactions[tx_id] = tx

        return tx

    def commit(self, tx: Transaction) -> bool:
        """Commit transaction."""
        if tx.state != OperationState.IN_PROGRESS:
            return False

        tx.state = OperationState.COMPLETED
        tx.completed_at = time.time()

        # Release locks
        for resource in tx.resources:
            self._lock_manager.release(resource, tx.tx_id)

        return True

    def rollback(self, tx: Transaction) -> bool:
        """Rollback transaction."""
        if tx.state == OperationState.COMPLETED:
            return False

        # Execute rollback actions
        for action in reversed(tx.rollback_actions):
            try:
                action()
            except Exception as e:
                logger.error(f"Rollback action failed: {e}")

        tx.state = OperationState.ROLLED_BACK
        tx.completed_at = time.time()

        # Release locks
        for resource in tx.resources:
            self._lock_manager.release(resource, tx.tx_id)

        return True


# ============================================================================
# Main Engine
# ============================================================================


class AtomicOperationEnforcer:
    """
    Atomic Operation Enforcer - TOCTOU Defense

    Comprehensive atomicity enforcement:
    - Lock management
    - State validation
    - Transaction management

    Invention #41 from research.
    Addresses OWASP ASI-04.
    """

    def __init__(self, lock_timeout: float = 5.0):
        self.lock_manager = LockManager(timeout=lock_timeout)
        self.state_validator = StateValidator()
        self.tx_manager = TransactionManager(self.lock_manager)

        logger.info("AtomicOperationEnforcer initialized")

    def execute_atomic(
        self,
        operation: Callable[[], Any],
        resources: Set[str],
        rollback: Optional[Callable[[], None]] = None,
    ) -> AtomicResult:
        """
        Execute operation atomically.

        Args:
            operation: Function to execute
            resources: Resources to lock
            rollback: Rollback function if failed

        Returns:
            AtomicResult
        """
        start = time.time()

        # Begin transaction
        tx = self.tx_manager.begin(resources)
        if not tx:
            return AtomicResult(
                success=False,
                violation=ViolationType.RACE_CONDITION,
                operation_id="",
                duration_ms=(time.time() - start) * 1000,
                explanation="Could not acquire locks",
            )

        if rollback:
            tx.rollback_actions.append(rollback)

        try:
            # Execute operation
            result = operation()

            # Commit
            self.tx_manager.commit(tx)

            return AtomicResult(
                success=True,
                result=result,
                operation_id=tx.tx_id,
                duration_ms=(time.time() - start) * 1000,
                explanation="Operation completed atomically",
            )
        except Exception as e:
            # Rollback on failure
            self.tx_manager.rollback(tx)

            return AtomicResult(
                success=False,
                violation=ViolationType.CONCURRENT_MODIFICATION,
                operation_id=tx.tx_id,
                duration_ms=(time.time() - start) * 1000,
                explanation=str(e),
            )

    def check_and_set(
        self,
        key: str,
        expected_version: int,
        new_value: Any,
    ) -> AtomicResult:
        """
        Atomic check-and-set with version validation.
        """
        start = time.time()

        def operation():
            if not self.state_validator.validate_version(
                    key, expected_version):
                raise ValueError("State version mismatch")
            return self.state_validator.set_state(key, new_value)

        return self.execute_atomic(operation, {key})


# ============================================================================
# Convenience
# ============================================================================

_default_enforcer: Optional[AtomicOperationEnforcer] = None


def get_enforcer() -> AtomicOperationEnforcer:
    global _default_enforcer
    if _default_enforcer is None:
        _default_enforcer = AtomicOperationEnforcer()
    return _default_enforcer
