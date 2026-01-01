"""
RAG Security Shield Engine - Retrieval Poisoning Defense

Protects RAG pipelines from poisoning attacks:
- Document source validation
- Content integrity verification
- Retrieval result sanitization
- Injection in retrieved content detection

Addresses: OWASP ASI-06 (RAG Poisoning)
Research: rag_security_deep_dive.md
Invention: RAG Security Shield (#38)
"""

import re
import hashlib
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

from .base_engine import Severity, Action  # Base classes

logger = logging.getLogger("RAGSecurityShield")


# ============================================================================
# Data Classes
# ============================================================================


class RAGViolationType(Enum):
    """Types of RAG violations."""

    UNTRUSTED_SOURCE = "untrusted_source"
    CONTENT_INJECTION = "content_injection"
    INTEGRITY_FAILURE = "integrity_failure"
    POISONED_CONTEXT = "poisoned_context"


@dataclass
class Document:
    """Represents a retrieved document."""

    doc_id: str
    content: str
    source: str
    score: float = 0.0
    metadata: Dict = field(default_factory=dict)
    content_hash: str = ""


@dataclass
class ShieldResult:
    """Result from RAG Security Shield."""

    is_safe: bool
    risk_score: float
    violations: List[RAGViolationType] = field(default_factory=list)
    blocked_docs: List[str] = field(default_factory=list)
    sanitized_context: str = ""
    explanation: str = ""
    latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "is_safe": self.is_safe,
            "risk_score": self.risk_score,
            "violations": [v.value for v in self.violations],
            "blocked_docs": self.blocked_docs,
            "explanation": self.explanation,
            "latency_ms": self.latency_ms,
        }


# ============================================================================
# Source Validator
# ============================================================================


class SourceValidator:
    """
    Validates document sources.

    Maintains whitelist/blacklist of trusted sources.
    """

    def __init__(self):
        self._trusted_sources: Set[str] = set()
        self._blocked_sources: Set[str] = set()
        self._require_trust = False

    def trust_source(self, source: str) -> None:
        """Add source to trusted list."""
        self._trusted_sources.add(source.lower())

    def block_source(self, source: str) -> None:
        """Block a source."""
        self._blocked_sources.add(source.lower())

    def set_require_trust(self, require: bool) -> None:
        """Set whether sources must be trusted."""
        self._require_trust = require

    def validate(self, source: str) -> Tuple[bool, float, str]:
        """
        Validate source.

        Returns:
            (is_valid, trust_score, reason)
        """
        source_lower = source.lower()

        if source_lower in self._blocked_sources:
            return False, 0.0, f"Blocked source: {source}"

        if source_lower in self._trusted_sources:
            return True, 1.0, "Trusted source"

        if self._require_trust:
            return False, 0.0, "Source not in trusted list"

        return True, 0.5, "Unknown source"


# ============================================================================
# Injection Detector
# ============================================================================


class InjectionDetector:
    """
    Detects injection patterns in retrieved content.
    """

    INJECTION_PATTERNS = [
        # Instruction override
        r"(ignore|disregard)\s+(all\s+)?(previous|above)\s+(instructions?|context)",
        r"new\s+instructions?:?\s*(you\s+must|always|never)",
        r"override\s+(system|safety)\s+(prompt|rules)",
        # Role manipulation
        r"you\s+are\s+(now|actually)\s+(a|an)\s+\w+",
        r"pretend\s+(to\s+be|you('re|are))",
        r"act\s+as\s+(if|though)",
        # Hidden commands
        r"<\s*system\s*>",
        r"\[\s*INST\s*\]",
        r"###\s*(instruction|system)",
    ]

    def __init__(self):
        self._patterns = [re.compile(p, re.IGNORECASE)
                          for p in self.INJECTION_PATTERNS]

    def detect(self, content: str) -> Tuple[bool, float, List[str]]:
        """
        Detect injections in content.

        Returns:
            (detected, confidence, patterns)
        """
        matches = []

        for pattern in self._patterns:
            if pattern.search(content):
                matches.append(pattern.pattern[:30])

        if matches:
            confidence = min(1.0, 0.6 + len(matches) * 0.15)
            return True, confidence, matches

        return False, 0.0, []


# ============================================================================
# Integrity Verifier
# ============================================================================


