"""
Unit tests for Secure Model Loader.
"""

import hashlib
import pytest
from engines.secure_model_loader import (
    SecureModelLoader,
    IntegrityVerifier,
    SignatureVerifier,
    MalwareScanner,
    ModelManifest,
    LoadStatus,
    ThreatType,
)


class TestIntegrityVerifier:
    """Tests for integrity verifier."""

    def test_verify_correct_hash(self):
        """Correct hash verifies."""
        verifier = IntegrityVerifier()
        data = b"test data"
        expected = hashlib.sha256(data).hexdigest()

        result = verifier.verify_hash(data, expected)

        assert result is True

    def test_verify_wrong_hash(self):
        """Wrong hash fails."""
        verifier = IntegrityVerifier()

        result = verifier.verify_hash(b"data", "wronghash")

        assert result is False


class TestSignatureVerifier:
    """Tests for signature verifier."""

    def test_trusted_publisher(self):
        """Trusted publisher verified."""
        verifier = SignatureVerifier()
        manifest = ModelManifest("m1", "1.0", "hash", "sig", "sentinel")

        result = verifier.verify(manifest)

        assert result is True

    def test_untrusted_publisher(self):
        """Untrusted publisher fails."""
        verifier = SignatureVerifier()
        manifest = ModelManifest("m1", "1.0", "hash", "sig", "untrusted")

        result = verifier.verify(manifest)

        assert result is False


class TestMalwareScanner:
    """Tests for malware scanner."""

    def test_clean_data_passes(self):
        """Clean data passes."""
        scanner = MalwareScanner()

        threats = scanner.scan(b"clean model weights")

        assert len(threats) == 0

    def test_malicious_detected(self):
        """Malicious code detected."""
        scanner = MalwareScanner()

        threats = scanner.scan(b"model with eval(code)")

        assert ThreatType.MALICIOUS_CODE in threats


class TestSecureModelLoader:
    """Integration tests."""

    def test_load_valid_model(self):
        """Valid model loads."""
        loader = SecureModelLoader()
        data = b"valid model data"
        manifest = ModelManifest(
            "model1",
            "1.0",
            hashlib.sha256(data).hexdigest(),
            "signature",
            "sentinel",
        )

        result = loader.load(data, manifest)

        assert result.status == LoadStatus.SUCCESS
        assert result.verified is True

    def test_tampered_model_fails(self):
        """Tampered model fails."""
        loader = SecureModelLoader()
        manifest = ModelManifest("m1", "1.0", "wronghash", "sig", "sentinel")

        result = loader.load(b"data", manifest)

        assert ThreatType.TAMPERED in result.threats

    def test_malicious_quarantined(self):
        """Malicious model quarantined."""
        loader = SecureModelLoader()
        data = b"eval(malicious_code)"
        manifest = ModelManifest(
            "m1",
            "1.0",
            hashlib.sha256(data).hexdigest(),
            "sig",
            "sentinel",
        )

        result = loader.load(data, manifest)

        assert result.status == LoadStatus.QUARANTINED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
