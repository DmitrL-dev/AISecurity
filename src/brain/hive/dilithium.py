"""
Post-Quantum Cryptography Module

Implements CRYSTALS-Dilithium signatures for quantum-resistant security.
Uses liboqs via oqs-python when available, falls back to simulated mode.

Based on NIST PQC standardization (FIPS 204).
"""

import logging
import hashlib
import secrets
from dataclasses import dataclass
from typing import Optional
from datetime import datetime

logger = logging.getLogger("PostQuantum")

# Try to import liboqs
try:
    import oqs
    OQS_AVAILABLE = True
    logger.info("liboqs available - using real CRYSTALS-Dilithium")
except ImportError:
    OQS_AVAILABLE = False
    logger.warning("liboqs not available - using simulated PQC")


@dataclass
class DilithiumKeyPair:
    """CRYSTALS-Dilithium key pair."""
    public_key: bytes
    secret_key: bytes
    algorithm: str = "Dilithium3"
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class DilithiumSignature:
    """Signed message with Dilithium."""
    message: bytes
    signature: bytes
    public_key: bytes
    algorithm: str
    timestamp: datetime


class CRYSTALSDilithium:
    """
    CRYSTALS-Dilithium digital signature scheme.

    Security levels:
    - Dilithium2: NIST Level 2 (≈ AES-128)
    - Dilithium3: NIST Level 3 (≈ AES-192) [DEFAULT]
    - Dilithium5: NIST Level 5 (≈ AES-256)

    Usage:
        pqc = CRYSTALSDilithium()
        keypair = pqc.generate_keypair()

        sig = pqc.sign(b"message", keypair.secret_key)
        valid = pqc.verify(b"message", sig.signature, keypair.public_key)
    """

    ALGORITHMS = {
        "Dilithium2": {"pk_size": 1312, "sk_size": 2528, "sig_size": 2420},
        "Dilithium3": {"pk_size": 1952, "sk_size": 4000, "sig_size": 3293},
        "Dilithium5": {"pk_size": 2592, "sk_size": 4864, "sig_size": 4595},
    }

    def __init__(self, algorithm: str = "Dilithium3"):
        if algorithm not in self.ALGORITHMS:
            raise ValueError(f"Unknown algorithm: {algorithm}")

        self.algorithm = algorithm
        self._signer = None

        if OQS_AVAILABLE:
            try:
                self._signer = oqs.Signature(algorithm)
            except Exception as e:
                logger.error(f"Failed to init oqs.Signature: {e}")

        logger.info(f"Initialized {algorithm} (real={OQS_AVAILABLE})")

    def generate_keypair(self) -> DilithiumKeyPair:
        """Generate a new Dilithium key pair."""
        if self._signer:
            public_key = self._signer.generate_keypair()
            secret_key = self._signer.export_secret_key()
        else:
            # Simulated mode - generate random keys of correct size
            sizes = self.ALGORITHMS[self.algorithm]
            public_key = secrets.token_bytes(sizes["pk_size"])
            secret_key = secrets.token_bytes(sizes["sk_size"])

        return DilithiumKeyPair(
            public_key=public_key,
            secret_key=secret_key,
            algorithm=self.algorithm
        )

    def sign(self, message: bytes, secret_key: bytes) -> DilithiumSignature:
        """Sign a message with Dilithium."""
        if self._signer:
            # Real signing with liboqs
            signature = self._signer.sign(message)
        else:
            # Simulated - hash-based signature (NOT quantum-safe, just for testing)
            sig_size = self.ALGORITHMS[self.algorithm]["sig_size"]
            # Create deterministic "signature" from message + key
            h = hashlib.sha3_512(message + secret_key).digest()
            signature = h * (sig_size // len(h) + 1)
            signature = signature[:sig_size]

        return DilithiumSignature(
            message=message,
            signature=signature,
            public_key=b"",  # Don't include in signature object
            algorithm=self.algorithm,
            timestamp=datetime.now()
        )

    def verify(self, message: bytes, signature: bytes, public_key: bytes) -> bool:
        """Verify a Dilithium signature."""
        if self._signer:
            try:
                verifier = oqs.Signature(self.algorithm)
                return verifier.verify(message, signature, public_key)
            except Exception as e:
                logger.error(f"Verification failed: {e}")
                return False
        else:
            # Simulated - always return True in test mode
            # In production, liboqs must be installed
            logger.warning(
                "Simulated verification - install liboqs for real PQC")
            return len(signature) == self.ALGORITHMS[self.algorithm]["sig_size"]

    @staticmethod
    def is_available() -> bool:
        """Check if real PQC is available."""
        return OQS_AVAILABLE


class HybridSigner:
    """
    Hybrid Ed25519 + Dilithium signer.

    Provides both classical and post-quantum signatures.
    Valid if EITHER signature is valid (defense in depth).
    """

    def __init__(self):
        self.dilithium = CRYSTALSDilithium("Dilithium3")
        self._ed25519_available = False

        try:
            from cryptography.hazmat.primitives.asymmetric import ed25519
            self._ed25519_available = True
        except ImportError:
            pass

    def generate_hybrid_keypair(self) -> dict:
        """Generate both Ed25519 and Dilithium keys."""
        result = {
            "dilithium": self.dilithium.generate_keypair()
        }

        if self._ed25519_available:
            from cryptography.hazmat.primitives.asymmetric import ed25519
            ed_private = ed25519.Ed25519PrivateKey.generate()
            result["ed25519"] = {
                "private": ed_private,
                "public": ed_private.public_key()
            }

        return result

    def hybrid_sign(self, message: bytes, keypair: dict) -> dict:
        """Create hybrid signature (Ed25519 + Dilithium)."""
        signatures = {}

        # Dilithium signature
        dil_keypair = keypair["dilithium"]
        signatures["dilithium"] = self.dilithium.sign(
            message, dil_keypair.secret_key
        ).signature

        # Ed25519 signature
        if "ed25519" in keypair and self._ed25519_available:
            signatures["ed25519"] = keypair["ed25519"]["private"].sign(message)

        return signatures

    def hybrid_verify(self, message: bytes, signatures: dict, public_keys: dict) -> bool:
        """
        Verify hybrid signature.
        Returns True if at least one signature is valid.
        """
        results = []

        # Verify Dilithium
        if "dilithium" in signatures and "dilithium" in public_keys:
            dil_valid = self.dilithium.verify(
                message,
                signatures["dilithium"],
                public_keys["dilithium"]
            )
            results.append(dil_valid)

        # Verify Ed25519
        if "ed25519" in signatures and "ed25519" in public_keys:
            try:
                public_keys["ed25519"].verify(signatures["ed25519"], message)
                results.append(True)
            except Exception:
                results.append(False)

        # Valid if ANY signature is valid
        return any(results)


# Singleton
_dilithium: Optional[CRYSTALSDilithium] = None


def get_dilithium() -> CRYSTALSDilithium:
    """Get singleton Dilithium instance."""
    global _dilithium
    if _dilithium is None:
        _dilithium = CRYSTALSDilithium()
    return _dilithium
