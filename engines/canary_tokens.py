"""
Canary Tokens Engine - Data Leak Detection for SENTINEL Community

Injects invisible watermarks into LLM responses using zero-width characters.
When data leaks, we can trace the exact source (user, session, timestamp).

Use Cases:
- Detect unauthorized sharing of LLM responses
- Track which user/session leaked confidential data
- Identify insider threats
- Compliance monitoring

Example:
    from canary_tokens import CanaryTokenEngine
    
    engine = CanaryTokenEngine()
    
    # Mark a response before sending
    result = engine.mark_response(
        "Your API key is: sk-abc123...",
        user_id="user_42",
        session_id="sess_8a7b"
    )
    llm_response = result.marked_text  # Invisible markers added
    
    # Later: check if text was leaked
    leaked_text = "...found on pastebin..."
    extraction = engine.check_leak(leaked_text)
    if extraction.found:
        print(f"Leak source: user={extraction.token.user_id}")
"""

import re
import logging
import secrets
import hashlib
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger("CanaryTokens")


# ============================================================================
# Constants - Zero-Width Characters
# ============================================================================

ZERO_WIDTH_SPACE = "\u200b"      # Binary: 00
ZERO_WIDTH_NON_JOINER = "\u200c" # Binary: 01
ZERO_WIDTH_JOINER = "\u200d"     # Binary: 10
WORD_JOINER = "\u2060"           # Binary: 11

ZW_CHARS = [ZERO_WIDTH_SPACE, ZERO_WIDTH_NON_JOINER, ZERO_WIDTH_JOINER, WORD_JOINER]


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class CanaryToken:
    """A canary token with tracking metadata."""
    token_id: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    document_hash: str = ""
    encoded_data: str = ""

    def to_dict(self) -> dict:
        return {
            "token_id": self.token_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "document_hash": self.document_hash,
        }


@dataclass
class CanaryResult:
    """Result from canary token operations."""
    original_text: str
    marked_text: str
    token: Optional[CanaryToken] = None
    success: bool = True


@dataclass
class CanaryExtraction:
    """Extracted canary information from text."""
    found: bool
    token: Optional[CanaryToken] = None
    raw_data: str = ""
    extraction_method: str = ""


# ============================================================================
# Canary Encoder - Binary ↔ Zero-Width
# ============================================================================

class CanaryEncoder:
    """Encodes canary tokens using zero-width characters."""

    def __init__(self):
        self._encode_map = {
            "00": ZERO_WIDTH_SPACE,
            "01": ZERO_WIDTH_NON_JOINER,
            "10": ZERO_WIDTH_JOINER,
            "11": WORD_JOINER,
        }
        self._decode_map = {v: k for k, v in self._encode_map.items()}

    def encode_to_zerowidth(self, data: str) -> str:
        """Encode string to invisible zero-width characters."""
        binary = "".join(format(ord(c), "08b") for c in data)
        if len(binary) % 2:
            binary += "0"
        
        result = ""
        for i in range(0, len(binary), 2):
            bits = binary[i:i+2]
            result += self._encode_map.get(bits, ZERO_WIDTH_SPACE)
        return result

    def decode_from_zerowidth(self, encoded: str) -> str:
        """Decode zero-width characters back to string."""
        zw_only = "".join(c for c in encoded if c in ZW_CHARS)
        if not zw_only:
            return ""
        
        binary = ""
        for c in zw_only:
            binary += self._decode_map.get(c, "00")
        
        result = ""
        for i in range(0, len(binary), 8):
            byte = binary[i:i+8]
            if len(byte) == 8:
                char_code = int(byte, 2)
                if 32 <= char_code < 127:
                    result += chr(char_code)
        return result

    def create_marker(
        self,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        document_id: Optional[str] = None,
    ) -> Tuple[str, CanaryToken]:
        """Create a canary marker with metadata."""
        token_id = secrets.token_hex(8)
        
        payload = {
            "t": token_id[:8],
            "u": (user_id or "")[:8],
            "s": (session_id or "")[:8],
            "d": int(datetime.now().timestamp()) % 100000,
        }
        
        payload_str = json.dumps(payload, separators=(",", ":"))
        encoded = self.encode_to_zerowidth(payload_str)
        
        token = CanaryToken(
            token_id=token_id,
            user_id=user_id,
            session_id=session_id,
            created_at=datetime.now(),
            document_hash=hashlib.sha256(payload_str.encode()).hexdigest()[:16],
            encoded_data=payload_str,
        )
        return encoded, token


# ============================================================================
# Canary Injector
# ============================================================================

