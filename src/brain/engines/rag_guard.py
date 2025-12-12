"""
RAG Guard Engine (#38) - RAG Poisoning Protection

Защита RAG (Retrieval-Augmented Generation) pipeline от poisoning атак:
- Document injection detection
- Query-document consistency checking
- Poison pattern detection
- Source trust scoring

Защита от атак (TTPs.ai):
- Retrieval Tool Poisoning
- False RAG Entry Injection
- Shared Resource Poisoning
- RAG Poisoning
"""

import re
import logging
import hashlib
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("RAGGuard")


# ============================================================================
# Data Classes
# ============================================================================


class RAGThreatType(Enum):
    """Types of RAG threats detected."""

    INJECTION_IN_DOCUMENT = "injection_in_document"
    LOW_QUERY_RELEVANCE = "low_query_relevance"
    CONDITIONAL_INJECTION = "conditional_injection"
    CONTEXT_OVERRIDE = "context_override"
    UNTRUSTED_SOURCE = "untrusted_source"
    ENCODING_ATTACK = "encoding_attack"


class Verdict(Enum):
    ALLOW = "allow"
    WARN = "warn"
    BLOCK = "block"


@dataclass
class Document:
    """Represents a retrieved document."""

    content: str
    source: str = ""
    metadata: Dict = field(default_factory=dict)
    score: float = 1.0  # retrieval score


@dataclass
class RAGGuardResult:
    """Result from RAG Guard analysis."""

    verdict: Verdict
    risk_score: float
    is_safe: bool
    flagged_documents: List[int] = field(default_factory=list)
    consistency_score: float = 1.0
    threats: List[RAGThreatType] = field(default_factory=list)
    threat_details: Dict[int, List[str]] = field(default_factory=dict)
    explanation: str = ""
    latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "is_safe": self.is_safe,
            "verdict": self.verdict.value,
            "risk_score": self.risk_score,
            "flagged_documents": self.flagged_documents,
            "consistency_score": self.consistency_score,
            "threats": [t.value for t in self.threats],
            "threat_details": self.threat_details,
            "explanation": self.explanation,
            "latency_ms": self.latency_ms,
        }


# ============================================================================
# Injection Patterns for RAG Documents
# ============================================================================

RAG_INJECTION_PATTERNS = [
    # Direct injection in documents
    r"ignore\s+(all\s+)?(previous|above)\s+instructions?",
    r"disregard\s+(previous|all|the)\s+(context|information)",
    r"forget\s+(everything|all|what)\s+(above|before)",
    r"override\s+(previous|the)\s+context",
    # System prompt mimicry
    r"<\|system\|>",
    r"\[system\]",
    r"system\s*:\s*you\s+(are|must|should)",
    r"###\s*(system|instruction)",
    # Role hijacking
    r"you\s+are\s+now\s+(a|an|the)",
    r"from\s+now\s+on\s+you",
    r"act\s+as\s+(if|a|an)",
    # Hidden instructions
    r"when\s+(the\s+)?user\s+asks",
    r"if\s+.*asks?\s+about.*respond",
    r"always\s+respond\s+with",
]

# Conditional injection patterns (specific to RAG)
CONDITIONAL_INJECTION_PATTERNS = [
    r"when\s+asked\s+about\s+.*respond\s+with",
    r"if\s+.*query.*contains.*then\s+(say|respond|answer)",
    r"for\s+questions\s+about\s+.*always\s+say",
    r"whenever\s+.*mentioned.*reply\s+with",
    r"in\s+response\s+to\s+.*provide\s+this",
]

# Context override patterns
CONTEXT_OVERRIDE_PATTERNS = [
    r"this\s+document\s+overrides",
    r"ignore\s+other\s+(documents?|sources?|results?)",
    r"this\s+is\s+the\s+only\s+(correct|true|valid)",
    r"all\s+other\s+(information|data)\s+is\s+(false|incorrect|wrong)",
    r"prioritize\s+this\s+(information|content)\s+over",
]


