"""Extended tests for virtual filesystem module."""

import pytest
from rlm_toolkit.security.virtual_fs import VirtualFS, VirtualFile, VirtualPath


class TestVirtualFS:
    """Extended tests for VirtualFS."""
    
    def test_creation(self):
        """Test VFS creation."""
        vfs = VirtualFS()
        
        assert vfs is not None
    
    def test_creation_with_quota(self):
        """Test VFS creation with quota."""
        vfs = VirtualFS(max_size_mb=10)
        
        # Just verify it accepts the parameter
        assert vfs is not None
    
    def test_write_text(self):
        """Test writing text file."""
        vfs = VirtualFS()
        
        vfs.write_text("/test.txt", "content")
        
        assert vfs.exists("/test.txt")
    
    def test_read_text(self):
        """Test reading text file."""
        vfs = VirtualFS()
        
        vfs.write_text("/test.txt", "hello")
        
        content = vfs.read_text("/test.txt")
        assert content == "hello"
    
    def test_write_bytes(self):
        """Test writing bytes."""
        vfs = VirtualFS()
        
        vfs.write_bytes("/data.bin", b"binary data")
        
        assert vfs.exists("/data.bin")
    
    def test_read_bytes(self):
        """Test reading bytes."""
        vfs = VirtualFS()
        
        vfs.write_bytes("/data.bin", b"hello")
        
        content = vfs.read_bytes("/data.bin")
        assert content == b"hello"
    
    def test_list_dir(self):
        """Test listing directory."""
        vfs = VirtualFS()
        
        vfs.write_text("/a.txt", "a")
        vfs.write_text("/b.txt", "b")
        
        files = vfs.list_dir("/")
        
        assert "a.txt" in files
        assert "b.txt" in files
    
    def test_delete(self):
        """Test deleting file."""
        vfs = VirtualFS()
        
        vfs.write_text("/file.txt", "data")
        vfs.delete("/file.txt")
        
        assert not vfs.exists("/file.txt")
    
    def test_cleanup(self):
        """Test cleanup all files."""
        vfs = VirtualFS()
        
        vfs.write_text("/a.txt", "a")
        vfs.write_text("/b.txt", "b")
        vfs.cleanup()
        
        assert not vfs.exists("/a.txt")
    
    def test_usage_percent(self):
        """Test usage percentage."""
        vfs = VirtualFS(max_size_mb=1)
        
        vfs.write_text("/file.txt", "x" * 1000)
        
        assert vfs.usage_percent >= 0
    
    def test_open_file(self):
        """Test open for file-like access."""
        vfs = VirtualFS()
        
        # Write using open
        with vfs.open("/test.txt", "w") as f:
            f.write("hello")
        
        # Read using open
        with vfs.open("/test.txt", "r") as f:
            content = f.read()
        
        assert content == "hello"


class TestVirtualFile:
    """Tests for VirtualFile."""
    
    def test_write_and_read(self):
        """Test file write and read."""
        vfs = VirtualFS()
        
        f = vfs.open("/test.txt", "w")
        f.write("content")
        f.close()
        
        f = vfs.open("/test.txt", "r")
        content = f.read()
        f.close()
        
        assert content == "content"
    
    def test_context_manager(self):
        """Test context manager."""
        vfs = VirtualFS()
        
        with vfs.open("/test.txt", "w") as f:
            f.write("hello")
        
        assert vfs.exists("/test.txt")


class TestVirtualPath:
    """Tests for VirtualPath."""
    
    def test_creation(self):
        """Test path creation."""
        vfs = VirtualFS()
        path = VirtualPath("/test", vfs)
        
        assert str(path) == "/test"
    
    def test_path_join(self):
        """Test path joining."""
        vfs = VirtualFS()
        path = VirtualPath("/dir", vfs)
        
        child = path / "file.txt"
        
        assert "file.txt" in str(child)
    
    def test_exists(self):
        """Test exists check."""
        vfs = VirtualFS()
        vfs.write_text("/file.txt", "content")
        
        path = VirtualPath("/file.txt", vfs)
        
        assert path.exists()
    
    def test_read_write(self):
        """Test read/write via path."""
        vfs = VirtualFS()
        path = VirtualPath("/file.txt", vfs)
        
        path.write_text("hello")
        content = path.read_text()
        
        assert content == "hello"
