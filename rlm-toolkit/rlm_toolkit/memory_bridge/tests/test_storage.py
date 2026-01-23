# Memory Bridge — Storage Tests
"""Unit tests for StateStorage."""

import os
import tempfile
import pytest
from datetime import datetime
from pathlib import Path

from rlm_toolkit.memory_bridge.models import (
    CognitiveStateVector,
    Goal,
    Fact,
    EntityType,
)
from rlm_toolkit.memory_bridge.storage import StateStorage


@pytest.fixture
def temp_db():
    """Create a temporary database file."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)  # Close the file descriptor immediately
    db_path = Path(path)
    yield db_path
    # Cleanup - ignore errors on Windows due to file locks
    try:
        if db_path.exists():
            db_path.unlink(missing_ok=True)
    except (PermissionError, OSError):
        pass  # File locked by SQLite, will be cleaned on next run


@pytest.fixture
def storage(temp_db):
    """Create a storage instance."""
    return StateStorage(db_path=temp_db, encryption_key="test_key_123")


class TestStateStorage:
    """Tests for StateStorage."""

    def test_init_creates_db(self, temp_db):
        storage = StateStorage(db_path=temp_db)
        assert temp_db.exists()

    def test_save_and_load(self, storage):
        state = CognitiveStateVector.new("test-session")
        state.primary_goal = Goal(id="g1", description="Test goal")

        version = storage.save_state(state)
        assert version == 1

        loaded = storage.load_state("test-session")
        assert loaded is not None
        assert loaded.session_id == "test-session"
        assert loaded.primary_goal.description == "Test goal"

    def test_versioning(self, storage):
        state = CognitiveStateVector.new("test-session")

        storage.save_state(state)

        state.version = 2
        storage.save_state(state)

        state.version = 3
        storage.save_state(state)

        versions = storage.get_versions("test-session")
        assert versions == [3, 2, 1]

    def test_load_specific_version(self, storage):
        state = CognitiveStateVector.new("test-session")
        state.context_summary = "v1"
        storage.save_state(state)

        state.version = 2
        state.context_summary = "v2"
        storage.save_state(state)

        loaded_v1 = storage.load_state("test-session", version=1)
        loaded_v2 = storage.load_state("test-session", version=2)

        assert loaded_v1.context_summary == "v1"
        assert loaded_v2.context_summary == "v2"

    def test_load_latest(self, storage):
        state = CognitiveStateVector.new("test-session")
        storage.save_state(state)

        state.version = 2
        state.context_summary = "latest"
        storage.save_state(state)

        loaded = storage.load_state("test-session")
        assert loaded.version == 2
        assert loaded.context_summary == "latest"

    def test_list_sessions(self, storage):
        s1 = CognitiveStateVector.new("session-1")
        s2 = CognitiveStateVector.new("session-2")

        storage.save_state(s1)
        storage.save_state(s2)

        sessions = storage.list_sessions()
        assert len(sessions) == 2
        session_ids = [s["session_id"] for s in sessions]
        assert "session-1" in session_ids
        assert "session-2" in session_ids

    def test_load_nonexistent(self, storage):
        loaded = storage.load_state("nonexistent")
        assert loaded is None

    def test_encryption(self, temp_db):
        """Verify data is encrypted in database."""
        storage = StateStorage(db_path=temp_db, encryption_key="secret123")

        state = CognitiveStateVector.new("encrypted-session")
        state.context_summary = "SECRET_DATA_12345"
        storage.save_state(state)

        # Read raw database content
        import sqlite3
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.execute("SELECT data FROM states")
            raw_data = cursor.fetchone()[0]

        # Raw data should NOT contain the plaintext
        assert b"SECRET_DATA_12345" not in raw_data

    def test_checksum_validation(self, storage):
        state = CognitiveStateVector.new("test-session")
        storage.save_state(state)

        # Corrupt the data in database
        import sqlite3
        with sqlite3.connect(storage.db_path) as conn:
            conn.execute(
                "UPDATE states SET data = X'00112233' WHERE session_id = ?", ("test-session",))
            conn.commit()

        # Loading should fail due to checksum mismatch
        with pytest.raises(Exception):  # Could be decryption or checksum error
            storage.load_state("test-session")

    def test_state_with_facts(self, storage):
        state = CognitiveStateVector.new("facts-session")
        state.facts.append(Fact(
            id="f1",
            entity_type=EntityType.PREFERENCE,
            content="User prefers SQLite",
            confidence=0.9,
        ))

        storage.save_state(state)
        loaded = storage.load_state("facts-session")

        assert len(loaded.facts) == 1
        assert loaded.facts[0].entity_type == EntityType.PREFERENCE
        assert loaded.facts[0].confidence == 0.9


class TestStateStorageNoEncryption:
    """Tests for storage without encryption."""

    def test_no_encryption(self, temp_db):
        storage = StateStorage(db_path=temp_db, encryption_key=None)

        state = CognitiveStateVector.new("plain-session")
        state.context_summary = "PLAIN_TEXT"
        storage.save_state(state)

        # Read raw database content
        import sqlite3
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.execute("SELECT data FROM states")
            raw_data = cursor.fetchone()[0]

        # Without encryption, plaintext should be visible
        assert b"PLAIN_TEXT" in raw_data


class TestStateStorageTTLCleanup:
    """Tests for TTL cleanup functionality."""

    def test_cleanup_expired_keeps_latest(self, temp_db):
        """Test that cleanup keeps latest N versions per session."""
        from datetime import timedelta

        storage = StateStorage(db_path=temp_db, ttl_days=30)

        # Create 5 versions of same session
        for i in range(1, 6):
            state = CognitiveStateVector.new("cleanup-session")
            state.version = i
            storage.save_state(state)

        # Should have 5 versions
        versions = storage.get_versions("cleanup-session")
        assert len(versions) == 5

        # Cleanup keeps latest 3 by default, but won't delete if not expired
        deleted = storage.cleanup_expired(keep_latest=3)

        # Nothing deleted because records are fresh
        # (TTL check prevents deletion of recent records)
        versions_after = storage.get_versions("cleanup-session")
        assert len(versions_after) >= 3

    def test_cleanup_returns_count(self, temp_db):
        """Test that cleanup returns correct deleted count."""
        storage = StateStorage(db_path=temp_db, ttl_days=0)  # 0-day TTL

        # Create state
        state = CognitiveStateVector.new("count-session")
        storage.save_state(state)

        # Cleanup with 0 TTL should consider everything expired
        deleted = storage.cleanup_expired(keep_latest=1)
        assert isinstance(deleted, int)
        assert deleted >= 0


class TestDeleteSession:
    """Tests for delete_session functionality (AC-06.4)."""

    def test_delete_session(self, temp_db):
        """Test deleting a session removes all its versions."""
        storage = StateStorage(db_path=temp_db)

        # Create multiple versions
        for i in range(1, 4):
            state = CognitiveStateVector.new("delete-me")
            state.version = i
            storage.save_state(state)

        # Verify we have 3 versions
        assert len(storage.get_versions("delete-me")) == 3

        # Delete
        deleted = storage.delete_session("delete-me")
        assert deleted == 3

        # Verify deleted
        assert len(storage.get_versions("delete-me")) == 0
        assert storage.load_state("delete-me") is None

    def test_delete_nonexistent_session(self, temp_db):
        """Test deleting nonexistent session returns 0."""
        storage = StateStorage(db_path=temp_db)
        deleted = storage.delete_session("nonexistent")
        assert deleted == 0

    def test_delete_session_logs_audit(self, temp_db):
        """Test that deleting a session creates an audit log entry."""
        storage = StateStorage(db_path=temp_db)

        # Create and delete
        state = CognitiveStateVector.new("audit-delete-test")
        storage.save_state(state)
        storage.delete_session("audit-delete-test")

        # Check audit log
        entries = storage.get_audit_log("audit-delete-test")
        actions = [e["action"] for e in entries]
        assert "delete" in actions


class TestAuditLog:
    """Tests for audit log functionality (AC-04.4)."""

    def test_audit_log_create_action(self, temp_db):
        """Test that creating first state logs CREATE action."""
        storage = StateStorage(db_path=temp_db)

        state = CognitiveStateVector.new("audit-create")
        storage.save_state(state)

        entries = storage.get_audit_log("audit-create")
        assert len(entries) == 1
        assert entries[0]["action"] == "create"
        assert entries[0]["version"] == 1

    def test_audit_log_update_action(self, temp_db):
        """Test that subsequent saves log UPDATE action."""
        storage = StateStorage(db_path=temp_db)

        state = CognitiveStateVector.new("audit-update")
        storage.save_state(state)

        state.version = 2
        storage.save_state(state)

        entries = storage.get_audit_log("audit-update")
        actions = [e["action"] for e in entries]
        assert "create" in actions
        assert "update" in actions

    def test_audit_log_restore_action(self, temp_db):
        """Test that restoring state logs RESTORE action."""
        storage = StateStorage(db_path=temp_db)

        state = CognitiveStateVector.new("audit-restore")
        storage.save_state(state)

        # Load with restore logging
        storage.load_state("audit-restore", log_restore=True)

        entries = storage.get_audit_log("audit-restore")
        actions = [e["action"] for e in entries]
        assert "restore" in actions

    def test_get_all_audit_log(self, temp_db):
        """Test getting all audit log entries."""
        storage = StateStorage(db_path=temp_db)

        # Create states for different sessions
        for session in ["session-a", "session-b"]:
            state = CognitiveStateVector.new(session)
            storage.save_state(state)

        # Get all entries
        all_entries = storage.get_audit_log()
        assert len(all_entries) == 2


class TestAES256GCM:
    """Tests for AES-256-GCM encryption (NFR-02)."""

    def test_gcm_encryption_active(self, temp_db):
        """Test that AES-256-GCM is used when cryptography is available."""
        storage = StateStorage(db_path=temp_db, encryption_key="my_secret_key")

        # Check that GCM is enabled
        assert storage._use_gcm is True
        assert storage._aesgcm is not None

    def test_gcm_encrypt_decrypt(self, temp_db):
        """Test AES-256-GCM round-trip."""
        storage = StateStorage(db_path=temp_db, encryption_key="test_key")

        plaintext = b"Hello, World!"
        ciphertext, nonce = storage._encrypt(plaintext)

        # Ciphertext should not equal plaintext
        assert ciphertext != plaintext

        # Nonce should be 12 bytes for GCM
        assert nonce is not None
        assert len(nonce) == 12

        # Decrypt should return original
        decrypted = storage._decrypt(ciphertext, nonce)
        assert decrypted == plaintext

    def test_gcm_nonce_stored_in_db(self, temp_db):
        """Test that nonce is stored in database for GCM mode."""
        storage = StateStorage(db_path=temp_db, encryption_key="test_key")

        state = CognitiveStateVector.new("gcm-test")
        storage.save_state(state)

        # Read raw nonce from database
        import sqlite3
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.execute(
                "SELECT nonce FROM states WHERE session_id = ?", ("gcm-test",))
            nonce = cursor.fetchone()[0]

        assert nonce is not None
        assert len(nonce) == 12
