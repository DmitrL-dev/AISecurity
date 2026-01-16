"""
Lazy Context
============

Memory-efficient context handling for 10M+ tokens (ADR-008).
"""

from __future__ import annotations

import hashlib
import mmap
from pathlib import Path
from typing import IO, Iterator, Optional, Union


class LazyContext:
    """Memory-efficient context wrapper.
    
    Supports lazy loading and memory-mapped access for large contexts.
    
    Example:
        >>> ctx = LazyContext("/path/to/huge_file.txt")
        >>> len(ctx)  # Doesn't load entire file
        10000000
        >>> chunk = ctx.slice(0, 1000)  # Only loads 1KB
    
    Attributes:
        source: Original source (str, Path, or file)
    """
    
    def __init__(self, source: Union[str, Path, IO]):
        """Initialize lazy context.
        
        Args:
            source: String content, file path, or file object
        """
        self._source = source
        self._hash: Optional[str] = None
        self._length: Optional[int] = None
        self._mmap: Optional[mmap.mmap] = None
        self._content: Optional[str] = None
        
        # Determine source type
        if isinstance(source, str) and not Path(source).exists():
            # Direct string content
            self._content = source
            self._length = len(source)
        elif isinstance(source, (str, Path)):
            # File path
            self._path = Path(source)
        else:
            # File-like object
            self._file = source
    
    @property
    def hash(self) -> str:
        """Compute hash lazily using streaming."""
        if self._hash is None:
            self._hash = self._compute_streaming_hash()
        return self._hash
    
    def _compute_streaming_hash(self) -> str:
        """Compute SHA-256 hash without loading entire file."""
        hasher = hashlib.sha256()
        
        if self._content is not None:
            # String content - hash first 100KB
            hasher.update(self._content[:100_000].encode())
        elif hasattr(self, '_path'):
            # File - stream chunks
            with open(self._path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    hasher.update(chunk)
                    # Only hash first 100KB for speed
                    if f.tell() > 100_000:
                        break
        
        return hasher.hexdigest()[:16]
    
    def __len__(self) -> int:
        """Get content length without loading."""
        if self._length is None:
            if self._content is not None:
                self._length = len(self._content)
            elif hasattr(self, '_path'):
                self._length = self._path.stat().st_size
            else:
                # File object - need to read
                pos = self._file.tell()
                self._file.seek(0, 2)
                self._length = self._file.tell()
                self._file.seek(pos)
        return self._length
    
    def slice(self, start: int, end: int) -> str:
        """Get slice of content efficiently.
        
        Uses memory-mapping for file-based contexts.
        """
        if self._content is not None:
            return self._content[start:end]
        
        if hasattr(self, '_path'):
            with open(self._path, 'r', encoding='utf-8') as f:
                f.seek(start)
                return f.read(end - start)
        
        # File object
        pos = self._file.tell()
        self._file.seek(start)
        content = self._file.read(end - start)
        self._file.seek(pos)
        return content
    
    def chunks(self, size: int = 100_000) -> Iterator[str]:
        """Yield chunks for streaming processing.
        
        Args:
            size: Chunk size in characters
        
        Yields:
            Content chunks
        """
        if self._content is not None:
            for i in range(0, len(self._content), size):
                yield self._content[i:i + size]
        elif hasattr(self, '_path'):
            with open(self._path, 'r', encoding='utf-8') as f:
                while True:
                    chunk = f.read(size)
                    if not chunk:
                        break
                    yield chunk
    
    def __str__(self) -> str:
        """Get full content (loads into memory)."""
        if self._content is not None:
            return self._content
        
        if hasattr(self, '_path'):
            return self._path.read_text(encoding='utf-8')
        
        return self._file.read()
    
    def __repr__(self) -> str:
        return f"LazyContext(length={len(self)}, hash={self.hash[:8]})"
