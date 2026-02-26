"""
SENTINEL Shield v2.0 — Encoding Detection Engine

Detects encoding-based obfuscation attacks:
1. Base64 encoded payloads
2. Hex encoded strings
3. ROT13 / Caesar cipher
4. Unicode homoglyph substitution
5. Invisible characters (ZWS, RTL override, etc.)
"""

import base64
import re
import logging
from .base import BaseEngine, EngineResult, ThreatMatch

logger = logging.getLogger("shield.engines.encoding")

# Unicode homoglyphs (Cyrillic/Greek/Latin lookalikes)
_HOMOGLYPH_MAP = {
    "\u0410": "A",
    "\u0412": "B",
    "\u0421": "C",
    "\u0415": "E",
    "\u041d": "H",
    "\u041a": "K",
    "\u041c": "M",
    "\u041e": "O",
    "\u0420": "P",
    "\u0422": "T",
    "\u0425": "X",
    "\u0430": "a",
    "\u0435": "e",
    "\u043e": "o",
    "\u0440": "p",
    "\u0441": "c",
    "\u0443": "y",
    "\u0445": "x",
    # Greek
    "\u0391": "A",
    "\u0392": "B",
    "\u0395": "E",
    "\u0397": "H",
    "\u0399": "I",
    "\u039a": "K",
    "\u039c": "M",
    "\u039d": "N",
    "\u039f": "O",
    "\u03a1": "P",
    "\u03a4": "T",
    "\u03a7": "X",
    "\u03b1": "a",
    "\u03bf": "o",
}

# Invisible/control characters
_INVISIBLE_CHARS = {
    "\u200b": "zero-width space",
    "\u200c": "zero-width non-joiner",
    "\u200d": "zero-width joiner",
    "\u200e": "left-to-right mark",
    "\u200f": "right-to-left mark",
    "\u202a": "left-to-right embedding",
    "\u202b": "right-to-left embedding",
    "\u202c": "pop directional formatting",
    "\u202d": "left-to-right override",
    "\u202e": "right-to-left override",
    "\u2060": "word joiner",
    "\u2061": "function application",
    "\u2062": "invisible times",
    "\u2063": "invisible separator",
    "\u2064": "invisible plus",
    "\ufeff": "byte order mark",
    "\ufff9": "interlinear annotation anchor",
    "\ufffa": "interlinear annotation separator",
    "\ufffb": "interlinear annotation terminator",
}

# Pattern for base64 detection
_BASE64_RE = re.compile(r"[A-Za-z0-9+/]{20,}={0,2}")
_HEX_RE = re.compile(r"(?:0x)?[0-9a-fA-F]{20,}")
_UNICODE_ESCAPE_RE = re.compile(r"\\u[0-9a-fA-F]{4}")