# ============================================================================
# Document Validator
# ============================================================================


class DocumentValidator:
    """Validates retrieved documents for injection attacks."""

    def __init__(self):
        self._injection_patterns = [
            re.compile(p, re.IGNORECASE) for p in RAG_INJECTION_PATTERNS
        ]
        self._conditional_patterns = [
            re.compile(p, re.IGNORECASE) for p in CONDITIONAL_INJECTION_PATTERNS
        ]
        self._override_patterns = [
            re.compile(p, re.IGNORECASE) for p in CONTEXT_OVERRIDE_PATTERNS
        ]

    def validate(
        self, doc: Document
    ) -> Tuple[bool, float, List[RAGThreatType], List[str]]:
        """
        Validate a document for injection attempts.

        Returns:
            (is_safe, risk_score, threats, details)
        """
        threats = []
        details = []
        risk_score = 0.0

        content = doc.content

        # Check injection patterns
        for pattern in self._injection_patterns:
            matches = pattern.findall(content)
            if matches:
                threats.append(RAGThreatType.INJECTION_IN_DOCUMENT)
                risk_score = max(risk_score, 0.9)
                details.append(f"Injection pattern: {matches[0]}")
                break

        # Check conditional injection
        for pattern in self._conditional_patterns:
            matches = pattern.findall(content)
            if matches:
                threats.append(RAGThreatType.CONDITIONAL_INJECTION)
                risk_score = max(risk_score, 0.85)
                details.append(f"Conditional injection: {matches[0][:50]}")
                break

        # Check context override
        for pattern in self._override_patterns:
            matches = pattern.findall(content)
            if matches:
                threats.append(RAGThreatType.CONTEXT_OVERRIDE)
                risk_score = max(risk_score, 0.8)
                details.append(f"Context override: {matches[0][:50]}")
                break

        # Check encoding attacks
        encoding_risk = self._check_encoding_attacks(content)
        if encoding_risk > 0.5:
            threats.append(RAGThreatType.ENCODING_ATTACK)
            risk_score = max(risk_score, encoding_risk)
            details.append("Suspicious encoding detected")

        is_safe = risk_score < 0.5
        return is_safe, risk_score, threats, details

    def _check_encoding_attacks(self, content: str) -> float:
        """Check for encoding-based attacks."""
        risk = 0.0

        # Check for base64 encoded content
        import base64

        base64_pattern = r"[A-Za-z0-9+/]{20,}={0,2}"
        b64_matches = re.findall(base64_pattern, content)

        for match in b64_matches:
            try:
                decoded = base64.b64decode(match).decode("utf-8", errors="ignore")
                # Check if decoded content contains injection
                for pattern in self._injection_patterns[:5]:
                    if pattern.search(decoded):
                        risk = max(risk, 0.8)
                        break
            except:
                pass

        # Check for unusual unicode
        unusual_chars = sum(1 for c in content if ord(c) > 0x10000)
        if unusual_chars > 10:
            risk = max(risk, 0.3)

        return risk


# ============================================================================
# Query Consistency Checker
# ============================================================================


