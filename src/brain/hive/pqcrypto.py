"""
Post-Quantum Cryptography Module
Implements Dilithium signatures for cognitive signature distribution.
Fallback to Ed25519 if PQC not available.
"""

import logging
import hashlib
import base64
from dataclasses import dataclass
from typing import Tuple, Optional
from datetime import datetime

logger = logging.getLogger("PQCrypto")

# Try to import PQC library
try:
    import oqs
    PQC_AVAILABLE = True
    logger.info("liboqs available - Post-Quantum Crypto enabled")
except ImportError:
    PQC_AVAILABLE = False
    logger.warning("liboqs not available - using Ed25519 fallback")

# Fallback to standard crypto
try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization
    ED25519_AVAILABLE = True
except ImportError:
    ED25519_AVAILABLE = False
    logger.warning("cryptography not available - signatures disabled")


@dataclass
class KeyPair:
    """Cryptographic key pair."""
    algorithm: str  # "dilithium3", "ed25519"
    public_key: bytes
    private_key: bytes
    created_at: datetime
    fingerprint: str


@dataclass
class Signature:
    """Cryptographic signature."""
    algorithm: str
    signature: bytes
    message_hash: str
    signer_fingerprint: str
    timestamp: datetime


class PostQuantumSigner:
    """
    Post-Quantum cryptographic signer.
    Uses Dilithium3 (NIST PQC standard) with Ed25519 fallback.
    """

    ALGORITHMS = {
        "dilithium3": "Dilithium3",  # NIST PQC Level 3
        "dilithium5": "Dilithium5",  # NIST PQC Level 5 (highest)
        "ed25519": "Ed25519",         # Classical fallback
    }

    def __init__(self, algorithm: str = "dilithium3"):
        self.algorithm = algorithm
        self._keypair: Optional[KeyPair] = None

        # Validate algorithm availability
        if algorithm.startswith("dilithium"):
            if not PQC_AVAILABLE:
                logger.warning(
                    f"{algorithm} not available, falling back to Ed25519")
                self.algorithm = "ed25519"

        if self.algorithm == "ed25519" and not ED25519_AVAILABLE:
            raise RuntimeError("No cryptographic backend available")

        logger.info(f"PostQuantumSigner initialized with {self.algorithm}")

    def generate_keypair(self) -> KeyPair:
        """Generate new key pair."""
        if self.algorithm == "ed25519":
            return self._generate_ed25519()
        else:
            return self._generate_dilithium()

    def _generate_ed25519(self) -> KeyPair:
        """Generate Ed25519 key pair."""
        private_key = Ed25519PrivateKey.generate()
        public_key = private_key.public_key()

        private_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption()
        )

        public_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )

        fingerprint = hashlib.sha256(public_bytes).hexdigest()[:16]

        self._keypair = KeyPair(
            algorithm="ed25519",
            public_key=public_bytes,
            private_key=private_bytes,
            created_at=datetime.now(),
            fingerprint=fingerprint,
        )

        logger.info(f"Generated Ed25519 keypair: {fingerprint}")
        return self._keypair

    def _generate_dilithium(self) -> KeyPair:
        """Generate Dilithium key pair (PQC)."""
        if not PQC_AVAILABLE:
            raise RuntimeError("liboqs not available")

        sig_alg = self.ALGORITHMS.get(self.algorithm, "Dilithium3")

        with oqs.Signature(sig_alg) as signer:
            public_key = signer.generate_keypair()
            private_key = signer.export_secret_key()

        fingerprint = hashlib.sha256(public_key).hexdigest()[:16]

        self._keypair = KeyPair(
            algorithm=self.algorithm,
            public_key=public_key,
            private_key=private_key,
            created_at=datetime.now(),
            fingerprint=fingerprint,
        )

        logger.info(f"Generated {self.algorithm} keypair: {fingerprint}")
        return self._keypair

    def sign(self, message: bytes) -> Signature:
        """Sign message."""
        if not self._keypair:
            self.generate_keypair()

        message_hash = hashlib.sha256(message).hexdigest()

        if self.algorithm == "ed25519":
            signature = self._sign_ed25519(message)
        else:
            signature = self._sign_dilithium(message)

        return Signature(
            algorithm=self.algorithm,
            signature=signature,
            message_hash=message_hash,
            signer_fingerprint=self._keypair.fingerprint,
            timestamp=datetime.now(),
        )

    def _sign_ed25519(self, message: bytes) -> bytes:
        """Sign with Ed25519."""
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

        private_key = Ed25519PrivateKey.from_private_bytes(
            self._keypair.private_key)
        return private_key.sign(message)

    def _sign_dilithium(self, message: bytes) -> bytes:
        """Sign with Dilithium."""
        sig_alg = self.ALGORITHMS.get(self.algorithm, "Dilithium3")

        with oqs.Signature(sig_alg, self._keypair.private_key) as signer:
            signature = signer.sign(message)

        return signature

    def verify(self, message: bytes, signature: Signature, public_key: bytes) -> bool:
        """Verify signature."""
        try:
            if signature.algorithm == "ed25519":
                return self._verify_ed25519(message, signature.signature, public_key)
            else:
                return self._verify_dilithium(message, signature.signature, public_key, signature.algorithm)
        except Exception as e:
            logger.error(f"Signature verification failed: {e}")
            return False

    def _verify_ed25519(self, message: bytes, signature: bytes, public_key: bytes) -> bool:
        """Verify Ed25519 signature."""
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

        try:
            pubkey = Ed25519PublicKey.from_public_bytes(public_key)
            pubkey.verify(signature, message)
            return True
        except:
            return False

    def _verify_dilithium(self, message: bytes, signature: bytes, public_key: bytes, algorithm: str) -> bool:
        """Verify Dilithium signature."""
        sig_alg = self.ALGORITHMS.get(algorithm, "Dilithium3")

        with oqs.Signature(sig_alg) as verifier:
            return verifier.verify(message, signature, public_key)

    def sign_cognitive_update(self, update_data: dict) -> Tuple[bytes, Signature]:
        """
        Sign a cognitive signature update.
        Used for secure distribution of engine configurations.
        """
        import json

        # Serialize update
        update_bytes = json.dumps(update_data, sort_keys=True).encode('utf-8')

        # Sign
        signature = self.sign(update_bytes)

        logger.info(
            f"Signed cognitive update: {len(update_bytes)} bytes, "
            f"algo={signature.algorithm}"
        )

        return update_bytes, signature

    def get_public_key_pem(self) -> str:
        """Export public key as base64."""
        if not self._keypair:
            self.generate_keypair()

        return base64.b64encode(self._keypair.public_key).decode('utf-8')


# Factory function
def create_signer(prefer_pqc: bool = True) -> PostQuantumSigner:
    """
    Create signer with appropriate algorithm.

    Args:
        prefer_pqc: If True, use Dilithium if available
    """
    if prefer_pqc and PQC_AVAILABLE:
        return PostQuantumSigner("dilithium3")
    else:
        return PostQuantumSigner("ed25519")


# Singleton for global use
_global_signer = None


def get_signer() -> PostQuantumSigner:
    global _global_signer
    if _global_signer is None:
        _global_signer = create_signer()
    return _global_signer