class CanaryInjector:
    """Injects canary tokens into text."""

    def __init__(self, encoder: CanaryEncoder):
        self.encoder = encoder

    def inject(
        self,
        text: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        position: str = "end",
    ) -> CanaryResult:
        """
        Inject canary token into text.
        
        Args:
            text: Text to mark
            user_id: User identifier for tracking
            session_id: Session identifier
            position: "start", "end", or "distributed"
        """
        marker, token = self.encoder.create_marker(user_id=user_id, session_id=session_id)
        
        if position == "start":
            marked = marker + text
        elif position == "distributed":
            marked = self._distribute_marker(text, marker)
        else:  # end
            marked = text + marker
        
        return CanaryResult(original_text=text, marked_text=marked, token=token, success=True)

    def _distribute_marker(self, text: str, marker: str) -> str:
        """Distribute marker throughout text at word boundaries."""
        words = text.split()
        if len(words) < 2:
            return text + marker
        
        chunk_size = max(1, len(marker) // min(5, len(words)))
        marker_chunks = [marker[i:i+chunk_size] for i in range(0, len(marker), chunk_size)]
        
        result = []
        chunk_idx = 0
        
        for i, word in enumerate(words):
            result.append(word)
            if chunk_idx < len(marker_chunks) and i % (len(words) // len(marker_chunks) + 1) == 0:
                result.append(marker_chunks[chunk_idx])
                chunk_idx += 1
        
        while chunk_idx < len(marker_chunks):
            result.append(marker_chunks[chunk_idx])
            chunk_idx += 1
        
        return " ".join(result)


# ============================================================================
# Canary Extractor
# ============================================================================

class CanaryExtractor:
    """Extracts canary tokens from text."""

    def __init__(self, encoder: CanaryEncoder):
        self.encoder = encoder

    def extract(self, text: str) -> CanaryExtraction:
        """Extract canary token from text if present."""
        zw_count = sum(1 for c in text if c in ZW_CHARS)
        
        if zw_count < 10:
            return CanaryExtraction(found=False)
        
        decoded = self.encoder.decode_from_zerowidth(text)
        if not decoded:
            return CanaryExtraction(found=False)
        
        try:
            payload = json.loads(decoded)
            token = CanaryToken(
                token_id=payload.get("t", ""),
                user_id=payload.get("u") or None,
                session_id=payload.get("s") or None,
                encoded_data=decoded,
            )
            return CanaryExtraction(found=True, token=token, raw_data=decoded, extraction_method="zero_width")
        except json.JSONDecodeError:
            return CanaryExtraction(found=True, token=None, raw_data=decoded, extraction_method="zero_width_partial")

    def has_canary(self, text: str) -> bool:
        """Quick check if text contains canary markers."""
        return any(c in text for c in ZW_CHARS)


# ============================================================================
# Main Engine
# ============================================================================

class CanaryTokenEngine:
    """
    SENTINEL Canary Token Engine
    
    Marks LLM responses with invisible tracking tokens
    that reveal the source of any data leaks.
    
    Usage:
        engine = CanaryTokenEngine()
        
        # Mark response before sending to user
        result = engine.mark_response("Sensitive data...", user_id="user123")
        send_to_user(result.marked_text)
        
        # Check for leaks
        if engine.check_leak(found_text).found:
            alert("Data leak detected!")
    """

    def __init__(self):
        self.encoder = CanaryEncoder()
        self.injector = CanaryInjector(self.encoder)
        self.extractor = CanaryExtractor(self.encoder)
        self._tokens: Dict[str, CanaryToken] = {}
        logger.info("CanaryTokenEngine initialized")

    def mark_response(
        self,
        response: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        distributed: bool = False,
    ) -> CanaryResult:
        """
        Mark LLM response with canary token.
        
        Args:
            response: Response text to mark
            user_id: User identifier for tracking
            session_id: Session identifier
            distributed: Spread marker throughout text (harder to remove)
        """
        position = "distributed" if distributed else "end"
        result = self.injector.inject(text=response, user_id=user_id, session_id=session_id, position=position)
        
        if result.token:
            self._tokens[result.token.token_id] = result.token
        return result

    def check_leak(self, leaked_text: str) -> CanaryExtraction:
        """
        Check if text contains our canary marker.
        
        Returns extraction with source information if found.
        """
        extraction = self.extractor.extract(leaked_text)
        
        if extraction.found and extraction.token:
            logger.warning(f"CANARY DETECTED! Token={extraction.token.token_id}, User={extraction.token.user_id}")
        return extraction

    def strip_canary(self, text: str) -> str:
        """Remove canary markers from text (for display purposes)."""
        return "".join(c for c in text if c not in ZW_CHARS)

    def get_info(self) -> dict:
        """Engine metadata for SENTINEL integration."""
        return {
            "name": "CanaryTokenEngine",
            "version": "1.0.0",
            "description": "Invisible watermarking for data leak detection",
            "category": "defense",
            "owasp": ["LLM06"],
        }


# ============================================================================
# Convenience API
# ============================================================================

_default_engine: Optional[CanaryTokenEngine] = None

def get_engine() -> CanaryTokenEngine:
    global _default_engine
    if _default_engine is None:
        _default_engine = CanaryTokenEngine()
    return _default_engine

def mark_text(text: str, user_id: Optional[str] = None, session_id: Optional[str] = None) -> CanaryResult:
    """Quick API to mark text with canary."""
    return get_engine().mark_response(text, user_id, session_id)

def check_for_leak(text: str) -> CanaryExtraction:
    """Quick API to check for leaked canary."""
    return get_engine().check_leak(text)


# ============================================================================
# CLI Demo
# ============================================================================

if __name__ == "__main__":
    print("🐦 SENTINEL Canary Token Demo\n")
    
    engine = CanaryTokenEngine()
    
    # Mark some text
    secret = "The API key is: sk-abc123xyz789"
    result = engine.mark_response(secret, user_id="user_42", session_id="sess_001")
    
    print(f"Original: {secret}")
    print(f"Marked:   {result.marked_text}")
    print(f"Same visually? {secret == engine.strip_canary(result.marked_text)}")
    print(f"Token ID: {result.token.token_id}")
    print()
    
    # Simulate leak detection
    print("Checking for leak in marked text...")
    extraction = engine.check_leak(result.marked_text)
    
    if extraction.found:
        print(f"🚨 LEAK DETECTED!")
        print(f"   Source User: {extraction.token.user_id}")
        print(f"   Session: {extraction.token.session_id}")
        print(f"   Token: {extraction.token.token_id}")
    else:
        print("✅ No canary found")
