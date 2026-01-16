"""
Virtual Filesystem
==================

In-memory sandboxed filesystem for REPL execution.
Prevents disk exhaustion attacks (CIRCLE FR-3.9).
"""

from __future__ import annotations

import io
import os
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Any, Dict, Iterator, Optional, Union


class DiskQuotaExceeded(Exception):
    """Raised when virtual filesystem quota is exceeded."""
    pass


class VirtualFile:
    """In-memory file object.
    
    Mimics real file interface for sandboxed file operations.
    """
    
    def __init__(self, fs: "VirtualFS", path: str, mode: str = "r"):
        self._fs = fs
        self._path = path
        self._mode = mode
        self._buffer: io.BytesIO | io.StringIO
        self._closed = False
        
        if "b" in mode:
            # Binary mode
            if "r" in mode or "a" in mode:
                # Read existing content for read or append mode
                try:
                    content = fs.read_bytes(path)
                except FileNotFoundError:
                    content = b""
                self._buffer = io.BytesIO(content)
                if "a" in mode:
                    self._buffer.seek(0, 2)  # Seek to end for append
            else:
                self._buffer = io.BytesIO()
        else:
            # Text mode
            if "r" in mode or "a" in mode:
                # Read existing content for read or append mode
                try:
                    text_content = fs.read_text(path)
                except FileNotFoundError:
                    text_content = ""
                self._buffer = io.StringIO(text_content)
                if "a" in mode:
                    self._buffer.seek(0, 2)  # Seek to end for append
            else:
                self._buffer = io.StringIO()
    
    def read(self, size: int = -1) -> Union[str, bytes]:
        return self._buffer.read(size)
    
    def readline(self) -> Union[str, bytes]:
        return self._buffer.readline()
    
    def readlines(self) -> list:
        return self._buffer.readlines()
    
    def write(self, data: Union[str, bytes]) -> int:
        if "r" in self._mode and "+" not in self._mode:
            raise IOError("File not open for writing")
        # Type-safe write based on buffer type
        if isinstance(self._buffer, io.BytesIO):
            if isinstance(data, str):
                data = data.encode()
            return self._buffer.write(data)
        else:
            if isinstance(data, bytes):
                data = data.decode()
            return self._buffer.write(data)
    
    def close(self) -> None:
        if not self._closed:
            # Write back to virtual FS if in write mode
            if "w" in self._mode or "a" in self._mode or "+" in self._mode:
                self._buffer.seek(0)
                content = self._buffer.read()
                if isinstance(content, str):
                    self._fs.write_text(self._path, content)
                else:
                    self._fs.write_bytes(self._path, content)
            self._closed = True
    
    def __enter__(self) -> "VirtualFile":
        return self
    
    def __exit__(self, *args) -> None:
        self.close()
    
    def seek(self, pos: int, whence: int = 0) -> int:
        return self._buffer.seek(pos, whence)
    
    def tell(self) -> int:
        return self._buffer.tell()
    
    @property
    def closed(self) -> bool:
        return self._closed


