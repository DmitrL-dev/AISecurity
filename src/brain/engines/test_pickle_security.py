"""
Tests for PickleSecurityEngine.

Validates ML model supply chain attack detection.
"""

import pickle
import pytest
from unittest.mock import patch, MagicMock

from src.brain.engines.pickle_security import (
    PickleSecurityEngine,
    PyTorchModelScanner,
    PickleAnalysisResult,
    PickleSeverity,
    PickleOpcodeScanner,
    UNSAFE_MODULES,
    DANGEROUS_CALLS,
    ML_ALLOWLIST,
)
from src.brain.engines.base_engine import Severity


class TestPickleSeverity:
    """Test PickleSeverity enum."""
    
    def test_severity_ordering(self):
        """Test severity levels are properly ordered."""
        assert PickleSeverity.LIKELY_SAFE.value < PickleSeverity.SUSPICIOUS.value
        assert PickleSeverity.SUSPICIOUS.value < PickleSeverity.LIKELY_UNSAFE.value
        assert PickleSeverity.LIKELY_UNSAFE.value < PickleSeverity.OVERTLY_MALICIOUS.value
    
    def test_to_sentinel_severity(self):
        """Test mapping to SENTINEL severity."""
        assert PickleSeverity.LIKELY_SAFE.to_sentinel_severity() == Severity.INFO
        assert PickleSeverity.SUSPICIOUS.to_sentinel_severity() == Severity.MEDIUM
        assert PickleSeverity.OVERTLY_MALICIOUS.to_sentinel_severity() == Severity.CRITICAL


class TestUnsafeModules:
    """Test UNSAFE_MODULES constant."""
    
    def test_contains_os(self):
        """Test os module is blocked."""
        assert "os" in UNSAFE_MODULES
    
    def test_contains_subprocess(self):
        """Test subprocess module is blocked."""
        assert "subprocess" in UNSAFE_MODULES
    
    def test_contains_builtins(self):
        """Test builtins are blocked."""
        assert "builtins" in UNSAFE_MODULES
        assert "__builtins__" in UNSAFE_MODULES
        assert "__builtin__" in UNSAFE_MODULES
    
    def test_contains_torch_hub(self):
        """Test torch.hub is blocked (can load remote code)."""
        assert "torch.hub" in UNSAFE_MODULES


class TestMLAllowlist:
    """Test ML_ALLOWLIST constant."""
    
    def test_numpy_allowed(self):
        """Test numpy types are allowed."""
        assert "numpy" in ML_ALLOWLIST
        assert "ndarray" in ML_ALLOWLIST["numpy"]
        assert "dtype" in ML_ALLOWLIST["numpy"]
    
    def test_torch_allowed(self):
        """Test torch types are allowed."""
        assert "torch" in ML_ALLOWLIST
        assert "Tensor" in ML_ALLOWLIST["torch"]
        assert "FloatStorage" in ML_ALLOWLIST["torch"]
    
    def test_collections_allowed(self):
        """Test collections are allowed."""
        assert "collections" in ML_ALLOWLIST
        assert "OrderedDict" in ML_ALLOWLIST["collections"]


class TestPickleOpcodeScanner:
    """Test PickleOpcodeScanner class."""
    
    def setup_method(self):
        self.scanner = PickleOpcodeScanner()
    
    def test_scan_safe_pickle(self):
        """Test scanning safe pickle data."""
        safe_data = pickle.dumps({"key": "value", "number": 42})
        result = self.scanner.scan(safe_data)
        
        assert result.is_safe
        assert result.severity == PickleSeverity.LIKELY_SAFE
        assert len(result.dangerous_imports) == 0
        assert len(result.dangerous_calls) == 0
    
    def test_scan_list_pickle(self):
        """Test scanning list pickle."""
        list_data = pickle.dumps([1, 2, 3, "test"])
        result = self.scanner.scan(list_data)
        
        assert result.is_safe
        assert result.severity == PickleSeverity.LIKELY_SAFE
    
    def test_detect_os_system(self):
        """Test detection of os.system attack."""
        # Craft malicious pickle using __reduce__
        class Malicious:
            def __reduce__(self):
                import os
                return (os.system, ("echo pwned",))
        
        malicious_data = pickle.dumps(Malicious())
        result = self.scanner.scan(malicious_data)
        
        # Should detect dangerous import
        assert not result.is_safe
        assert result.severity.value >= PickleSeverity.LIKELY_UNSAFE.value
    
    def test_detect_subprocess_call(self):
        """Test detection of subprocess.call attack."""
        class SubprocessAttack:
            def __reduce__(self):
                import subprocess
                return (subprocess.call, (["id"],))
        
        malicious_data = pickle.dumps(SubprocessAttack())
        result = self.scanner.scan(malicious_data)
        
        assert not result.is_safe
        assert "subprocess" in str(result.dangerous_imports) or len(result.findings) > 0
    
    def test_detect_eval_call(self):
        """Test detection of eval call."""
        class EvalAttack:
            def __reduce__(self):
                return (eval, ("__import__('os').system('id')",))
        
        malicious_data = pickle.dumps(EvalAttack())
        result = self.scanner.scan(malicious_data)
        
        # Eval should be flagged as dangerous call
        assert not result.is_safe


