"""
Unit tests for Homomorphic Encryption Engine.
"""

import pytest
import numpy as np
from engines.homomorphic_engine import (
    HomomorphicEngine,
    HEKeyGenerator,
    HEEncryptor,
    HEDecryptor,
    HEEvaluator,
    EncryptedPromptAnalyzer,
    HEScheme,
    SecurityLevel,
    EncryptedVector,
)


class TestHEKeyGenerator:
    """Tests for HEKeyGenerator."""

    def test_generate_context(self):
        """Test context generation."""
        context = HEKeyGenerator.generate_context(
            scheme=HEScheme.CKKS,
            security_level=SecurityLevel.BITS_128
        )

        assert context.context_id is not None
        assert context.public_key is not None
        assert context.secret_key is not None
        assert context.relin_keys is not None

    def test_export_public_context(self):
        """Test public context export."""
        context = HEKeyGenerator.generate_context()
        public_context = HEKeyGenerator.export_public_context(context)

        assert public_context.public_key is not None
        assert public_context.secret_key is None  # Should be removed


class TestHEEncryptorDecryptor:
    """Tests for encryption and decryption."""

    def setup_method(self):
        self.context = HEKeyGenerator.generate_context()
        self.encryptor = HEEncryptor(self.context)
        self.decryptor = HEDecryptor(self.context)

    def test_encrypt_vector(self):
        """Test vector encryption."""
        plaintext = np.array([1.0, 2.0, 3.0, 4.0])
        encrypted = self.encryptor.encrypt_vector(plaintext)

        assert encrypted.id is not None
        assert encrypted.shape == plaintext.shape
        assert len(encrypted.ciphertext) > len(plaintext.tobytes())

    def test_decrypt_vector(self):
        """Test vector decryption."""
        plaintext = np.array([1.0, 2.0, 3.0, 4.0])
        encrypted = self.encryptor.encrypt_vector(plaintext)
        decrypted = self.decryptor.decrypt_vector(encrypted)

        assert decrypted.shape == plaintext.shape
        np.testing.assert_array_almost_equal(decrypted, plaintext)

    def test_encrypt_embedding(self):
        """Test embedding encryption."""
        embedding = np.random.randn(768)
        encrypted = self.encryptor.encrypt_embedding(embedding)

        assert encrypted.shape == (768,)


class TestHEEvaluator:
    """Tests for homomorphic operations."""

    def setup_method(self):
        self.context = HEKeyGenerator.generate_context()
        self.encryptor = HEEncryptor(self.context)
        self.evaluator = HEEvaluator(self.context)

    def test_add(self):
        """Test homomorphic addition."""
        a = self.encryptor.encrypt_vector(np.array([1.0, 2.0]))
        b = self.encryptor.encrypt_vector(np.array([3.0, 4.0]))

        result = self.evaluator.add(a, b)

        assert result.id is not None
        assert result.shape == a.shape

    def test_multiply(self):
        """Test homomorphic multiplication."""
        a = self.encryptor.encrypt_vector(np.array([1.0, 2.0]))
        b = self.encryptor.encrypt_vector(np.array([3.0, 4.0]))

        result = self.evaluator.multiply(a, b)

        assert result.id is not None
        assert result.level > a.level

    def test_add_plain(self):
        """Test plaintext addition."""
        encrypted = self.encryptor.encrypt_vector(np.array([1.0, 2.0]))
        plain = np.array([10.0, 20.0])

        result = self.evaluator.add_plain(encrypted, plain)

        assert result.shape == encrypted.shape

    def test_dot_product(self):
        """Test encrypted dot product."""
        a = self.encryptor.encrypt_vector(np.array([1.0, 2.0, 3.0]))
        b = self.encryptor.encrypt_vector(np.array([4.0, 5.0, 6.0]))

        result = self.evaluator.dot_product(a, b)

        assert result.shape == (1,)


