"""Tests for AutoIndexer."""

import pytest
import tempfile
from pathlib import Path

from rlm_toolkit.indexer import AutoIndexer, IndexResult, index_project


class TestAutoIndexer:
    """Tests for AutoIndexer."""

    @pytest.fixture
    def project_dir(self, tmp_path):
        """Create temporary project with files."""
        # Create Python files
        (tmp_path / "main.py").write_text("def main(): pass")
        (tmp_path / "utils.py").write_text("def helper(): return 42")

        # Create subdirectory
        subdir = tmp_path / "src"
        subdir.mkdir()
        (subdir / "core.py").write_text("class Core: pass")

        return tmp_path

    @pytest.fixture
    def indexer(self, project_dir):
        """Create indexer for project."""
        return AutoIndexer(project_dir, languages=["python"])

    def test_not_indexed_initially(self, indexer):
        """Test project is not indexed initially."""
        assert not indexer.is_indexed()

    def test_discover_files(self, indexer, project_dir):
        """Test file discovery."""
        files = indexer._discover_files()

        assert len(files) == 3
        assert any(f.name == "main.py" for f in files)

    def test_full_index(self, indexer):
        """Test full project indexing."""
        result = indexer._index_full()

        assert result.files_indexed == 3
        assert indexer.is_indexed()

    def test_get_status(self, indexer):
        """Test getting indexer status."""
        status = indexer.get_status()

        assert "indexed" in status
        assert "crystals" in status
        assert "needs_update" in status

    def test_delta_update(self, indexer, project_dir):
        """Test delta update."""
        # First, full index
        indexer._index_full()

        # Modify a file
        (project_dir / "main.py").write_text("def main(): return 1")

        # Delta update
        updated = indexer.delta_update([str(project_dir / "main.py")])

        assert updated == 1

    def test_get_new_files(self, indexer, project_dir):
        """Test finding new files."""
        # Index first
        indexer._index_full()

        # Add new file
        (project_dir / "new.py").write_text("# new")

        new_files = indexer.get_new_files()

        assert len(new_files) == 1
        assert new_files[0].name == "new.py"

    def test_ensure_indexed(self, indexer):
        """Test ensure_indexed."""
        # First call should start indexing
        result = indexer.ensure_indexed()

        # Wait for indexing (in real code this is background)
        import time

        time.sleep(0.5)

        # Already indexed now
        assert indexer.is_indexed()

    def test_ignore_dirs(self, project_dir):
        """Test ignored directories."""
        # Create node_modules (should be ignored)
        nm = project_dir / "node_modules"
        nm.mkdir()
        (nm / "package.js").write_text("// ignored")

        # Create venv (should be ignored)
        venv = project_dir / "venv"
        venv.mkdir()
        (venv / "lib.py").write_text("# ignored")

        indexer = AutoIndexer(project_dir)
        files = indexer._discover_files()

        # Should not include ignored dirs
        assert not any("node_modules" in str(f) for f in files)
        assert not any("venv" in str(f) for f in files)

    def test_progress_callback(self, project_dir):
        """Test progress callback."""
        progress_calls = []

        def on_progress(msg, current, total):
            progress_calls.append((msg, current, total))

        indexer = AutoIndexer(project_dir, on_progress=on_progress)
        indexer._index_full()

        assert len(progress_calls) > 0


class TestIndexProject:
    """Tests for index_project convenience function."""

    def test_index_project(self, tmp_path):
        """Test convenience function."""
        (tmp_path / "app.py").write_text("x = 1")

        result = index_project(tmp_path, languages=["python"])

        assert result.files_indexed == 1
