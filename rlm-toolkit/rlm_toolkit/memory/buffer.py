"""
Buffer Memory
=============

Simple FIFO buffer memory implementation.
"""

from __future__ import annotations

from collections import deque
from typing import Any, Deque, Dict, List, Optional

from rlm_toolkit.memory.base import Memory, MemoryEntry


class BufferMemory(Memory):
    """Simple FIFO buffer memory.
    
    Stores entries in a fixed-size buffer. When full, oldest entries
    are removed. Retrieval returns most recent entries.
    
    Example:
        >>> memory = BufferMemory(max_entries=10)
        >>> memory.add("First message")
        >>> memory.add("Second message")
        >>> recent = memory.retrieve("anything", k=2)
    
    Attributes:
        max_entries: Maximum buffer size
    """
    
    def __init__(self, max_entries: int = 100):
        """Initialize buffer memory.
        
        Args:
            max_entries: Maximum number of entries to keep
        """
        self.max_entries = max_entries
        self._buffer: Deque[MemoryEntry] = deque(maxlen=max_entries)
    
    def add(self, content: str, metadata: Optional[Dict] = None) -> MemoryEntry:
        """Add content to buffer."""
        entry = MemoryEntry(
            content=content,
            metadata=metadata or {},
        )
        self._buffer.append(entry)
        return entry
    
    def retrieve(self, query: str, k: int = 5) -> List[MemoryEntry]:
        """Retrieve most recent k entries.
        
        Note: BufferMemory ignores query and returns most recent.
        For query-based retrieval, use EpisodicMemory.
        """
        # Return most recent k entries (reversed for recency order)
        entries = list(self._buffer)[-k:]
        entries.reverse()
        return entries
    
    def clear(self) -> int:
        """Clear buffer."""
        count = len(self._buffer)
        self._buffer.clear()
        return count
    
    @property
    def size(self) -> int:
        return len(self._buffer)
    
    def get_all(self) -> List[MemoryEntry]:
        """Get all entries in order."""
        return list(self._buffer)
    
    def get_context_window(self, k: int = 10) -> str:
        """Get formatted context from recent entries."""
        entries = self.retrieve("", k)
        entries.reverse()  # Chronological order
        return self.to_context(entries)