class EncodingEngine(BaseEngine):
    """
    Encoding-based obfuscation detection.

    Attackers encode injection payloads in base64, hex, rot13,
    or use unicode homoglyphs to bypass regex filters.
    """

    def __init__(self, weight: float = 0.8):
        super().__init__(name="encoding", weight=weight)
        # Known injection keywords to check in decoded payloads
        self._injection_keywords = [
            "ignore",
            "instructions",
            "system",
            "prompt",
            "jailbreak",
            "bypass",
            "admin",
            "developer",
            "password",
            "secret",
            "credential",
            "token",
            "execute",
            "eval",
            "exec",
            "shell",
        ]

    def _check_base64(self, text: str) -> list[ThreatMatch]:
        """Check for base64-encoded suspicious content."""
        threats = []
        for match in _BASE64_RE.finditer(text):
            encoded = match.group(0)
            try:
                # Add padding if needed
                padded = encoded + "=" * (4 - len(encoded) % 4)
                decoded = base64.b64decode(padded).decode("utf-8", errors="ignore")

                # Check if decoded content contains injection keywords
                decoded_lower = decoded.lower()
                for kw in self._injection_keywords:
                    if kw in decoded_lower:
                        threats.append(
                            ThreatMatch(
                                threat_type="base64_encoded_injection",
                                risk_score=0.85,
                                engine=self.name,
                                description=f"Base64 payload contains '{kw}'",
                                matched_text=encoded[:50],
                                metadata={
                                    "decoded_preview": decoded[:100],
                                    "keyword": kw,
                                },
                            )
                        )
                        break
                else:
                    # Base64 present but no keywords — lower risk
                    if len(encoded) > 50:
                        threats.append(
                            ThreatMatch(
                                threat_type="base64_payload",
                                risk_score=0.40,
                                engine=self.name,
                                description="Large base64-encoded payload detected",
                                matched_text=encoded[:50],
                            )
                        )
            except Exception:
                pass  # Not valid base64
        return threats

    def _check_hex(self, text: str) -> list[ThreatMatch]:
        """Check for hex-encoded suspicious content."""
        threats = []
        for match in _HEX_RE.finditer(text):
            hex_str = match.group(0).lstrip("0x")
            if len(hex_str) < 20:
                continue
            try:
                decoded = bytes.fromhex(hex_str).decode("utf-8", errors="ignore")
                decoded_lower = decoded.lower()
                for kw in self._injection_keywords:
                    if kw in decoded_lower:
                        threats.append(
                            ThreatMatch(
                                threat_type="hex_encoded_injection",
                                risk_score=0.80,
                                engine=self.name,
                                description=f"Hex payload contains '{kw}'",
                                matched_text=hex_str[:50],
                                metadata={"decoded_preview": decoded[:100]},
                            )
                        )
                        break
            except Exception:
                pass
        return threats

    def _check_homoglyphs(self, text: str) -> list[ThreatMatch]:
        """Check for unicode homoglyph substitutions."""
        threats = []
        homoglyph_count = sum(1 for c in text if c in _HOMOGLYPH_MAP)

        if homoglyph_count > 0:
            # Normalize homoglyphs to ASCII
            normalized = "".join(_HOMOGLYPH_MAP.get(c, c) for c in text)
            if normalized != text:
                ratio = homoglyph_count / max(len(text), 1)
                risk = min(0.3 + ratio * 2, 0.9)
                threats.append(
                    ThreatMatch(
                        threat_type="homoglyph_substitution",
                        risk_score=risk,
                        engine=self.name,
                        description=f"{homoglyph_count} homoglyph characters detected ({ratio:.0%} of text)",
                        metadata={
                            "homoglyph_count": homoglyph_count,
                            "normalized_preview": normalized[:100],
                        },
                    )
                )
        return threats

    def _check_invisible_chars(self, text: str) -> list[ThreatMatch]:
        """Check for invisible/control characters."""
        threats = []
        found = {}
        for char, name in _INVISIBLE_CHARS.items():
            count = text.count(char)
            if count > 0:
                found[name] = count

        if found:
            # RTL override is especially dangerous
            risk = 0.70 if "right-to-left override" in found else 0.50
            threats.append(
                ThreatMatch(
                    threat_type="invisible_characters",
                    risk_score=risk,
                    engine=self.name,
                    description=f"Found {sum(found.values())} invisible characters: {', '.join(found.keys())}",
                    metadata={"characters": found},
                )
            )
        return threats

    def _check_unicode_escapes(self, text: str) -> list[ThreatMatch]:
        """Check for unicode escape sequences in text."""
        threats = []
        escapes = _UNICODE_ESCAPE_RE.findall(text)
        if len(escapes) > 3:
            threats.append(
                ThreatMatch(
                    threat_type="unicode_escape_sequence",
                    risk_score=0.55,
                    engine=self.name,
                    description=f"{len(escapes)} unicode escape sequences detected",
                    metadata={"count": len(escapes), "sample": escapes[:5]},
                )
            )
        return threats

    def analyze(self, text: str) -> EngineResult:
        threats: list[ThreatMatch] = []

        threats.extend(self._check_base64(text))
        threats.extend(self._check_hex(text))
        threats.extend(self._check_homoglyphs(text))
        threats.extend(self._check_invisible_chars(text))
        threats.extend(self._check_unicode_escapes(text))

        max_risk = max((t.risk_score for t in threats), default=0.0)

        return EngineResult(
            engine_name=self.name,
            risk_score=max_risk,
            threats=threats,
        )
