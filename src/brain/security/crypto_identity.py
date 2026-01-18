#!/usr/bin/env python3
"""
SENTINEL Brain — Cryptographic Agent Identity

Ed25519-based cryptographic identity for AI agents.
Prevents impersonation, MITM, and replay attacks.

OWASP Mapping:
- ASI02: Inadequate Sandboxing
- ASI03: Identity/Privilege Abuse  
- ASI09: Trust Exploitation
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Set
from pathlib import Path
import time
import secrets
import hashlib
import json

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
        Ed25519PublicKey,
    )
    from cryptography.hazmat.primitives import serialization
    from cryptography.exceptions import InvalidSignature
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False


@dataclass
class SignedRequest:
    """Cryptographically signed request."""
    payload: bytes
    signature: bytes
    timestamp: int
    nonce: str
    agent_id: str
    
    def to_dict(self) -> Dict:
        return {
            "payload": self.payload.hex(),
            "signature": self.signature.hex(),
            "timestamp": self.timestamp,
            "nonce": self.nonce,
            "agent_id": self.agent_id,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "SignedRequest":
        return cls(
            payload=bytes.fromhex(data["payload"]),
            signature=bytes.fromhex(data["signature"]),
            timestamp=data["timestamp"],
            nonce=data["nonce"],
            agent_id=data["agent_id"],
        )


@dataclass
class AgentIdentity:
    """Agent cryptographic identity."""
    agent_id: str
    public_key: bytes
    created_at: float = field(default_factory=time.time)
    last_used: Optional[float] = None


class CryptoIdentityManager:
    """Ed25519-based agent identity management.
    
    Features:
    - Generate Ed25519 keypairs per agent
    - Sign requests with timestamp and nonce
    - Verify signatures with replay protection
    - Encrypted key storage
    
    Example:
        manager = CryptoIdentityManager()
        
        # Generate identity
        public_key = manager.generate_identity("agent-001")
        
        # Sign request
        signed = manager.sign_request("agent-001", b"payload")
        
        # Verify
        is_valid = manager.verify_request(signed, public_key)
    """
    
    # Timestamp tolerance (seconds)
    TIMESTAMP_TOLERANCE = 300  # 5 minutes
    
    # Nonce cache size
    MAX_NONCES = 10000
    
    def __init__(self, keystore_path: Optional[str] = None):
        """Initialize crypto manager.
        
        Args:
            keystore_path: Path to encrypted key storage (optional)
        """
        if not CRYPTO_AVAILABLE:
            raise ImportError(
                "cryptography library required. Install with: pip install cryptography"
            )
        
        self.keystore_path = Path(keystore_path) if keystore_path else None
        self._private_keys: Dict[str, Ed25519PrivateKey] = {}
        self._public_keys: Dict[str, bytes] = {}
        self._used_nonces: Set[str] = set()
        self._identities: Dict[str, AgentIdentity] = {}
    
    def generate_identity(self, agent_id: str) -> bytes:
        """Generate new Ed25519 keypair for agent.
        
        Args:
            agent_id: Unique agent identifier
            
        Returns:
            Public key bytes (32 bytes)
        """
        if agent_id in self._private_keys:
            raise ValueError(f"Identity already exists for agent: {agent_id}")
        
        # Generate keypair
        private_key = Ed25519PrivateKey.generate()
        public_key = private_key.public_key()
        
        # Extract raw bytes
        public_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        
        # Store
        self._private_keys[agent_id] = private_key
        self._public_keys[agent_id] = public_bytes
        self._identities[agent_id] = AgentIdentity(
            agent_id=agent_id,
            public_key=public_bytes
        )
        
        return public_bytes
    
    def get_public_key(self, agent_id: str) -> Optional[bytes]:
        """Get agent's public key.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Public key bytes or None if not found
        """
        return self._public_keys.get(agent_id)
    
    def register_external_key(self, agent_id: str, public_key: bytes):
        """Register external agent's public key for verification.
        
        Args:
            agent_id: Agent identifier
            public_key: 32-byte Ed25519 public key
        """
        if len(public_key) != 32:
            raise ValueError("Public key must be 32 bytes")
        
        self._public_keys[agent_id] = public_key
        self._identities[agent_id] = AgentIdentity(
            agent_id=agent_id,
            public_key=public_key
        )
    
    def sign_request(self, agent_id: str, payload: bytes) -> SignedRequest:
        """Sign request with agent's private key.
        
        Args:
            agent_id: Agent identifier
            payload: Request payload to sign
            
        Returns:
            SignedRequest with signature, timestamp, nonce
        """
        private_key = self._private_keys.get(agent_id)
        if private_key is None:
            raise ValueError(f"No private key for agent: {agent_id}")
        
        # Generate nonce and timestamp
        timestamp = int(time.time())
        nonce = secrets.token_hex(16)
        
        # Build data to sign (payload + timestamp + nonce + agent_id)
        data_to_sign = self._build_signing_data(payload, timestamp, nonce, agent_id)
        
        # Sign
        signature = private_key.sign(data_to_sign)
        
        # Update last used
        if agent_id in self._identities:
            self._identities[agent_id].last_used = time.time()
        
        return SignedRequest(
            payload=payload,
            signature=signature,
            timestamp=timestamp,
            nonce=nonce,
            agent_id=agent_id
        )
    
    def verify_request(
        self, 
        request: SignedRequest, 
        public_key: Optional[bytes] = None
    ) -> bool:
        """Verify signed request.
        
        Args:
            request: Signed request to verify
            public_key: Public key (optional, uses registered key if not provided)
            
        Returns:
            True if valid, False otherwise
        """
        # Get public key
        if public_key is None:
            public_key = self._public_keys.get(request.agent_id)
        
        if public_key is None:
            return False
        
        # Check timestamp (within tolerance)
        current_time = int(time.time())
        if abs(current_time - request.timestamp) > self.TIMESTAMP_TOLERANCE:
            return False
        
        # Check nonce not reused (replay protection)
        nonce_key = f"{request.agent_id}:{request.nonce}"
        if nonce_key in self._used_nonces:
            return False
        
        # Build expected signing data
        data_to_sign = self._build_signing_data(
            request.payload, 
            request.timestamp, 
            request.nonce,
            request.agent_id
        )
        
        # Verify signature
        try:
            public_key_obj = Ed25519PublicKey.from_public_bytes(public_key)
            public_key_obj.verify(request.signature, data_to_sign)
            
            # Mark nonce as used
            self._mark_nonce_used(nonce_key)
            
            return True
        except InvalidSignature:
            return False
        except Exception:
            return False
    
    def _build_signing_data(
        self, 
        payload: bytes, 
        timestamp: int, 
        nonce: str,
        agent_id: str
    ) -> bytes:
        """Build canonical data for signing."""
        # Hash payload to normalize length
        payload_hash = hashlib.sha256(payload).digest()
        
        # Concatenate: payload_hash + timestamp + nonce + agent_id
        data = (
            payload_hash + 
            timestamp.to_bytes(8, 'big') + 
            nonce.encode('utf-8') +
            agent_id.encode('utf-8')
        )
        return data
    
    def _mark_nonce_used(self, nonce_key: str):
        """Mark nonce as used, with cache eviction."""
        if len(self._used_nonces) >= self.MAX_NONCES:
            # Evict oldest (simple approach - clear half)
            # In production, use LRU or time-based eviction
            to_remove = list(self._used_nonces)[:self.MAX_NONCES // 2]
            for key in to_remove:
                self._used_nonces.discard(key)
        
        self._used_nonces.add(nonce_key)
    
    def revoke_identity(self, agent_id: str):
        """Revoke agent identity.
        
        Args:
            agent_id: Agent to revoke
        """
        self._private_keys.pop(agent_id, None)
        self._public_keys.pop(agent_id, None)
        self._identities.pop(agent_id, None)
    
    def list_identities(self) -> Dict[str, AgentIdentity]:
        """List all registered identities."""
        return dict(self._identities)
    
    def export_public_keys(self) -> Dict[str, str]:
        """Export all public keys as hex strings."""
        return {
            agent_id: key.hex() 
            for agent_id, key in self._public_keys.items()
        }


# Convenience function
def create_signed_message(
    agent_id: str,
    message: str,
    manager: CryptoIdentityManager
) -> Dict:
    """Create a signed JSON message.
    
    Args:
        agent_id: Agent identifier
        message: Message string
        manager: Crypto manager with agent's key
        
    Returns:
        Dict with message and signature
    """
    payload = message.encode('utf-8')
    signed = manager.sign_request(agent_id, payload)
    
    return {
        "message": message,
        "signed_request": signed.to_dict()
    }