class VirtualFS:
    """In-memory virtual filesystem.
    
    Provides sandboxed file operations with quota enforcement.
    
    Example:
        >>> vfs = VirtualFS(max_size_mb=10)
        >>> vfs.write_text("/data/result.txt", "Hello")
        >>> print(vfs.read_text("/data/result.txt"))
        Hello
    
    Attributes:
        max_size: Maximum total size in bytes
        current_size: Current usage in bytes
    """
    
    def __init__(self, max_size_mb: int = 100):
        """Initialize virtual filesystem.
        
        Args:
            max_size_mb: Maximum total storage in MB (default: 100)
        """
        self._files: Dict[str, bytes] = {}
        self.max_size = max_size_mb * 1024 * 1024
        self.current_size = 0
    
    def _normalize_path(self, path: str) -> str:
        """Normalize path to consistent format."""
        # Convert to forward slashes, make absolute
        path = path.replace("\\", "/")
        if not path.startswith("/"):
            path = "/" + path
        # Resolve . and ..
        parts: list[str] = []
        for part in path.split("/"):
            if part == "..":
                if parts:
                    parts.pop()
            elif part and part != ".":
                parts.append(part)
        return "/" + "/".join(parts)
    
    def write_bytes(self, path: str, content: bytes) -> None:
        """Write bytes to virtual file.
        
        Args:
            path: File path
            content: Bytes content
        
        Raises:
            DiskQuotaExceeded: If quota would be exceeded
        """
        path = self._normalize_path(path)
        
        # Calculate size change
        old_size = len(self._files.get(path, b""))
        new_size = len(content)
        size_delta = new_size - old_size
        
        if self.current_size + size_delta > self.max_size:
            raise DiskQuotaExceeded(
                f"Quota exceeded: {self.current_size + size_delta} > {self.max_size} bytes "
                f"(max {self.max_size // 1024 // 1024}MB)"
            )
        
        self._files[path] = content
        self.current_size += size_delta
    
    def write_text(self, path: str, content: str, encoding: str = "utf-8") -> None:
        """Write text to virtual file."""
        self.write_bytes(path, content.encode(encoding))
    
    def read_bytes(self, path: str) -> bytes:
        """Read bytes from virtual file."""
        path = self._normalize_path(path)
        if path not in self._files:
            raise FileNotFoundError(f"Virtual file not found: {path}")
        return self._files[path]
    
    def read_text(self, path: str, encoding: str = "utf-8") -> str:
        """Read text from virtual file."""
        return self.read_bytes(path).decode(encoding)
    
    def exists(self, path: str) -> bool:
        """Check if file exists."""
        path = self._normalize_path(path)
        return path in self._files
    
    def delete(self, path: str) -> bool:
        """Delete file and free quota."""
        path = self._normalize_path(path)
        if path in self._files:
            self.current_size -= len(self._files[path])
            del self._files[path]
            return True
        return False
    
    def list_dir(self, path: str = "/") -> list[str]:
        """List files in directory."""
        path = self._normalize_path(path)
        if not path.endswith("/"):
            path += "/"
        
        result = set()
        for file_path in self._files:
            if file_path.startswith(path):
                remainder = file_path[len(path):]
                if "/" in remainder:
                    # Directory
                    result.add(remainder.split("/")[0] + "/")
                else:
                    # File
                    result.add(remainder)
        return sorted(result)
    
    def open(self, path: str, mode: str = "r") -> VirtualFile:
        """Open virtual file.
        
        Returns file-like object for use in with statements.
        """
        path = self._normalize_path(path)
        
        # Create empty file if opening for write
        if "w" in mode and path not in self._files:
            self._files[path] = b""
        
        return VirtualFile(self, path, mode)
    
    def cleanup(self) -> None:
        """Clear all files and reset quota."""
        self._files.clear()
        self.current_size = 0
    
    @property
    def usage_percent(self) -> float:
        """Current usage as percentage."""
        return (self.current_size / self.max_size) * 100 if self.max_size > 0 else 0
    
    def __repr__(self) -> str:
        return f"VirtualFS(files={len(self._files)}, usage={self.usage_percent:.1f}%)"


class VirtualPath:
    """Sandboxed pathlib.Path replacement.
    
    Provides safe path operations that work with VirtualFS.
    """
    
    def __init__(self, path: str, fs: VirtualFS):
        self._path = path
        self._fs = fs
    
    def __truediv__(self, other: str) -> "VirtualPath":
        new_path = str(PurePosixPath(self._path) / other)
        return VirtualPath(new_path, self._fs)
    
    def __str__(self) -> str:
        return self._path
    
    def exists(self) -> bool:
        return self._fs.exists(self._path)
    
    def read_text(self, encoding: str = "utf-8") -> str:
        return self._fs.read_text(self._path, encoding)
    
    def read_bytes(self) -> bytes:
        return self._fs.read_bytes(self._path)
    
    def write_text(self, content: str, encoding: str = "utf-8") -> int:
        self._fs.write_text(self._path, content, encoding)
        return len(content)
    
    def write_bytes(self, content: bytes) -> int:
        self._fs.write_bytes(self._path, content)
        return len(content)
    
    def unlink(self) -> None:
        self._fs.delete(self._path)
    
    @property
    def name(self) -> str:
        return PurePosixPath(self._path).name
    
    @property
    def parent(self) -> "VirtualPath":
        return VirtualPath(str(PurePosixPath(self._path).parent), self._fs)
