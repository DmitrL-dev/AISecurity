"""
Memory Base
===========

Abstract memory interface (ADR-005).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class MemoryEntry:
    """A single memory entry.
    
    Attributes:
        content: The stored content
        metadata: Additional metadata
        timestamp: When entry was created
        embedding: Optional vector embedding
        score: Relevance score (set during retrieval)
    """
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    embedding: Optional[List[float]] = None
    score: Optional[float] = None
    
    def __post_init__(self):
        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp)
    
    def to_dict(self) -> Dict[str, Any]:
        """Export to dictionary."""
        return {
            'content': self.content,
            'metadata': self.metadata,
            'timestamp': self.timestamp.isoformat(),
            'score': self.score,
        }


class Memory(ABC):
    """Abstract base class for memory systems.
    
    Memory systems store and retrieve context across RLM runs.
    Implementations include:
    - BufferMemory: Simple FIFO buffer
    - EpisodicMemory: EM-LLM-inspired with similarity + temporal retrieval
    
    Example:
        >>> memory = BufferMemory(max_entries=100)
        >>> memory.add("The document discusses AI safety")
        >>> relevant = memory.retrieve("What is the topic?", k=5)
    """
    
    @abstractmethod
    def add(self, content: str, metadata: Optional[Dict] = None) -> MemoryEntry:
        """Add content to memory.
        
        Args:
            content: Text content to store
            metadata: Optional metadata
        
        Returns:
            Created memory entry
        """
        pass
    
    @abstractmethod
    def retrieve(self, query: str, k: int = 5) -> List[MemoryEntry]:
        """Retrieve relevant memories.
        
        Args:
            query: Query string
            k: Number of results
        
        Returns:
            List of relevant memory entries
        """
        pass
    
    @abstractmethod
    def clear(self) -> int:
        """Clear all memories.
        
        Returns:
            Number of entries cleared
        """
        pass
    
    @property
    @abstractmethod
    def size(self) -> int:
        """Number of entries in memory."""
        pass
    
    def add_batch(self, contents: List[str], metadata: Optional[List[Dict]] = None) -> List[MemoryEntry]:
        """Add multiple entries.
        
        Args:
            contents: List of content strings
            metadata: Optional list of metadata dicts
        
        Returns:
            List of created entries
        """
        metadata = metadata or [{}] * len(contents)
        return [self.add(c, m) for c, m in zip(contents, metadata)]
    
    def to_context(self, entries: List[MemoryEntry], separator: str = "\n\n") -> str:
        """Format entries as context string.
        
        Args:
            entries: Memory entries
            separator: Entry separator
        
        Returns:
            Formatted context string
        """
        return separator.join(e.content for e in entries)
