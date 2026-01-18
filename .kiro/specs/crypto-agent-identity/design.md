# Cryptographic Agent Identity — Technical Design

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    SENTINEL Brain                                │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   Trust Zone    │  │  CryptoIdentity │  │   Verifier      │ │
│  │   Controller    │──│     Manager     │──│    Engine       │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│           │                   │                     │           │
│           ▼                   ▼                     ▼           │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                      KeyStore (Encrypted)                   ││
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    ││
│  │  │ Agent A  │  │ Agent B  │  │ Agent C  │  │   ...    │    ││
│  │  │ Ed25519  │  │ Ed25519  │  │ Ed25519  │  │          │    ││
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘    ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

## Components

### 1. CryptoIdentityManager

**File:** `src/brain/security/crypto_identity.py`

```python
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from dataclasses import dataclass
from typing import Optional
import time
import secrets

@dataclass
class SignedRequest:
    payload: bytes
    signature: bytes
    timestamp: int
    nonce: str
    agent_id: str

class CryptoIdentityManager:
    """Ed25519-based agent identity management."""
    
    def __init__(self, keystore_path: str, master_key: bytes):
        self.keystore_path = keystore_path
        self.master_key = master_key
        self._keys: Dict[str, Ed25519PrivateKey] = {}
    
    def generate_identity(self, agent_id: str) -> bytes:
        """Generate new Ed25519 keypair for agent."""
        private_key = Ed25519PrivateKey.generate()
        self._keys[agent_id] = private_key
        self._save_key(agent_id, private_key)
        return private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
    
    def sign_request(self, agent_id: str, payload: bytes) -> SignedRequest:
        """Sign request with agent's private key."""
        private_key = self._get_key(agent_id)
        timestamp = int(time.time())
        nonce = secrets.token_hex(16)
        
        # Include metadata in signed data
        data_to_sign = self._build_signing_data(payload, timestamp, nonce)
        signature = private_key.sign(data_to_sign)
        
        return SignedRequest(
            payload=payload,
            signature=signature,
            timestamp=timestamp,
            nonce=nonce,
            agent_id=agent_id
        )
    
    def verify_request(self, request: SignedRequest, public_key: bytes) -> bool:
        """Verify signed request."""
        # Check timestamp (5 min window)
        if abs(time.time() - request.timestamp) > 300:
            return False
        
        # Check nonce not reused
        if self._nonce_used(request.nonce):
            return False
        
        # Verify signature
        data_to_sign = self._build_signing_data(
            request.payload, request.timestamp, request.nonce
        )
        try:
            public_key_obj = Ed25519PublicKey.from_public_bytes(public_key)
            public_key_obj.verify(request.signature, data_to_sign)
            self._mark_nonce_used(request.nonce)
            return True
        except InvalidSignature:
            return False
```

### 2. KeyStore

**File:** `src/brain/security/keystore.py`

```python
class EncryptedKeyStore:
    """AES-256-GCM encrypted key storage."""
    
    def __init__(self, path: str, master_key: bytes):
        self.path = Path(path)
        self.cipher = AESGCM(master_key)
    
    def save(self, agent_id: str, private_key: Ed25519PrivateKey):
        """Encrypt and save private key."""
        key_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption()
        )
        nonce = os.urandom(12)
        ciphertext = self.cipher.encrypt(nonce, key_bytes, None)
        
        key_file = self.path / f"{agent_id}.key"
        key_file.write_bytes(nonce + ciphertext)
    
    def load(self, agent_id: str) -> Ed25519PrivateKey:
        """Load and decrypt private key."""
        key_file = self.path / f"{agent_id}.key"
        data = key_file.read_bytes()
        nonce, ciphertext = data[:12], data[12:]
        key_bytes = self.cipher.decrypt(nonce, ciphertext, None)
        return Ed25519PrivateKey.from_private_bytes(key_bytes)
```

### 3. TrustZone Integration

**Modified:** `src/brain/security/trust_zones.py`

```python
class TrustZone:
    def __init__(self, level: TrustLevel, crypto_manager: CryptoIdentityManager):
        self.level = level
        self.crypto = crypto_manager
        self.require_signature = level in [TrustLevel.HIGH, TrustLevel.LOW]
    
    def validate_request(self, request: SignedRequest) -> bool:
        if not self.require_signature:
            return True  # MEDIUM zone bypass
        
        public_key = self._get_agent_public_key(request.agent_id)
        return self.crypto.verify_request(request, public_key)
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `src/brain/security/crypto_identity.py` | NEW | CryptoIdentityManager |
| `src/brain/security/keystore.py` | NEW | EncryptedKeyStore |
| `src/brain/security/trust_zones.py` | MODIFY | Add crypto validation |
| `tests/test_crypto_identity.py` | NEW | Unit tests |
| `tests/test_keystore.py` | NEW | KeyStore tests |

## Dependencies

```toml
# pyproject.toml additions
cryptography = ">=42.0.0"
```

## Verification Plan

### Unit Tests
```bash
pytest tests/test_crypto_identity.py -v
pytest tests/test_keystore.py -v
```

### Integration Test
```bash
pytest tests/integration/test_trust_zone_crypto.py -v
```

### Manual Verification
1. Generate keypair for test agent
2. Sign a request
3. Verify signature succeeds
4. Tamper with payload → verify fails
5. Replay same request → verify fails (nonce reuse)
