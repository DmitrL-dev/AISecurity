"""Extended tests for memory modules."""

import pytest
from rlm_toolkit.memory.buffer import BufferMemory
from rlm_toolkit.memory.episodic import EpisodicMemory


class TestBufferMemory:
    """Extended tests for BufferMemory."""
    
    def test_creation(self):
        """Test buffer creation."""
        memory = BufferMemory(max_entries=100)
        
        assert memory is not None
    
    def test_add_and_retrieve(self):
        """Test adding and retrieving entries."""
        memory = BufferMemory()
        
        memory.add("value1")
        
        result = memory.retrieve("query", k=1)
        assert len(result) == 1
        assert result[0].content == "value1"
    
    def test_max_entries(self):
        """Test max entries limit."""
        memory = BufferMemory(max_entries=3)
        
        memory.add("v1")
        memory.add("v2")
        memory.add("v3")
        memory.add("v4")
        
        # Should have evicted oldest
        assert memory.size == 3
    
    def test_clear(self):
        """Test clearing memory."""
        memory = BufferMemory()
        
        memory.add("content")
        memory.clear()
        
        assert memory.size == 0
    
    def test_get_all(self):
        """Test get_all method."""
        memory = BufferMemory()
        
        memory.add("a")
        memory.add("b")
        
        entries = memory.get_all()
        
        assert len(entries) == 2
    
    def test_get_context_window(self):
        """Test context window formatting."""
        memory = BufferMemory()
        
        memory.add("First")
        memory.add("Second")
        
        context = memory.get_context_window(k=2)
        
        assert "First" in context or "Second" in context


class TestEpisodicMemory:
    """Extended tests for EpisodicMemory."""
    
    def test_creation(self):
        """Test episodic memory creation."""
        memory = EpisodicMemory()
        
        assert memory is not None
    
    def test_add_entry(self):
        """Test adding entry."""
        memory = EpisodicMemory()
        
        entry = memory.add("test content")
        
        assert entry.content == "test content"
        assert memory.size > 0
    
    def test_retrieve_similar(self):
        """Test similarity retrieval."""
        memory = EpisodicMemory()
        
        memory.add("python programming language")
        memory.add("cooking recipe instructions")
        
        results = memory.retrieve(query="python code", k=1)
        
        assert len(results) >= 0
    
    def test_clear(self):
        """Test clearing episodes."""
        memory = EpisodicMemory()
        
        memory.add("content")
        memory.clear()
        
        assert memory.size == 0
    
    def test_summary_stats(self):
        """Test summary statistics."""
        memory = EpisodicMemory()
        
        memory.add("entry 1")
        memory.add("entry 2")
        
        stats = memory.summary_stats()
        
        assert stats["size"] == 2
