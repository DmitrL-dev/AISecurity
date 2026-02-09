"""
Tests for thread-safe SQLite connection module.

Tests verify:
- check_same_thread=False is set
- WAL mode is enabled
- busy_timeout is configured
- safe_connection context manager works
- Multi-thread access doesn't crash
"""

import sqlite3
import threading
import pytest
from pathlib import Path

from rlm_toolkit.storage.connection import (
    get_connection,
    safe_connection,
)


class TestGetConnection:
    """Tests for get_connection factory."""

    def test_returns_connection(self, tmp_path):
        """get_connection returns a sqlite3.Connection."""
        db = tmp_path / "test.db"
        conn = get_connection(db)
        assert isinstance(conn, sqlite3.Connection)
        conn.close()

    def test_check_same_thread_false(self, tmp_path):
        """Connection allows cross-thread access."""
        db = tmp_path / "test.db"
        conn = get_connection(db)

        # Create a table in main thread
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, val TEXT)")
        conn.execute("INSERT INTO test VALUES (1, 'hello')")
        conn.commit()

        # Read from another thread — should NOT raise
        results = []
        errors = []

        def read_from_thread():
            try:
                row = conn.execute("SELECT val FROM test WHERE id = 1").fetchone()
                results.append(row[0])
            except Exception as e:
                errors.append(e)

        t = threading.Thread(target=read_from_thread)
        t.start()
        t.join(timeout=5)

        assert not errors, f"Cross-thread access failed: {errors}"
        assert results == ["hello"]
        conn.close()

    def test_wal_mode_enabled(self, tmp_path):
        """WAL journal mode is set for file databases."""
        db = tmp_path / "test.db"
        conn = get_connection(db, wal_mode=True)

        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode == "wal"
        conn.close()

    def test_wal_mode_skip_memory(self):
        """WAL mode is skipped for :memory: databases."""
        conn = get_connection(":memory:", wal_mode=True)
        # :memory: databases don't support WAL
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode == "memory"
        conn.close()

    def test_busy_timeout_set(self, tmp_path):
        """busy_timeout PRAGMA is configured."""
        db = tmp_path / "test.db"
        conn = get_connection(db)

        timeout = conn.execute("PRAGMA busy_timeout").fetchone()[0]
        assert timeout == 5000
        conn.close()

    def test_row_factory_set(self, tmp_path):
        """Row factory is applied when specified."""
        db = tmp_path / "test.db"
        conn = get_connection(db, row_factory=sqlite3.Row)

        conn.execute("CREATE TABLE test (id INTEGER, name TEXT)")
        conn.execute("INSERT INTO test VALUES (1, 'test')")
        conn.commit()

        row = conn.execute("SELECT * FROM test").fetchone()
        assert row["name"] == "test"
        conn.close()

    def test_accepts_string_path(self, tmp_path):
        """Works with string paths."""
        db = str(tmp_path / "test.db")
        conn = get_connection(db)
        assert isinstance(conn, sqlite3.Connection)
        conn.close()

    def test_accepts_path_object(self, tmp_path):
        """Works with Path objects."""
        db = tmp_path / "test.db"
        conn = get_connection(db)
        assert isinstance(conn, sqlite3.Connection)
        conn.close()


class TestSafeConnection:
    """Tests for safe_connection context manager."""

    def test_basic_usage(self, tmp_path):
        """Context manager provides connection and auto-commits."""
        db = tmp_path / "test.db"

        with safe_connection(db) as conn:
            conn.execute("CREATE TABLE test (val TEXT)")
            conn.execute("INSERT INTO test VALUES ('hello')")

        # Verify data persisted (auto-committed)
        with safe_connection(db) as conn:
            row = conn.execute("SELECT val FROM test").fetchone()
            assert row[0] == "hello"

    def test_rollback_on_error(self, tmp_path):
        """Context manager rolls back on exception."""
        db = tmp_path / "test.db"

        # Create table first
        with safe_connection(db) as conn:
            conn.execute("CREATE TABLE test (val TEXT)")
            conn.execute("INSERT INTO test VALUES ('original')")

        # This should rollback
        with pytest.raises(ValueError):
            with safe_connection(db) as conn:
                conn.execute("INSERT INTO test VALUES ('bad')")
                raise ValueError("test error")

        # Verify rollback — only 'original' remains
        with safe_connection(db) as conn:
            rows = conn.execute("SELECT val FROM test").fetchall()
            assert len(rows) == 1
            assert rows[0][0] == "original"

    def test_connection_closed_after_use(self, tmp_path):
        """Connection is closed after context exits."""
        db = tmp_path / "test.db"

        with safe_connection(db) as conn:
            conn.execute("CREATE TABLE test (val TEXT)")

        # Connection should be closed - operations should fail
        with pytest.raises(Exception):
            conn.execute("SELECT 1")

    def test_thread_safe(self, tmp_path):
        """Multiple threads can use safe_connection concurrently."""
        db = tmp_path / "test.db"

        with safe_connection(db) as conn:
            conn.execute(
                "CREATE TABLE test " "(id INTEGER PRIMARY KEY, thread_id INTEGER)"
            )

        errors = []

        def writer(thread_id):
            try:
                with safe_connection(db) as conn:
                    conn.execute(
                        "INSERT INTO test (thread_id) VALUES (?)",
                        (thread_id,),
                    )
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors, f"Thread-safe writes failed: {errors}"

        with safe_connection(db) as conn:
            count = conn.execute("SELECT COUNT(*) FROM test").fetchone()[0]
            assert count == 10
