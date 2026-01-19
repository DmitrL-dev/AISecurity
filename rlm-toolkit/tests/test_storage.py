"""Tests for SQLite Storage."""

import pytest
import time
import tempfile
from pathlib import Path

from rlm_toolkit.storage import CrystalStorage, get_storage
from rlm_toolkit.freshness import FreshnessMetadata


class MockCrystal:
    """Mock crystal for testing."""

    def __init__(self, path: str, name: str):
        self.path = path
        self.name = name
        self.primitives = []
        self.token_count = 100
        self.content_hash = "abc123"


class TestCrystalStorage:
    """Tests for CrystalStorage."""

    @pytest.fixture
    def storage(self, tmp_path):
        """Create storage in temp directory."""
        return CrystalStorage(tmp_path / ".rlm")

    @pytest.fixture
    def crystal(self):
        """Create mock crystal."""
        return MockCrystal("/test/file.py", "file.py")

    @pytest.fixture
    def freshness(self):
        """Create freshness metadata."""
        return FreshnessMetadata(
            indexed_at=time.time(),
            source_mtime=time.time(),
            source_hash="abc123",
        )

    def test_save_and_load(self, storage, crystal, freshness):
        """Test saving and loading crystal."""
        storage.save_crystal(crystal, freshness)

        loaded = storage.load_crystal(crystal.path)

        assert loaded is not None
        assert loaded["crystal"]["path"] == crystal.path
        assert loaded["freshness"].source_hash == freshness.source_hash

    def test_has_crystal(self, storage, crystal, freshness):
        """Test checking crystal existence."""
        assert not storage.has_crystal(crystal.path)

        storage.save_crystal(crystal, freshness)

        assert storage.has_crystal(crystal.path)

    def test_delete_crystal(self, storage, crystal, freshness):
        """Test deleting crystal."""
        storage.save_crystal(crystal, freshness)
        assert storage.has_crystal(crystal.path)

        storage.delete_crystal(crystal.path)

        assert not storage.has_crystal(crystal.path)

    def test_load_all(self, storage, freshness):
        """Test loading all crystals."""
        for i in range(5):
            c = MockCrystal(f"/test/file{i}.py", f"file{i}.py")
            storage.save_crystal(c, freshness)

        all_crystals = list(storage.load_all())

        assert len(all_crystals) == 5

    def test_get_stale_crystals(self, storage, crystal):
        """Test getting stale crystals."""
        old_freshness = FreshnessMetadata(
            indexed_at=time.time() - (48 * 3600),  # 48 hours ago
            source_mtime=time.time(),
            source_hash="abc",
        )

        storage.save_crystal(crystal, old_freshness)

        stale = storage.get_stale_crystals(ttl_hours=24)

        assert crystal.path in stale

    def test_get_stats(self, storage, crystal, freshness):
        """Test getting statistics."""
        storage.save_crystal(crystal, freshness)

        stats = storage.get_stats()

        assert stats["total_crystals"] == 1
        assert stats["db_size_mb"] > 0

    def test_metadata(self, storage):
        """Test metadata storage."""
        storage.set_metadata("last_commit", "abc123")

        value = storage.get_metadata("last_commit")

        assert value == "abc123"

    def test_mark_validated(self, storage, crystal, freshness):
        """Test marking as validated."""
        storage.save_crystal(crystal, freshness)

        storage.mark_validated(crystal.path)

        loaded = storage.load_crystal(crystal.path)
        assert loaded["freshness"].last_validated is not None

    def test_confirm_current(self, storage, crystal, freshness):
        """Test human confirmation."""
        storage.save_crystal(crystal, freshness)

        storage.confirm_current(crystal.path)

        loaded = storage.load_crystal(crystal.path)
        assert loaded["freshness"].human_confirmed

    def test_clear(self, storage, crystal, freshness):
        """Test clearing storage."""
        storage.save_crystal(crystal, freshness)

        count = storage.clear()

        assert count == 1
        assert not storage.has_crystal(crystal.path)


class TestGetStorage:
    """Tests for get_storage function."""

    def test_get_storage(self, tmp_path):
        """Test getting storage for project."""
        storage = get_storage(tmp_path)

        assert storage is not None
        assert (tmp_path / ".rlm").exists()