class TestPickleSecurityEngine:
    """Test PickleSecurityEngine class."""
    
    def setup_method(self):
        self.engine = PickleSecurityEngine()
    
    def test_engine_name(self):
        """Test engine name property."""
        assert self.engine.name == "pickle_security"
    
    def test_engine_version(self):
        """Test engine version property."""
        assert self.engine.version == "1.0.0"
    
    def test_analyze_safe_bytes(self):
        """Test analyzing safe pickle bytes."""
        safe_data = pickle.dumps({"test": 123, "list": [1, 2, 3]})
        result = self.engine.analyze_bytes(safe_data)
        
        assert result.is_safe
        assert result.severity == PickleSeverity.LIKELY_SAFE
    
    def test_analyze_malicious_bytes(self):
        """Test analyzing malicious pickle bytes."""
        class Malicious:
            def __reduce__(self):
                import os
                return (os.system, ("id",))
        
        malicious_data = pickle.dumps(Malicious())
        result = self.engine.analyze_bytes(malicious_data)
        
        assert not result.is_safe
        assert result.severity.value >= PickleSeverity.LIKELY_UNSAFE.value
    
    def test_detect_text_patterns(self):
        """Test text pattern detection."""
        text_with_os = "import os; os.system('malicious')"
        result = self.engine.detect(text_with_os)
        
        assert result.detected
        assert result.severity == Severity.HIGH
    
    def test_detect_safe_text(self):
        """Test safe text detection."""
        safe_text = "This is a normal string with no threats"
        result = self.engine.detect(safe_text)
        
        assert not result.detected
        assert result.severity == Severity.INFO
    
    def test_is_import_safe_numpy(self):
        """Test numpy imports are safe."""
        assert self.engine.is_import_safe("numpy", "ndarray")
        assert self.engine.is_import_safe("numpy", "dtype")
    
    def test_is_import_safe_torch(self):
        """Test torch imports are safe."""
        assert self.engine.is_import_safe("torch", "Tensor")
        assert self.engine.is_import_safe("torch", "FloatStorage")
    
    def test_is_import_unsafe_os(self):
        """Test os imports are unsafe."""
        assert not self.engine.is_import_safe("os", "system")
        assert not self.engine.is_import_safe("os", "popen")
    
    def test_is_import_unsafe_subprocess(self):
        """Test subprocess imports are unsafe."""
        assert not self.engine.is_import_safe("subprocess", "call")
        assert not self.engine.is_import_safe("subprocess", "Popen")
    
    def test_invalid_pickle_detection(self):
        """Test detection of invalid pickle format."""
        invalid_data = b"this is not a pickle file"
        result = self.engine.analyze_bytes(invalid_data)
        
        # Invalid format should be suspicious
        assert result.severity == PickleSeverity.SUSPICIOUS
    
    def test_health_check(self):
        """Test engine health check."""
        assert self.engine.health_check()


class TestPyTorchModelScanner:
    """Test PyTorchModelScanner class."""
    
    def setup_method(self):
        self.scanner = PyTorchModelScanner()
    
    def test_supported_extensions(self):
        """Test supported file extensions."""
        assert ".pt" in self.scanner.SUPPORTED_EXTENSIONS
        assert ".pth" in self.scanner.SUPPORTED_EXTENSIONS
        assert ".bin" in self.scanner.SUPPORTED_EXTENSIONS
        assert ".ckpt" in self.scanner.SUPPORTED_EXTENSIONS
    
    def test_unsupported_extension(self):
        """Test unsupported file extension."""
        result = self.scanner.scan("model.txt")
        
        assert result.is_safe
        assert "Unsupported extension" in result.findings[0]
    
    def test_file_not_found(self):
        """Test handling of non-existent file."""
        result = self.scanner.scan("/nonexistent/model.pt")
        
        assert not result.is_safe
        assert "File not found" in result.findings[0]


class TestPickleAnalysisResult:
    """Test PickleAnalysisResult dataclass."""
    
    def test_to_dict_basic(self):
        """Test to_dict conversion."""
        result = PickleAnalysisResult(
            severity=PickleSeverity.LIKELY_SAFE,
            is_safe=True,
            findings=["No issues"],
        )
        
        d = result.to_dict()
        
        assert d["severity"] == "LIKELY_SAFE"
        assert d["is_safe"] is True
        assert "No issues" in d["findings"]
    
    def test_to_dict_with_threats(self):
        """Test to_dict with detected threats."""
        result = PickleAnalysisResult(
            severity=PickleSeverity.OVERTLY_MALICIOUS,
            is_safe=False,
            findings=["Detected os.system call"],
            dangerous_imports=["os.system"],
            dangerous_calls=["eval"],
        )
        
        d = result.to_dict()
        
        assert d["severity"] == "OVERTLY_MALICIOUS"
        assert d["is_safe"] is False
        assert "os.system" in d["dangerous_imports"]
        assert "eval" in d["dangerous_calls"]


class TestIntegration:
    """Integration tests."""
    
    def test_complex_safe_pickle(self):
        """Test complex but safe pickle structure."""
        engine = PickleSecurityEngine()
        
        # Complex nested structure
        data = {
            "model_state": {
                "layers": [1.0, 2.0, 3.0],
                "config": {"hidden_size": 768},
            },
            "metadata": {
                "version": "1.0",
                "created": "2024-01-01",
            },
        }
        
        pickled = pickle.dumps(data)
        result = engine.analyze_bytes(pickled)
        
        assert result.is_safe
        assert result.severity == PickleSeverity.LIKELY_SAFE
    
    def test_nested_attack_detection(self):
        """Test detection of nested malicious pickle."""
        engine = PickleSecurityEngine()
        
        # Wrap malicious class in nested structure
        class NestedAttack:
            def __reduce__(self):
                import os
                return (os.system, ("whoami",))
        
        data = {
            "innocent": {"key": "value"},
            "payload": NestedAttack(),
        }
        
        pickled = pickle.dumps(data)
        result = engine.analyze_bytes(pickled)
        
        # Should still detect the attack
        assert not result.is_safe


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