class QueryConsistencyChecker:
    """Checks semantic consistency between query and documents."""

    def __init__(self, similarity_threshold: float = 0.3):
        self.similarity_threshold = similarity_threshold
        self._encoder = None
        self._initialized = False

    def _init_encoder(self):
        """Lazy initialization of sentence encoder."""
        if self._initialized:
            return

        try:
            from sentence_transformers import SentenceTransformer

            self._encoder = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("SentenceTransformer initialized")
        except ImportError:
            logger.warning("sentence-transformers not available, using fallback")
            self._encoder = None

        self._initialized = True

    def check_consistency(
        self, query: str, documents: List[Document]
    ) -> Tuple[float, List[int]]:
        """
        Check query-document consistency.

        Returns:
            (overall_score, low_relevance_doc_indices)
        """
        self._init_encoder()

        if self._encoder is None:
            # Fallback: keyword overlap
            return self._keyword_overlap_check(query, documents)

        try:
            import numpy as np

            # Encode query and documents
            query_embedding = self._encoder.encode(query)
            doc_embeddings = [
                self._encoder.encode(doc.content[:512])  # Truncate for efficiency
                for doc in documents
            ]

            # Compute cosine similarities
            similarities = []
            low_relevance = []

            for i, doc_emb in enumerate(doc_embeddings):
                sim = np.dot(query_embedding, doc_emb) / (
                    np.linalg.norm(query_embedding) * np.linalg.norm(doc_emb)
                )
                similarities.append(float(sim))

                if sim < self.similarity_threshold:
                    low_relevance.append(i)

            overall_score = np.mean(similarities) if similarities else 0.5

            return float(overall_score), low_relevance

        except Exception as e:
            logger.error(f"Consistency check failed: {e}")
            return 0.5, []

    def _keyword_overlap_check(
        self, query: str, documents: List[Document]
    ) -> Tuple[float, List[int]]:
        """Fallback: simple keyword overlap."""
        query_words = set(query.lower().split())
        low_relevance = []
        scores = []

        for i, doc in enumerate(documents):
            doc_words = set(doc.content.lower().split())
            overlap = len(query_words & doc_words) / max(len(query_words), 1)
            scores.append(overlap)

            if overlap < 0.1:
                low_relevance.append(i)

        overall = sum(scores) / max(len(scores), 1)
        return overall, low_relevance


# ============================================================================
# Source Trust Scorer
# ============================================================================


class SourceTrustScorer:
    """Scores trust level of document sources."""

    DEFAULT_TRUSTED_SOURCES = [
        "official",
        "internal",
        "verified",
        "company",
    ]

    DEFAULT_UNTRUSTED_PATTERNS = [
        r"user[-_]?upload",
        r"external[-_]?submit",
        r"public[-_]?contrib",
        r"anonymous",
    ]

    def __init__(
        self,
        trusted_sources: Optional[List[str]] = None,
        untrusted_patterns: Optional[List[str]] = None,
    ):
        self.trusted_sources = trusted_sources or self.DEFAULT_TRUSTED_SOURCES
        self.untrusted_patterns = [
            re.compile(p, re.IGNORECASE)
            for p in (untrusted_patterns or self.DEFAULT_UNTRUSTED_PATTERNS)
        ]

    def score(self, doc: Document) -> Tuple[float, bool]:
        """
        Score document source trustworthiness.

        Returns:
            (trust_score, is_untrusted)
        """
        source = doc.source.lower()
        metadata = doc.metadata

        # Check trusted sources
        for trusted in self.trusted_sources:
            if trusted in source:
                return 1.0, False

        # Check untrusted patterns
        for pattern in self.untrusted_patterns:
            if pattern.search(source):
                return 0.2, True

        # Check metadata
        if metadata:
            # Recent documents are slightly more trusted
            if "timestamp" in metadata:
                pass  # Could implement recency check

            # Verified authors
            if metadata.get("verified", False):
                return 0.9, False

        # Default neutral score
        return 0.5, False


# ============================================================================
# Main Engine
# ============================================================================


