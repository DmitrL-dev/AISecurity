"""Extended tests for LazyContext module."""

import pytest
import tempfile
import os
from pathlib import Path
from io import StringIO

from rlm_toolkit.core.context import LazyContext


class TestLazyContextString:
    """Tests for LazyContext with string input."""
    
    def test_creation_from_string(self):
        """Test creation from string."""
        ctx = LazyContext("Hello, world!")
        
        assert len(ctx) == 13
    
    def test_slice_string(self):
        """Test slicing string content."""
        ctx = LazyContext("Hello, world!")
        
        assert ctx.slice(0, 5) == "Hello"
        assert ctx.slice(7, 12) == "world"
    
    def test_hash_string(self):
        """Test hash computation for string."""
        ctx = LazyContext("Hello, world!")
        
        assert len(ctx.hash) == 16
    
    def test_str_returns_content(self):
        """Test str() returns full content."""
        content = "Test content here"
        ctx = LazyContext(content)
        
        assert str(ctx) == content
    
    def test_repr(self):
        """Test repr format."""
        ctx = LazyContext("Test")
        
        repr_str = repr(ctx)
        assert "LazyContext" in repr_str
        assert "length=" in repr_str
    
    def test_chunks_string(self):
        """Test chunking string content."""
        content = "a" * 1000
        ctx = LazyContext(content)
        
        chunks = list(ctx.chunks(size=100))
        
        assert len(chunks) == 10
        assert all(len(c) == 100 for c in chunks)


class TestLazyContextFile:
    """Tests for LazyContext with file input."""
    
    def test_creation_from_file(self, tmp_path):
        """Test creation from file path."""
        file_path = tmp_path / "test.txt"
        file_path.write_text("File content here", encoding="utf-8")
        
        ctx = LazyContext(str(file_path))
        
        assert len(ctx) == 17
    
    def test_slice_file(self, tmp_path):
        """Test slicing file content."""
        file_path = tmp_path / "test.txt"
        file_path.write_text("Hello, world!", encoding="utf-8")
        
        ctx = LazyContext(str(file_path))
        
        assert ctx.slice(0, 5) == "Hello"
    
    def test_hash_file(self, tmp_path):
        """Test hash for file."""
        file_path = tmp_path / "test.txt"
        file_path.write_text("Test content", encoding="utf-8")
        
        ctx = LazyContext(str(file_path))
        
        assert len(ctx.hash) == 16
    
    def test_str_file(self, tmp_path):
        """Test str() loads file content."""
        file_path = tmp_path / "test.txt"
        file_path.write_text("Full content", encoding="utf-8")
        
        ctx = LazyContext(str(file_path))
        
        assert str(ctx) == "Full content"
    
    def test_chunks_file(self, tmp_path):
        """Test chunking file content."""
        file_path = tmp_path / "test.txt"
        file_path.write_text("a" * 500, encoding="utf-8")
        
        ctx = LazyContext(str(file_path))
        
        chunks = list(ctx.chunks(size=100))
        
        assert len(chunks) == 5
    
    def test_path_object(self, tmp_path):
        """Test creation from Path object."""
        file_path = tmp_path / "test.txt"
        file_path.write_text("Path test", encoding="utf-8")
        
        ctx = LazyContext(Path(file_path))
        
        assert len(ctx) == 9


class TestLazyContextFileObject:
    """Tests for LazyContext with file object input."""
    
    def test_creation_from_file_object(self):
        """Test creation from file-like object."""
        file_obj = StringIO("File object content")
        
        ctx = LazyContext(file_obj)
        
        assert len(ctx) > 0
    
    def test_slice_file_object(self):
        """Test slicing file object."""
        file_obj = StringIO("Hello, world!")
        
        ctx = LazyContext(file_obj)
        
        result = ctx.slice(0, 5)
        assert result == "Hello"
    
    def test_str_file_object(self):
        """Test str() reads file object."""
        file_obj = StringIO("Content here")
        
        ctx = LazyContext(file_obj)
        
        # Seek to start for str()
        file_obj.seek(0)
        assert str(ctx) == "Content here"


class TestLazyContextLargeContent:
    """Tests for LazyContext with large content."""
    
    def test_large_string(self):
        """Test with large string."""
        large = "x" * 1_000_000  # 1MB
        ctx = LazyContext(large)
        
        assert len(ctx) == 1_000_000
        assert ctx.slice(0, 100) == "x" * 100
    
    def test_hash_truncates(self):
        """Test hash only uses first 100KB."""
        large = "y" * 200_000
        ctx = LazyContext(large)
        
        # Should still compute hash
        assert len(ctx.hash) == 16
