"""
Unit tests for Quantum-Safe Model Vault.
"""

import pytest
from engines.quantum_safe_model_vault import (
    QuantumSafeModelVault,
    SimulatedKyber,
    SimulatedDilithium,
    KeyManager,
    PQCEncryption,
    VaultOperation,
    PQCAlgorithm,
)


class TestSimulatedKyber:
    """Tests for simulated Kyber."""

    def test_keygen(self):
        """Key generation works."""
        kyber = SimulatedKyber()

        public, private = kyber.keygen()

        assert len(public) == 32
        assert len(private) == 32

    def test_encapsulate(self):
        """Encapsulation works."""
        kyber = SimulatedKyber()
        public, _ = kyber.keygen()

        ciphertext, shared = kyber.encapsulate(public)

        assert len(ciphertext) == 32
        assert len(shared) == 32


class TestSimulatedDilithium:
    """Tests for simulated Dilithium."""

    def test_keygen(self):
        """Key generation works."""
        dilithium = SimulatedDilithium()

        public, private = dilithium.keygen()

        assert len(public) == 32
        assert len(private) == 64

    def test_sign(self):
        """Signing works."""
        dilithium = SimulatedDilithium()
        _, private = dilithium.keygen()

        signature = dilithium.sign(private, b"test message")

        assert len(signature) == 32


class TestKeyManager:
    """Tests for key manager."""

    def test_generate_kem_keypair(self):
        """KEM keypair generation works."""
        km = KeyManager()

        public = km.generate_kem_keypair("test")

        assert len(public) == 32
        assert km.get_keypair("kem_test") is not None

    def test_generate_signing_keypair(self):
        """Signing keypair generation works."""
        km = KeyManager()

        public = km.generate_signing_keypair("test")

        assert len(public) == 32
        assert km.get_keypair("sig_test") is not None


class TestQuantumSafeModelVault:
    """Integration tests."""

    def test_create_vault(self):
        """Vault creation works."""
        vault = QuantumSafeModelVault()

        enc_pub, sig_pub = vault.create_vault("model1")

        assert len(enc_pub) == 32
        assert len(sig_pub) == 32

    def test_protect_model(self):
        """Model protection works."""
        vault = QuantumSafeModelVault()
        vault.create_vault("model1")

        result = vault.protect_model("model1", b"model weights data")

        assert result.success is True
        assert result.operation == VaultOperation.ENCRYPT

    def test_verify_protection(self):
        """Protection verification works."""
        vault = QuantumSafeModelVault()
        vault.create_vault("model1")

        result = vault.verify_protection("model1", "abc123")

        assert result.success is True
        assert result.operation == VaultOperation.VERIFY

    def test_verify_missing_vault(self):
        """Missing vault returns failure."""
        vault = QuantumSafeModelVault()

        result = vault.verify_protection("missing", "abc")

        assert result.success is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