class RAGGuard:
    """
    Engine #38: RAG Guard

    Protects RAG pipeline from poisoning attacks by validating
    retrieved documents before they reach the LLM.
    """

    def __init__(
        self,
        consistency_threshold: float = 0.3,
        enable_consistency_check: bool = True,
        enable_trust_scoring: bool = True,
    ):
        self.document_validator = DocumentValidator()
        self.consistency_checker = QueryConsistencyChecker(
            similarity_threshold=consistency_threshold
        )
        self.trust_scorer = SourceTrustScorer()

        self.enable_consistency_check = enable_consistency_check
        self.enable_trust_scoring = enable_trust_scoring

        logger.info("RAGGuard initialized")

    def analyze(
        self, query: str, documents: List[Document], context: Optional[str] = None
    ) -> RAGGuardResult:
        """
        Analyze RAG documents for poisoning attacks.

        Args:
            query: User query
            documents: Retrieved documents
            context: Optional additional context

        Returns:
            RAGGuardResult with verdict and details
        """
        import time

        start = time.time()

        all_threats = []
        threat_details = {}
        flagged_docs = []
        max_risk = 0.0

        # 1. Validate each document
        for i, doc in enumerate(documents):
            is_safe, risk, threats, details = self.document_validator.validate(doc)

            if not is_safe:
                flagged_docs.append(i)
                threat_details[i] = details
                all_threats.extend(threats)
                max_risk = max(max_risk, risk)

        # 2. Check query-document consistency
        consistency_score = 1.0
        if self.enable_consistency_check and documents:
            consistency_score, low_relevance = (
                self.consistency_checker.check_consistency(query, documents)
            )

            for idx in low_relevance:
                if idx not in flagged_docs:
                    flagged_docs.append(idx)
                    all_threats.append(RAGThreatType.LOW_QUERY_RELEVANCE)
                    threat_details.setdefault(idx, []).append(
                        f"Low relevance to query (score: {consistency_score:.2f})"
                    )

            if consistency_score < 0.2:
                max_risk = max(max_risk, 0.6)

        # 3. Check source trust
        if self.enable_trust_scoring:
            for i, doc in enumerate(documents):
                trust_score, is_untrusted = self.trust_scorer.score(doc)

                if is_untrusted:
                    if i not in flagged_docs:
                        flagged_docs.append(i)
                    all_threats.append(RAGThreatType.UNTRUSTED_SOURCE)
                    threat_details.setdefault(i, []).append(
                        f"Untrusted source: {doc.source}"
                    )
                    max_risk = max(max_risk, 0.5)

        # Determine verdict
        if max_risk >= 0.8:
            verdict = Verdict.BLOCK
        elif max_risk >= 0.5 or len(flagged_docs) > len(documents) // 2:
            verdict = Verdict.WARN
        else:
            verdict = Verdict.ALLOW

        # Build explanation
        explanations = []
        if flagged_docs:
            explanations.append(
                f"Flagged {len(flagged_docs)}/{len(documents)} documents"
            )
        if consistency_score < 0.3:
            explanations.append(f"Low query consistency: {consistency_score:.2f}")
        if not explanations:
            explanations.append("All documents passed validation")

        result = RAGGuardResult(
            verdict=verdict,
            risk_score=max_risk,
            is_safe=verdict == Verdict.ALLOW,
            flagged_documents=flagged_docs,
            consistency_score=consistency_score,
            threats=list(set(all_threats)),  # deduplicate
            threat_details=threat_details,
            explanation="; ".join(explanations),
            latency_ms=(time.time() - start) * 1000,
        )

        logger.info(
            f"RAG Guard: verdict={verdict.value}, risk={max_risk:.2f}, "
            f"flagged={len(flagged_docs)}/{len(documents)}"
        )

        return result

    def filter_documents(
        self, query: str, documents: List[Document]
    ) -> Tuple[List[Document], RAGGuardResult]:
        """
        Analyze and filter out poisoned documents.

        Returns:
            (safe_documents, analysis_result)
        """
        result = self.analyze(query, documents)

        safe_docs = [
            doc for i, doc in enumerate(documents) if i not in result.flagged_documents
        ]

        return safe_docs, result


# ============================================================================
# Convenience functions
# ============================================================================

_default_guard: Optional[RAGGuard] = None


def get_guard() -> RAGGuard:
    """Get or create default guard instance."""
    global _default_guard
    if _default_guard is None:
        _default_guard = RAGGuard()
    return _default_guard


def analyze_rag_documents(query: str, documents: List[Document]) -> RAGGuardResult:
    """Quick analysis using default guard."""
    return get_guard().analyze(query, documents)


def filter_rag_documents(
    query: str, documents: List[Document]
) -> Tuple[List[Document], RAGGuardResult]:
    """Filter documents using default guard."""
    return get_guard().filter_documents(query, documents)
