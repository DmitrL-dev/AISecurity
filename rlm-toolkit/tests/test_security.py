"""Unit tests for security module."""

import pytest
from rlm_toolkit.security.virtual_fs import VirtualFS, VirtualFile, DiskQuotaExceeded
from rlm_toolkit.security.attack_detector import IndirectAttackDetector
from rlm_toolkit.security.platform_guards import create_guards


class TestVirtualFS:
    """Tests for VirtualFS."""
    
    def test_write_and_read(self):
        """Test basic file write and read."""
        fs = VirtualFS(max_size_mb=10)
        fs.write_text("/test.txt", "Hello, World!")
        content = fs.read_text("/test.txt")
        assert content == "Hello, World!"
    
    def test_write_binary(self):
        """Test binary file operations."""
        fs = VirtualFS()
        data = b"\x00\x01\x02\x03"
        fs.write_bytes("/binary.bin", data)
        result = fs.read_bytes("/binary.bin")
        assert result == data
    
    def test_file_not_found(self):
        """Test FileNotFoundError on missing file."""
        fs = VirtualFS()
        with pytest.raises(FileNotFoundError):
            fs.read_text("/nonexistent.txt")
    
    def test_quota_enforcement(self):
        """Test disk quota is enforced."""
        fs = VirtualFS(max_size_mb=1)  # 1MB limit
        
        # Try to write more than quota
        big_data = "x" * (2 * 1024 * 1024)  # 2MB
        with pytest.raises(DiskQuotaExceeded):
            fs.write_text("/big.txt", big_data)
    
    def test_delete_file(self):
        """Test file deletion."""
        fs = VirtualFS()
        fs.write_text("/temp.txt", "temp")
        assert fs.exists("/temp.txt")
        fs.delete("/temp.txt")
        assert not fs.exists("/temp.txt")
    
    def test_list_directory(self):
        """Test directory listing."""
        fs = VirtualFS()
        fs.write_text("/dir/file1.txt", "1")
        fs.write_text("/dir/file2.txt", "2")
        fs.write_text("/other/file3.txt", "3")
        
        files = fs.list_dir("/dir")
        assert len(files) == 2
    
    def test_append_mode(self):
        """Test file append mode."""
        fs = VirtualFS()
        fs.write_text("/log.txt", "line1\n")
        
        with fs.open("/log.txt", "a") as f:
            f.write("line2\n")
        
        content = fs.read_text("/log.txt")
        assert "line1" in content
        assert "line2" in content


class TestAttackDetector:
    """Tests for IndirectAttackDetector."""
    
    def test_detect_base64_import(self):
        """Test detection of base64-encoded imports."""
        detector = IndirectAttackDetector()
        # "import os" encoded
        code = "exec(__import__('base64').b64decode('aW1wb3J0IG9z'))"
        warnings = detector.analyze(code)
        assert len(warnings) > 0
    
    def test_detect_chr_chain(self):
        """Test detection of chr() concatenation."""
        detector = IndirectAttackDetector()
        # "import" via chr()
        code = "exec(chr(105)+chr(109)+chr(112)+chr(111)+chr(114)+chr(116))"
        warnings = detector.analyze(code)
        assert len(warnings) > 0
    
    def test_detect_dynamic_import(self):
        """Test detection of __import__."""
        detector = IndirectAttackDetector()
        code = "__import__('subprocess')"
        warnings = detector.analyze(code)
        assert any(w.level in ("high", "critical") for w in warnings)
    
    def test_safe_code_no_warnings(self):
        """Test that safe code produces no warnings."""
        detector = IndirectAttackDetector()
        code = """
def add(a, b):
    return a + b

result = add(1, 2)
print(result)
"""
        warnings = detector.analyze(code)
        # Should have no high/critical warnings
        critical = [w for w in warnings if w.level in ("critical", "high")]
        assert len(critical) == 0


class TestPlatformGuards:
    """Tests for PlatformGuards."""
    
    def test_create_guards(self):
        """Test guard creation doesn't fail."""
        guards = create_guards()
        assert guards is not None
    
    def test_guard_has_required_methods(self):
        """Test guards have required interface."""
        guards = create_guards()
        assert hasattr(guards, "set_memory_limit")
        assert hasattr(guards, "set_cpu_limit")
        # execute_with_limits may not exist on all platforms
        # but these core methods should exist
