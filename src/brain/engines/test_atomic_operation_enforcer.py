"""
Unit tests for Atomic Operation Enforcer.
"""

import pytest
import threading
import time
from engines.atomic_operation_enforcer import (
    AtomicOperationEnforcer,
    LockManager,
    StateValidator,
    ViolationType,
)


class TestLockManager:
    """Tests for lock management."""

    def test_acquire_and_release(self):
        """Lock can be acquired and released."""
        manager = LockManager()

        acquired = manager.acquire("resource1", "owner1")
        released = manager.release("resource1", "owner1")

        assert acquired is True
        assert released is True

    def test_wrong_owner_cannot_release(self):
        """Wrong owner cannot release lock."""
        manager = LockManager()

        manager.acquire("resource1", "owner1")
        released = manager.release("resource1", "owner2")

        assert released is False

    def test_is_locked(self):
        """is_locked returns correct status."""
        manager = LockManager()

        assert manager.is_locked("resource1") is False
        manager.acquire("resource1", "owner1")
        assert manager.is_locked("resource1") is True


class TestStateValidator:
    """Tests for state validation."""

    def test_version_increments(self):
        """Version increments on set."""
        validator = StateValidator()

        v1 = validator.set_state("key1", "value1")
        v2 = validator.set_state("key1", "value2")

        assert v2 == v1 + 1

    def test_validate_version(self):
        """Version validation works."""
        validator = StateValidator()

        v1 = validator.set_state("key1", "value1")

        assert validator.validate_version("key1", v1) is True
        assert validator.validate_version("key1", v1 + 1) is False

    def test_get_state(self):
        """State can be retrieved."""
        validator = StateValidator()
        validator.set_state("key1", "value1")

        value = validator.get_state("key1")

        assert value == "value1"


class TestAtomicOperationEnforcer:
    """Integration tests."""

    def test_atomic_operation_success(self):
        """Atomic operation succeeds."""
        enforcer = AtomicOperationEnforcer()

        result = enforcer.execute_atomic(
            operation=lambda: 42,
            resources={"resource1"},
        )

        assert result.success is True
        assert result.result == 42

    def test_operation_failure_triggers_rollback(self):
        """Failed operation triggers rollback."""
        enforcer = AtomicOperationEnforcer()
        rollback_called = [False]

        def failing_op():
            raise ValueError("Intentional failure")

        def rollback():
            rollback_called[0] = True

        result = enforcer.execute_atomic(
            operation=failing_op,
            resources={"resource1"},
            rollback=rollback,
        )

        assert result.success is False
        assert rollback_called[0] is True

    def test_check_and_set_success(self):
        """Check-and-set succeeds with correct version."""
        enforcer = AtomicOperationEnforcer()

        # Initial state
        enforcer.state_validator.set_state("key1", "old")

        # Check-and-set with version 1
        result = enforcer.check_and_set("key1", 1, "new")

        assert result.success is True

    def test_check_and_set_stale_version(self):
        """Check-and-set fails with stale version."""
        enforcer = AtomicOperationEnforcer()

        # Set state twice
        enforcer.state_validator.set_state("key1", "v1")
        enforcer.state_validator.set_state("key1", "v2")

        # Try with old version
        result = enforcer.check_and_set("key1", 1, "new")

        assert result.success is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
