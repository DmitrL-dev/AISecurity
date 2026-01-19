"""Tests for AES-256-GCM Encryption."""

import pytest
import os

from rlm_toolkit.memory.crypto import (
    SecureEncryption,
    create_encryption,
    is_aes_available,
)


class TestSecureEncryption:
    """Tests for AES-256-GCM encryption."""

    @pytest.fixture
    def crypto(self):
        """Create encryption instance."""
        if not is_aes_available():
            pytest.skip("cryptography not installed")
        key = os.urandom(32)
        return SecureEncryption(key)

    def test_encrypt_decrypt(self, crypto):
        """Test basic encrypt/decrypt."""
        plaintext = b"Hello, World!"

        encrypted = crypto.encrypt(plaintext)
        decrypted = crypto.decrypt(encrypted)

        assert decrypted == plaintext

    def test_encrypted_differs(self, crypto):
        """Test that encrypted data differs from plaintext."""
        plaintext = b"Secret message"
        encrypted = crypto.encrypt(plaintext)

        assert encrypted != plaintext
        assert len(encrypted) >= len(plaintext)

    def test_unique_ciphertext(self, crypto):
        """Test that same plaintext produces different ciphertext (random nonce)."""
        plaintext = b"Same message"

        enc1 = crypto.encrypt(plaintext)
        enc2 = crypto.encrypt(plaintext)

        assert enc1 != enc2  # Different nonces

    def test_encrypt_string(self, crypto):
        """Test string encryption."""
        plaintext = "Hello, World!"

        encrypted = crypto.encrypt_string(plaintext)
        decrypted = crypto.decrypt_string(encrypted)

        assert decrypted == plaintext

    def test_tamper_detection(self, crypto):
        """Test that tampering is detected."""
        plaintext = b"Important data"
        encrypted = crypto.encrypt(plaintext)

        # Tamper with the ciphertext
        tampered = encrypted[:-1] + bytes([encrypted[-1] ^ 0xFF])

        with pytest.raises(ValueError):
            crypto.decrypt(tampered)

    def test_from_password(self):
        """Test key derivation from password."""
        if not is_aes_available():
            pytest.skip("cryptography not installed")

        crypto1, salt = SecureEncryption.from_password("mypassword")
        crypto2, _ = SecureEncryption.from_password("mypassword", salt=salt)

        # Same password + salt should produce same key
        plaintext = b"test"
        encrypted = crypto1.encrypt(plaintext)

        # Note: Can't directly compare keys, but can verify functionality
        assert crypto1.key == crypto2.key

    def test_generate_key(self):
        """Test key generation."""
        if not is_aes_available():
            pytest.skip("cryptography not installed")

        key = SecureEncryption.generate_key()

        assert len(key) == 32
        assert isinstance(key, bytes)

    def test_short_key_padding(self):
        """Test that short keys are padded."""
        if not is_aes_available():
            pytest.skip("cryptography not installed")

        short_key = b"short"
        crypto = SecureEncryption(short_key)

        assert len(crypto.key) == 32

    def test_associated_data(self, crypto):
        """Test encryption with associated data."""
        plaintext = b"message"
        aad = b"header"

        encrypted = crypto.encrypt(plaintext, associated_data=aad)
        decrypted = crypto.decrypt(encrypted, associated_data=aad)

        assert decrypted == plaintext

    def test_wrong_associated_data(self, crypto):
        """Test that wrong AAD causes failure."""
        plaintext = b"message"

        encrypted = crypto.encrypt(plaintext, associated_data=b"correct")

        with pytest.raises(ValueError):
            crypto.decrypt(encrypted, associated_data=b"wrong")


# XORCipher tests removed in v1.2.1 - XOR fallback is no longer supported
# See CHANGELOG.md for security rationale


class TestCreateEncryption:
    """Tests for create_encryption factory."""

    def test_with_key(self):
        """Test creating with key."""
        enc = create_encryption(key=os.urandom(32))
        assert enc is not None

    def test_with_password(self):
        """Test creating with password."""
        if not is_aes_available():
            pytest.skip("cryptography not installed")

        enc = create_encryption(password="mypassword")
        assert enc is not None

    def test_auto_key(self):
        """Test auto key generation."""
        enc = create_encryption()

        plaintext = b"test"
        encrypted = enc.encrypt(plaintext)
        decrypted = enc.decrypt(encrypted)

        assert decrypted == plaintext