class TestEncryptedPromptAnalyzer:
    """Tests for EncryptedPromptAnalyzer."""

    def setup_method(self):
        self.context = HEKeyGenerator.generate_context()
        self.encryptor = HEEncryptor(self.context)
        self.analyzer = EncryptedPromptAnalyzer(self.context)

    def test_analyze_encrypted_embedding(self):
        """Test encrypted analysis."""
        embedding = self.encryptor.encrypt_vector(np.random.randn(128))
        threats = [
            self.encryptor.encrypt_vector(np.random.randn(128))
            for _ in range(3)
        ]

        result = self.analyzer.analyze_encrypted_embedding(embedding, threats)

        assert result.result_id is not None
        assert result.computation_time_ms >= 0
        assert len(result.operations_performed) > 0

    def test_privacy_preserving_classification(self):
        """Test encrypted classification."""
        embedding = self.encryptor.encrypt_vector(np.random.randn(64))
        weights = self.encryptor.encrypt_vector(np.random.randn(64))
        bias = self.encryptor.encrypt_vector(np.array([0.5]))

        result = self.analyzer.privacy_preserving_classification(
            embedding, weights, bias
        )

        assert result.id is not None


class TestHomomorphicEngine:
    """Tests for main HomomorphicEngine."""

    def setup_method(self):
        self.engine = HomomorphicEngine()

    def test_setup(self):
        """Test engine setup."""
        self.engine.setup(
            scheme=HEScheme.CKKS,
            security_level=SecurityLevel.BITS_128
        )

        assert self.engine.context is not None
        assert self.engine.encryptor is not None
        assert self.engine.decryptor is not None

    def test_encrypt_decrypt(self):
        """Test encrypt/decrypt cycle."""
        self.engine.setup()

        original = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        encrypted = self.engine.encrypt(original)
        decrypted = self.engine.decrypt(encrypted)

        np.testing.assert_array_almost_equal(decrypted, original)

    def test_analyze_encrypted(self):
        """Test privacy-preserving analysis."""
        self.engine.setup()

        prompt = self.engine.encrypt(np.random.randn(256))
        threats = [
            self.engine.encrypt(np.random.randn(256))
            for _ in range(2)
        ]

        result = self.engine.analyze_encrypted(prompt, threats)

        assert result.result_id is not None
        assert result.noise_budget_remaining > 0

    def test_get_public_context(self):
        """Test public context export."""
        self.engine.setup()

        public = self.engine.get_public_context()

        assert public.secret_key is None
        assert public.public_key is not None

    def test_get_stats(self):
        """Test statistics."""
        self.engine.setup()

        # Do some operations
        self.engine.encrypt(np.array([1.0, 2.0]))
        self.engine.encrypt(np.array([3.0, 4.0]))

        stats = self.engine.get_stats()

        assert stats["initialized"] == True
        assert stats["total_operations"] == 2


class TestIntegration:
    """Integration tests."""

    def test_full_privacy_preserving_pipeline(self):
        """Test complete privacy-preserving analysis."""
        engine = HomomorphicEngine()
        engine.setup(scheme=HEScheme.CKKS)

        # Simulate prompt embedding
        prompt_embedding = np.random.randn(512)

        # Encrypt
        encrypted_prompt = engine.encrypt(prompt_embedding)

        # Create encrypted threat signatures
        threat_signatures = [
            engine.encrypt(np.random.randn(512))
            for _ in range(5)
        ]

        # Analyze (all encrypted)
        result = engine.analyze_encrypted(encrypted_prompt, threat_signatures)

        # Get stats
        stats = engine.get_stats()

        assert result is not None
        assert stats["total_operations"] > 0

    def test_multiple_schemes(self):
        """Test different HE schemes."""
        for scheme in [HEScheme.CKKS, HEScheme.BFV, HEScheme.BGV]:
            engine = HomomorphicEngine()
            engine.setup(scheme=scheme)

            data = np.array([1.0, 2.0, 3.0])
            encrypted = engine.encrypt(data)
            decrypted = engine.decrypt(encrypted)

            assert decrypted.shape == data.shape


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
