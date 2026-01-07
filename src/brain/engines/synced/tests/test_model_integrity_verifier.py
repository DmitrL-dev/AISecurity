"""
Unit tests for Model Integrity Verifier

Tests format safety, hash verification, suspicious content detection.

Generated: 2026-01-07
"""

import pytest
import tempfile
import os
from pathlib import Path
from model_integrity_verifier import (
    ModelIntegrityVerifier,
    ModelFormat,
    RiskLevel,
    verify
)


class TestModelIntegrityVerifier:
    """Tests for ModelIntegrityVerifier."""

    @pytest.fixture
    def verifier(self):
        return ModelIntegrityVerifier()

    @pytest.fixture
    def temp_dir(self):
        with tempfile.TemporaryDirectory() as d:
            yield d

    # =========================================================================
    # Format Safety Tests
    # =========================================================================

    def test_safetensors_is_safe(self, verifier, temp_dir):
        """Safetensors format should be safe."""
        path = Path(temp_dir) / "model.safetensors"
        path.write_bytes(b"dummy content")
        result = verifier.verify_file(str(path))
        assert any(c.check_name == "format_extension" and c.passed 
                   for c in result.checks)

    def test_onnx_is_low_risk(self, verifier, temp_dir):
        """ONNX format should be low risk."""
        path = Path(temp_dir) / "model.onnx"
        path.write_bytes(b"dummy content")
        result = verifier.verify_file(str(path))
        assert result.model_format == ModelFormat.ONNX

    def test_pickle_is_critical(self, verifier, temp_dir):
        """Pickle format should be critical risk."""
        path = Path(temp_dir) / "model.pkl"
        path.write_bytes(b"\x80\x04\x95test")  # Pickle header
        result = verifier.verify_file(str(path))
        assert result.overall_risk in [RiskLevel.HIGH, RiskLevel.CRITICAL]

    def test_pt_is_high_risk(self, verifier, temp_dir):
        """PyTorch .pt format should be high risk."""
        path = Path(temp_dir) / "model.pt"
        path.write_bytes(b"PK\x03\x04dummy")  # ZIP header
        result = verifier.verify_file(str(path))
        assert result.model_format == ModelFormat.TORCH

    def test_h5_is_medium_risk(self, verifier, temp_dir):
        """HDF5 .h5 format should be medium risk."""
        path = Path(temp_dir) / "model.h5"
        path.write_bytes(b"\x89HDFdummy")  # HDF5 header
        result = verifier.verify_file(str(path))
        assert result.model_format == ModelFormat.TENSORFLOW

    def test_unknown_format(self, verifier, temp_dir):
        """Unknown format should be flagged."""
        path = Path(temp_dir) / "model.xyz"
        path.write_bytes(b"unknown format")
        result = verifier.verify_file(str(path))
        assert result.model_format == ModelFormat.UNKNOWN

    # =========================================================================
    # Magic Bytes Tests
    # =========================================================================

    def test_pickle_magic_bytes(self, verifier, temp_dir):
        """Detect pickle magic bytes."""
        path = Path(temp_dir) / "sneaky.bin"
        path.write_bytes(b"\x80\x04\x95pickle_payload")
        result = verifier.verify_file(str(path))
        # Should detect pickle even with wrong extension
        assert any(c.check_name == "magic_bytes" and not c.passed 
                   for c in result.checks)

    def test_zip_magic_bytes(self, verifier, temp_dir):
        """Detect ZIP/PyTorch magic bytes."""
        path = Path(temp_dir) / "model.bin"
        path.write_bytes(b"PK\x03\x04torch_model")
        result = verifier.verify_file(str(path))
        assert result.detected = True

    def test_no_suspicious_magic(self, verifier, temp_dir):
        """Clean magic bytes should pass."""
        path = Path(temp_dir) / "clean.safetensors"
        path.write_bytes(b"clean safe content here")
        result = verifier.verify_file(str(path))
        assert any(c.check_name == "magic_bytes" and c.passed 
                   for c in result.checks)

    # =========================================================================
    # Hash Verification Tests
    # =========================================================================

    def test_hash_match(self, verifier, temp_dir):
        """Matching hash should pass."""
        path = Path(temp_dir) / "model.safetensors"
        content = b"test model content"
        path.write_bytes(content)
        
        # Pre-compute hash
        import hashlib
        expected = "sha256:" + hashlib.sha256(content).hexdigest()
        
        result = verifier.verify_file(str(path), expected_hash=expected)
        assert any(c.check_name == "hash_verification" and c.passed 
                   for c in result.checks)

    def test_hash_mismatch(self, verifier, temp_dir):
        """Mismatched hash should fail."""
        path = Path(temp_dir) / "model.safetensors"
        path.write_bytes(b"original content")
        
        result = verifier.verify_file(str(path), expected_hash="sha256:wronghash")
        assert any(c.check_name == "hash_verification" and not c.passed 
                   for c in result.checks)

    def test_hash_computed(self, verifier, temp_dir):
        """Hash should be computed and returned."""
        path = Path(temp_dir) / "model.safetensors"
        path.write_bytes(b"test content")
        
        result = verifier.verify_file(str(path))
        assert result.computed_hash is not None
        assert result.computed_hash.startswith("sha256:")

    # =========================================================================
    # Suspicious Content Tests
    # =========================================================================

    def test_exec_in_model(self, verifier, temp_dir):
        """Detect exec() in model file."""
        path = Path(temp_dir) / "model.pt"
        path.write_bytes(b"PK\x03\x04exec(payload)")
        result = verifier.verify_file(str(path))
        assert any(c.check_name == "suspicious_content" and not c.passed 
                   for c in result.checks)

    def test_eval_in_model(self, verifier, temp_dir):
        """Detect eval() in model file."""
        path = Path(temp_dir) / "model.pkl"
        path.write_bytes(b"\x80\x04\x95 eval(code)")
        result = verifier.verify_file(str(path))
        assert not result.is_verified

    def test_os_system_in_model(self, verifier, temp_dir):
        """Detect os.system in model file."""
        path = Path(temp_dir) / "model.pt"
        path.write_bytes(b"PK\x03\x04 import os; os.system('rm -rf /')")
        result = verifier.verify_file(str(path))
        assert result.overall_risk in [RiskLevel.HIGH, RiskLevel.CRITICAL]

    def test_reduce_method(self, verifier, temp_dir):
        """Detect __reduce__ in model file."""
        path = Path(temp_dir) / "model.pkl"
        path.write_bytes(b"\x80\x04\x95 __reduce__ exploit")
        result = verifier.verify_file(str(path))
        assert not result.is_verified

    def test_socket_in_model(self, verifier, temp_dir):
        """Detect socket operations in model."""
        path = Path(temp_dir) / "model.pt"
        path.write_bytes(b"PK\x03\x04 import socket; socket.connect()")
        result = verifier.verify_file(str(path))
        assert any("socket" in str(c.details).lower() 
                   for c in result.checks if not c.passed)

    # =========================================================================
    # File Not Found Tests
    # =========================================================================

    def test_file_not_found(self, verifier):
        """Non-existent file should return error."""
        result = verifier.verify_file("/nonexistent/model.pt")
        assert not result.is_verified
        assert result.overall_risk == RiskLevel.CRITICAL
        assert any("not found" in c.details.lower() for c in result.checks)

    # =========================================================================
    # Recommendations Tests
    # =========================================================================

    def test_recommendations_for_pickle(self, verifier, temp_dir):
        """Pickle files should get safetensors recommendation."""
        path = Path(temp_dir) / "model.pkl"
        path.write_bytes(b"\x80\x04\x95content")
        result = verifier.verify_file(str(path))
        assert any("safetensors" in r.lower() for r in result.recommendations)

    def test_recommendations_for_torch(self, verifier, temp_dir):
        """Torch files should get weights_only recommendation."""
        path = Path(temp_dir) / "model.pt"
        path.write_bytes(b"PK\x03\x04content")
        result = verifier.verify_file(str(path))
        assert any("weights_only" in r.lower() for r in result.recommendations)

    # =========================================================================
    # Overall Risk Tests
    # =========================================================================

    def test_safe_model_is_verified(self, verifier, temp_dir):
        """Safe model should be verified."""
        path = Path(temp_dir) / "model.safetensors"
        path.write_bytes(b"safe tensor content")
        result = verifier.verify_file(str(path))
        # Should be verified if all checks pass
        assert result.overall_risk in [RiskLevel.SAFE, RiskLevel.LOW]

    def test_critical_model_not_verified(self, verifier, temp_dir):
        """Critical risk model should not be verified."""
        path = Path(temp_dir) / "model.pkl"
        path.write_bytes(b"\x80\x04\x95 exec(evil_code)")
        result = verifier.verify_file(str(path))
        assert not result.is_verified
        assert result.overall_risk == RiskLevel.CRITICAL


# Run with: pytest test_model_integrity_verifier.py -v