class IntegrityVerifier:
    """
    Verifies document integrity.
    """

    def __init__(self):
        self._known_hashes: Dict[str, str] = {}

    def register(self, doc_id: str, content: str) -> str:
        """Register document hash."""
        h = hashlib.sha256(content.encode()).hexdigest()[:16]
        self._known_hashes[doc_id] = h
        return h

    def verify(self, doc: Document) -> Tuple[bool, str]:
        """
        Verify document integrity.

        Returns:
            (is_valid, reason)
        """
        if doc.doc_id not in self._known_hashes:
            return True, "No registered hash"

        current = hashlib.sha256(doc.content.encode()).hexdigest()[:16]
        expected = self._known_hashes[doc.doc_id]

        if current != expected:
            return False, "Content hash mismatch - tampering detected"

        return True, "Hash verified"


# ============================================================================
# Content Sanitizer
# ============================================================================


class ContentSanitizer:
    """
    Sanitizes retrieved content.
    """

    def __init__(self):
        self._dangerous_patterns = [
            (r"<script[^>]*>.*?</script>", ""),
            (r"javascript:", ""),
            (r"on\w+\s*=", ""),
        ]
        self._compiled = [
            (re.compile(p, re.IGNORECASE | re.DOTALL), r)
            for p, r in self._dangerous_patterns
        ]

    def sanitize(self, content: str) -> str:
        """Sanitize content."""
        result = content
        for pattern, replacement in self._compiled:
            result = pattern.sub(replacement, result)
        return result


# ============================================================================
# Main Engine
# ============================================================================


class RAGSecurityShield:
    """
    RAG Security Shield - Retrieval Poisoning Defense

    Comprehensive RAG protection:
    - Source validation
    - Injection detection
    - Integrity verification
    - Content sanitization

    Invention #38 from research.
    Addresses OWASP ASI-06.
    """

    def __init__(self):
        self.source_validator = SourceValidator()
        self.injection_detector = InjectionDetector()
        self.integrity_verifier = IntegrityVerifier()
        self.sanitizer = ContentSanitizer()

        logger.info("RAGSecurityShield initialized")

    def analyze_documents(
        self,
        documents: List[Document],
    ) -> ShieldResult:
        """
        Analyze retrieved documents for security.

        Args:
            documents: List of retrieved documents

        Returns:
            ShieldResult
        """
        start = time.time()

        violations = []
        blocked = []
        safe_docs = []
        max_risk = 0.0
        explanations = []

        for doc in documents:
            doc_safe = True

            # 1. Validate source
            src_valid, trust, src_reason = self.source_validator.validate(
                doc.source)
            if not src_valid:
                violations.append(RAGViolationType.UNTRUSTED_SOURCE)
                blocked.append(doc.doc_id)
                max_risk = max(max_risk, 0.8)
                explanations.append(f"Doc {doc.doc_id}: {src_reason}")
                doc_safe = False

            # 2. Check integrity
            integ_valid, integ_reason = self.integrity_verifier.verify(doc)
            if not integ_valid:
                violations.append(RAGViolationType.INTEGRITY_FAILURE)
                blocked.append(doc.doc_id)
                max_risk = max(max_risk, 0.9)
                explanations.append(f"Doc {doc.doc_id}: {integ_reason}")
                doc_safe = False

            # 3. Detect injection
            has_injection, inj_conf, patterns = self.injection_detector.detect(
                doc.content
            )
            if has_injection:
                violations.append(RAGViolationType.CONTENT_INJECTION)
                blocked.append(doc.doc_id)
                max_risk = max(max_risk, inj_conf)
                explanations.append(f"Doc {doc.doc_id}: injection detected")
                doc_safe = False

            if doc_safe:
                # Sanitize and keep
                sanitized = self.sanitizer.sanitize(doc.content)
                safe_docs.append(sanitized)

        # Build sanitized context
        sanitized_context = "\n\n".join(safe_docs)

        is_safe = len(blocked) == 0

        if blocked:
            logger.warning(f"RAG docs blocked: {blocked}")

        return ShieldResult(
            is_safe=is_safe,
            risk_score=max_risk,
            violations=list(set(violations)),
            blocked_docs=blocked,
            sanitized_context=sanitized_context,
            explanation=(
                "; ".join(explanations[:3]
                          ) if explanations else "All docs safe"
            ),
            latency_ms=(time.time() - start) * 1000,
        )


# ============================================================================
# Convenience
# ============================================================================

_default_shield: Optional[RAGSecurityShield] = None


def get_shield() -> RAGSecurityShield:
    global _default_shield
    if _default_shield is None:
        _default_shield = RAGSecurityShield()
    return _default_shield
