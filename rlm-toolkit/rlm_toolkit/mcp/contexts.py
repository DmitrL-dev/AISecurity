"""
Context Manager for RLM MCP Server.

Handles loading, storing, and managing contexts (files/directories).
"""

import os
import json
import hashlib
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

logger = logging.getLogger("rlm_mcp.contexts")


class ContextManager:
    """Manages loaded contexts for RLM MCP Server."""

    # Supported file extensions
    SUPPORTED_EXTENSIONS = {
        '.py', '.js', '.ts', '.jsx', '.tsx',  # Code
        '.md', '.txt', '.rst',                 # Docs
        '.json', '.yaml', '.yml', '.toml',     # Config
        '.html', '.css', '.scss',              # Web
        '.sql', '.sh', '.bash',                # Scripts
    }

    # Security limits (per Dr. Security review)
    MAX_FILE_SIZE_MB = 10  # Max size per file
    MAX_TOTAL_SIZE_MB = 100  # Max total context size
    MAX_FILES_PER_CONTEXT = 1000  # Max files in directory load

    def __init__(self, storage_dir: Optional[str] = None):
        """
        Initialize context manager.

        Args:
            storage_dir: Directory for persistent storage (default: .rlm/)
        """
        self.contexts: Dict[str, Dict[str, Any]] = {}
        self.storage_dir = Path(
            storage_dir) if storage_dir else self._find_storage_dir()
        self._ensure_storage_dir()

    def _find_storage_dir(self) -> Path:
        """Find or create .rlm directory in project root.

        Priority:
        1. RLM_PROJECT_ROOT env var (explicit configuration)
        2. Walk up from cwd to find .git or pyproject.toml
        3. Fallback to ~/.rlm (user home, survives IDE updates)
        """
        # Priority 1: Explicit env var
        project_root = os.getenv("RLM_PROJECT_ROOT")
        if project_root:
            return Path(project_root) / '.rlm'

        # Priority 2: Find project root by markers
        cwd = Path.cwd()
        markers = ['.git', 'pyproject.toml', 'package.json']

        for parent in [cwd] + list(cwd.parents):
            if any((parent / marker).exists() for marker in markers):
                return parent / '.rlm'

        # Priority 3: Fallback to user home directory
        return Path.home() / '.rlm'

    def _ensure_storage_dir(self):
        """Create storage directories if they don't exist."""
        (self.storage_dir / 'contexts').mkdir(parents=True, exist_ok=True)
        (self.storage_dir / 'crystals').mkdir(parents=True, exist_ok=True)
        (self.storage_dir / 'memory').mkdir(parents=True, exist_ok=True)
        (self.storage_dir / 'cache').mkdir(parents=True, exist_ok=True)

    async def load(self, path: str, name: Optional[str] = None) -> Dict[str, Any]:
        """
        Load a file or directory into context.

        Args:
            path: Path to file or directory
            name: Optional name for the context

        Returns:
            Context metadata
        """
        path = Path(path).resolve()

        if not path.exists():
            raise FileNotFoundError(f"Path not found: {path}")

        # Generate name if not provided
        if not name:
            name = path.name

        # Load content
        if path.is_file():
            content = self._load_file(path)
            file_count = 1
        else:
            content, file_count = self._load_directory(path)

        # Calculate metadata
        token_count = self._estimate_tokens(content)
        content_hash = hashlib.md5(content.encode()).hexdigest()[:8]

        # Store context
        context = {
            "name": name,
            "path": str(path),
            "content": content,
            "token_count": token_count,
            "file_count": file_count,
            "content_hash": content_hash,
            "loaded_at": datetime.now().isoformat(),
        }

        self.contexts[name] = context

        # Persist to disk
        self._save_context_metadata(name, context)

        logger.info(
            f"Loaded context '{name}': {file_count} files, {token_count} tokens")

        return {
            "name": name,
            "path": str(path),
            "token_count": token_count,
            "file_count": file_count,
        }

    def _load_file(self, path: Path) -> str:
        """Load a single file."""
        try:
            return path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            logger.warning(f"Cannot read file (not UTF-8): {path}")
            return ""

    def _load_directory(self, path: Path) -> tuple[str, int]:
        """Load all supported files from directory recursively."""
        contents = []
        file_count = 0

        for file_path in path.rglob('*'):
            # Skip hidden files and directories
            if any(part.startswith('.') for part in file_path.parts):
                continue

            # Skip unsupported extensions
            if file_path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
                continue

            if file_path.is_file():
                content = self._load_file(file_path)
                if content:
                    relative_path = file_path.relative_to(path)
                    contents.append(f"# File: {relative_path}\n{content}\n")
                    file_count += 1

        return "\n".join(contents), file_count

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (rough approximation: 4 chars = 1 token)."""
        return len(text) // 4

    def _save_context_metadata(self, name: str, context: Dict[str, Any]):
        """Save context metadata to disk."""
        metadata_path = self.storage_dir / 'contexts' / f'{name}.meta.json'

        # Don't save content to metadata file (too large)
        metadata = {k: v for k, v in context.items() if k != 'content'}

        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

    def get(self, name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get a loaded context by name.

        Args:
            name: Context name (returns first if not specified)

        Returns:
            Context dict or None
        """
        if name:
            return self.contexts.get(name)

        # Return first context if no name specified
        if self.contexts:
            return next(iter(self.contexts.values()))

        return None

    def list_all(self) -> List[Dict[str, Any]]:
        """List all loaded contexts (without content)."""
        return [
            {k: v for k, v in ctx.items() if k != 'content'}
            for ctx in self.contexts.values()
        ]

    def clear(self, name: Optional[str] = None):
        """Clear context(s)."""
        if name:
            self.contexts.pop(name, None)
        else:
            self.contexts.clear()
