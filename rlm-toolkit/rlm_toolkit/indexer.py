"""
Automatic Project Indexer.

Handles:
- First-time full project indexing
- Background indexing
- Delta updates for changed files
- File watching for realtime updates
"""

import os
import time
import logging
import threading
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set

from .crystal import HPEExtractor
from .freshness import FreshnessMetadata
from .storage import CrystalStorage, get_storage

logger = logging.getLogger("rlm_indexer")


class IndexResult:
    """Result of indexing operation."""

    def __init__(self):
        self.files_indexed = 0
        self.files_skipped = 0
        self.files_failed = 0
        self.primitives_extracted = 0
        self.duration_seconds = 0.0
        self.errors: List[str] = []

    def __str__(self):
        return (
            f"Indexed {self.files_indexed} files, "
            f"{self.primitives_extracted} primitives in {self.duration_seconds:.1f}s"
        )


class AutoIndexer:
    """
    Automatic project indexer.

    Handles full indexing, delta updates, and file watching.
    No CLI required - works automatically.

    Example:
        >>> indexer = AutoIndexer(Path("/project"))
        >>> indexer.ensure_indexed()  # Auto-indexes if needed
        >>> indexer.start_watching()   # Watch for changes
    """

    # File extensions to index by language
    EXTENSIONS = {
        "python": [".py", ".pyi"],
        "javascript": [".js", ".ts", ".jsx", ".tsx"],
        "go": [".go"],
        "rust": [".rs"],
        "c": [".c", ".h", ".cpp", ".hpp"],
        "java": [".java"],
        "ruby": [".rb"],
        "markdown": [".md"],
    }

    # Directories to ignore
    IGNORE_DIRS = {
        ".git",
        ".rlm",
        "__pycache__",
        "node_modules",
        "venv",
        ".venv",
        "env",
        ".env",
        "build",
        "dist",
        ".tox",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
    }

    def __init__(
        self,
        project_root: Path,
        languages: Optional[List[str]] = None,
        on_progress: Optional[Callable[[str, int, int], None]] = None,
    ):
        """
        Initialize indexer.

        Args:
            project_root: Root directory of project
            languages: Languages to index (default: all)
            on_progress: Callback for progress updates (message, current, total)
        """
        self.root = Path(project_root)
        self.languages = languages
        self.on_progress = on_progress

        self.storage = get_storage(self.root)
        self.extractor = HPEExtractor(use_spacy=False)  # Fast mode

        self._indexing = False
        self._watch_thread: Optional[threading.Thread] = None

    @property
    def extensions(self) -> Set[str]:
        """Get file extensions to index."""
        if self.languages:
            exts = set()
            for lang in self.languages:
                exts.update(self.EXTENSIONS.get(lang, []))
            return exts

        # All extensions
        return {ext for exts in self.EXTENSIONS.values() for ext in exts}

    def is_indexed(self) -> bool:
        """Check if project is already indexed."""
        stats = self.storage.get_stats()
        return stats["total_crystals"] > 0

    def ensure_indexed(self, force: bool = False) -> bool:
        """
        Ensure project is indexed.

        Returns True if already indexed, False if indexing started.
        """
        if not force and self.is_indexed():
            # Check for updates
            modified = self.storage.get_modified_files(self.root)
            if modified:
                logger.info(f"{len(modified)} files modified, updating...")
                self.delta_update(modified)
            return True

        # Start background indexing
        self._start_background_index()
        return False

    def _start_background_index(self):
        """Start indexing in background thread."""
        if self._indexing:
            return

        self._indexing = True
        thread = threading.Thread(
            target=self._index_full,
            daemon=True,
            name="rlm-auto-indexer",
        )
        thread.start()

        self._notify("🔄 Indexing project in background...")

    def _index_full(self) -> IndexResult:
        """Full project indexing."""
        result = IndexResult()
        start_time = time.time()

        try:
            files = list(self._discover_files())
            total = len(files)

            logger.info(f"Indexing {total} files...")

            for i, file_path in enumerate(files):
                try:
                    self._index_file(file_path)
                    result.files_indexed += 1

                    if self.on_progress:
                        self.on_progress(f"Indexing {file_path.name}", i + 1, total)

                except Exception as e:
                    result.files_failed += 1
                    result.errors.append(f"{file_path}: {e}")
                    logger.error(f"Failed to index {file_path}: {e}")

            # Save last indexed commit if git
            self._save_git_commit()

        finally:
            self._indexing = False

        result.duration_seconds = time.time() - start_time
        result.primitives_extracted = self.storage.get_stats()["total_crystals"]

        logger.info(f"Indexing complete: {result}")
        self._notify(f"✅ Indexed {result.files_indexed} files")

        return result

    def _index_file(self, file_path: Path) -> None:
        """Index a single file."""
        content = file_path.read_text(encoding="utf-8", errors="ignore")

        crystal = self.extractor.extract_from_file(
            str(file_path),
            content,
        )

        freshness = FreshnessMetadata.from_file(file_path)

        self.storage.save_crystal(crystal, freshness)

    def _discover_files(self) -> List[Path]:
        """Discover files to index."""
        files = []

        for root, dirs, filenames in os.walk(self.root):
            # Filter ignored directories
            dirs[:] = [d for d in dirs if d not in self.IGNORE_DIRS]

            for filename in filenames:
                if any(filename.endswith(ext) for ext in self.extensions):
                    files.append(Path(root) / filename)

        return files

    def delta_update(self, modified_paths: List[str]) -> int:
        """Update only modified files."""
        updated = 0

        for path_str in modified_paths:
            path = Path(path_str)

            if not path.exists():
                # File deleted
                self.storage.delete_crystal(path_str)
                updated += 1
            else:
                # File modified
                try:
                    self._index_file(path)
                    updated += 1
                except Exception as e:
                    logger.error(f"Failed to update {path}: {e}")

        logger.info(f"Delta update: {updated} files")
        return updated

    def get_new_files(self) -> List[Path]:
        """Find files not yet indexed."""
        new_files = []

        for file_path in self._discover_files():
            if not self.storage.has_crystal(str(file_path)):
                new_files.append(file_path)

        return new_files

    def start_watching(self) -> bool:
        """Start file watcher for realtime updates."""
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler
        except ImportError:
            logger.warning("watchdog not installed, file watching disabled")
            return False

        indexer = self

        class Handler(FileSystemEventHandler):
            def on_modified(self, event):
                if event.is_directory:
                    return

                path = Path(event.src_path)
                if any(path.suffix == ext for ext in indexer.extensions):
                    logger.debug(f"File modified: {path}")
                    indexer.delta_update([str(path)])

            def on_created(self, event):
                self.on_modified(event)

            def on_deleted(self, event):
                if not event.is_directory:
                    indexer.storage.delete_crystal(event.src_path)

        observer = Observer()
        observer.schedule(Handler(), str(self.root), recursive=True)
        observer.start()

        logger.info("File watcher started")
        return True

    def _save_git_commit(self):
        """Save current git commit hash."""
        try:
            import subprocess

            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.root,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                self.storage.set_metadata("last_commit", result.stdout.strip())
        except Exception:
            pass

    def _notify(self, message: str):
        """Send notification (to IDE/user)."""
        if self.on_progress:
            self.on_progress(message, 0, 0)
        logger.info(message)

    def get_status(self) -> Dict:
        """Get indexer status."""
        stats = self.storage.get_stats()
        modified = self.storage.get_modified_files(self.root)
        new_files = len(self.get_new_files())

        return {
            "indexed": self.is_indexed(),
            "indexing": self._indexing,
            "crystals": stats["total_crystals"],
            "tokens": stats["total_tokens"],
            "modified_files": len(modified),
            "new_files": new_files,
            "db_size_mb": stats.get("db_size_mb", 0),
            "needs_update": len(modified) > 0 or new_files > 0,
        }


def index_project(project_root: Path, **kwargs) -> IndexResult:
    """Convenience function to index a project."""
    indexer = AutoIndexer(project_root, **kwargs)
    return indexer._index_full()
