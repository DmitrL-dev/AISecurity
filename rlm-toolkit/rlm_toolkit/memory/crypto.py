"""
AES-256-GCM Encryption for RLM-Toolkit Memory.

Provides secure encryption for memory storage.
"""

import os
import base64
import logging
from typing import Optional, Tuple

logger = logging.getLogger("rlm_memory.crypto")

# Try to import cryptography
try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes

    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False
    AESGCM = None


class SecureEncryption:
    """
    AES-256-GCM encryption for secure memory storage.

    Features:
    - AES-256-GCM (authenticated encryption)
    - Unique nonce per encryption
    - Key derivation from password

    Example:
        >>> crypto = SecureEncryption(key=os.urandom(32))
        >>> encrypted = crypto.encrypt(b"secret data")
        >>> decrypted = crypto.decrypt(encrypted)
    """

    # AES-256 requires 32-byte key
    KEY_SIZE = 32
    # GCM nonce size
    NONCE_SIZE = 12

    def __init__(self, key: bytes):
        """
        Initialize with encryption key.

        Args:
            key: 32-byte encryption key
        """
        if not CRYPTOGRAPHY_AVAILABLE:
            raise RuntimeError(
                "cryptography library required. Install with: pip install cryptography"
            )

        if len(key) < self.KEY_SIZE:
            # Pad key if too short
            key = key.ljust(self.KEY_SIZE, b"\0")
        elif len(key) > self.KEY_SIZE:
            # Truncate if too long
            key = key[: self.KEY_SIZE]

        self.key = key
        self.aesgcm = AESGCM(key)

    def encrypt(self, plaintext: bytes, associated_data: bytes = None) -> bytes:
        """
        Encrypt data with AES-256-GCM.

        Args:
            plaintext: Data to encrypt
            associated_data: Optional authenticated data (not encrypted)

        Returns:
            Encrypted data (nonce + ciphertext + tag)
        """
        nonce = os.urandom(self.NONCE_SIZE)
        ciphertext = self.aesgcm.encrypt(nonce, plaintext, associated_data)
        return nonce + ciphertext

    def decrypt(self, ciphertext: bytes, associated_data: bytes = None) -> bytes:
        """
        Decrypt data.

        Args:
            ciphertext: Encrypted data (nonce + ciphertext + tag)
            associated_data: Associated data used during encryption

        Returns:
            Decrypted plaintext

        Raises:
            ValueError: If decryption fails (tampering detected)
        """
        if len(ciphertext) < self.NONCE_SIZE:
            raise ValueError("Invalid ciphertext: too short")

        nonce = ciphertext[: self.NONCE_SIZE]
        ct = ciphertext[self.NONCE_SIZE :]

        try:
            return self.aesgcm.decrypt(nonce, ct, associated_data)
        except Exception as e:
            raise ValueError(f"Decryption failed: {e}")

    def encrypt_string(self, plaintext: str) -> str:
        """Encrypt string and return base64-encoded result."""
        encrypted = self.encrypt(plaintext.encode("utf-8"))
        return base64.b64encode(encrypted).decode("ascii")

    def decrypt_string(self, ciphertext: str) -> str:
        """Decrypt base64-encoded ciphertext to string."""
        encrypted = base64.b64decode(ciphertext.encode("ascii"))
        decrypted = self.decrypt(encrypted)
        return decrypted.decode("utf-8")

    @classmethod
    def from_password(
        cls, password: str, salt: bytes = None
    ) -> Tuple["SecureEncryption", bytes]:
        """
        Create encryption from password using PBKDF2.

        Args:
            password: Password to derive key from
            salt: Salt for key derivation (generated if not provided)

        Returns:
            Tuple of (SecureEncryption instance, salt used)
        """
        if not CRYPTOGRAPHY_AVAILABLE:
            raise RuntimeError("cryptography library required")

        if salt is None:
            salt = os.urandom(16)

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=cls.KEY_SIZE,
            salt=salt,
            iterations=100_000,
        )
        key = kdf.derive(password.encode())

        return cls(key), salt

    @staticmethod
    def generate_key() -> bytes:
        """Generate a random 256-bit key."""
        return os.urandom(32)


# XORCipher class REMOVED (Security Audit T5.2)
# Triggered AV heuristics and should never be used in production


def create_encryption(key: bytes = None, password: str = None) -> SecureEncryption:
    """
    Create encryption instance.

    Args:
        key: Direct 32-byte key
        password: Password to derive key from

    Returns:
        SecureEncryption instance

    Raises:
        RuntimeError: If cryptography package not installed
    """
    if not CRYPTOGRAPHY_AVAILABLE:
        raise RuntimeError(
            "cryptography package required for encryption. "
            "Install with: pip install cryptography"
        )

    if password:
        enc, _ = SecureEncryption.from_password(password)
        return enc

    if key is None:
        key = os.urandom(32)

    return SecureEncryption(key)


def is_aes_available() -> bool:
    """Check if AES encryption is available."""
    return CRYPTOGRAPHY_AVAILABLE
