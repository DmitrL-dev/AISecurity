#!/usr/bin/env python3
"""
SENTINEL Brain — Encrypted KeyStore

AES-256-GCM encrypted storage for Ed25519 private keys.
"""

from pathlib import Path
from typing import Optional
import os
import json

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False


class EncryptedKeyStore:
    """AES-256-GCM encrypted key storage.
    
    Features:
    - Encrypt private keys at rest
    - 12-byte nonces for GCM
    - Key derivation from master secret
    
    Example:
        keystore = EncryptedKeyStore("/path/to/keys", master_key)
        keystore.save("agent-001", private_key)
        loaded = keystore.load("agent-001")
    """
    
    NONCE_SIZE = 12
    
    def __init__(self, path: str, master_key: bytes):
        """Initialize encrypted keystore.
        
        Args:
            path: Directory for key files
            master_key: 32-byte AES-256 master key
        """
        if not CRYPTO_AVAILABLE:
            raise ImportError("cryptography library required")
        
        if len(master_key) != 32:
            raise ValueError("Master key must be 32 bytes for AES-256")
        
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True)
        self.cipher = AESGCM(master_key)
    
    def save(self, agent_id: str, private_key: Ed25519PrivateKey):
        """Encrypt and save private key.
        
        Args:
            agent_id: Agent identifier
            private_key: Ed25519 private key
        """
        # Get raw private key bytes
        key_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        # Generate random nonce
        nonce = os.urandom(self.NONCE_SIZE)
        
        # Encrypt
        ciphertext = self.cipher.encrypt(nonce, key_bytes, None)
        
        # Write: nonce + ciphertext
        key_file = self.path / f"{self._safe_filename(agent_id)}.key"
        key_file.write_bytes(nonce + ciphertext)
    
    def load(self, agent_id: str) -> Optional[Ed25519PrivateKey]:
        """Load and decrypt private key.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Ed25519 private key or None if not found
        """
        key_file = self.path / f"{self._safe_filename(agent_id)}.key"
        
        if not key_file.exists():
            return None
        
        data = key_file.read_bytes()
        
        # Split: nonce + ciphertext
        nonce = data[:self.NONCE_SIZE]
        ciphertext = data[self.NONCE_SIZE:]
        
        # Decrypt
        try:
            key_bytes = self.cipher.decrypt(nonce, ciphertext, None)
            return Ed25519PrivateKey.from_private_bytes(key_bytes)
        except Exception:
            return None
    
    def delete(self, agent_id: str) -> bool:
        """Delete stored key.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            True if deleted, False if not found
        """
        key_file = self.path / f"{self._safe_filename(agent_id)}.key"
        
        if key_file.exists():
            key_file.unlink()
            return True
        return False
    
    def list_agents(self) -> list:
        """List all stored agent IDs."""
        return [
            f.stem for f in self.path.glob("*.key")
        ]
    
    def exists(self, agent_id: str) -> bool:
        """Check if key exists for agent."""
        key_file = self.path / f"{self._safe_filename(agent_id)}.key"
        return key_file.exists()
    
    def _safe_filename(self, agent_id: str) -> str:
        """Sanitize agent ID for filesystem."""
        # Replace unsafe chars
        safe = agent_id.replace("/", "_").replace("\\", "_")
        safe = safe.replace("..", "_").replace(" ", "_")
        return safe


class KeyStoreManager:
    """High-level keystore management.
    
    Wraps EncryptedKeyStore with automatic master key handling.
    """
    
    def __init__(self, base_path: str, master_key_env: str = "SENTINEL_MASTER_KEY"):
        """Initialize keystore manager.
        
        Args:
            base_path: Base directory for keys
            master_key_env: Environment variable for master key
        """
        master_key = os.environ.get(master_key_env)
        
        if master_key is None:
            # Generate and warn
            import warnings
            warnings.warn(
                f"No master key in {master_key_env}, using random key. "
                "Keys will be lost on restart!"
            )
            master_key_bytes = os.urandom(32)
        else:
            # Decode from hex
            master_key_bytes = bytes.fromhex(master_key)
        
        self.store = EncryptedKeyStore(base_path, master_key_bytes)
    
    def __getattr__(self, name):
        """Delegate to underlying store."""
        return getattr(self.store, name)
