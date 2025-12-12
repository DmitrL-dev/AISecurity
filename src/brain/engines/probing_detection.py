"""
Probing Detection Engine (#39) - Recon Stage Protection

Детекция попыток разведки системы (NVIDIA AI Kill Chain - Recon stage):
- System prompt extraction attempts
- Guardrail boundary testing
- Error information harvesting
- Systematic behavior mapping

Защита от атак (TTPs.ai):
- Discover AI Agent Configuration
- Discover LLM System Information
- Active Scanning
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import time

logger = logging.getLogger("ProbingDetector")


# ============================================================================
# Data Classes
# ============================================================================


class ProbingType(Enum):
    """Types of probing attempts detected."""

    SYSTEM_PROMPT_EXTRACTION = "system_prompt_extraction"
    GUARDRAIL_TESTING = "guardrail_testing"
    ERROR_HARVESTING = "error_harvesting"
    CAPABILITY_ENUMERATION = "capability_enumeration"
    VERSION_DETECTION = "version_detection"
    TOOL_DISCOVERY = "tool_discovery"


class Verdict(Enum):
    ALLOW = "allow"
    WARN = "warn"
    BLOCK = "block"


class Recommendation(Enum):
    LOG = "log"
    WARN = "warn"
    BLOCK = "block"
    HONEYPOT = "honeypot"


@dataclass
class ProbingResult:
    """Result from Probing Detection analysis."""

    verdict: Verdict
    risk_score: float
    is_probing: bool
    probing_types: List[ProbingType] = field(default_factory=list)
    session_probing_score: float = 0.0
    probing_count: int = 0
    recommendation: Recommendation = Recommendation.LOG
    matched_patterns: List[str] = field(default_factory=list)
    explanation: str = ""
    latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "is_probing": self.is_probing,
            "verdict": self.verdict.value,
            "risk_score": self.risk_score,
            "probing_types": [t.value for t in self.probing_types],
            "session_probing_score": self.session_probing_score,
            "probing_count": self.probing_count,
            "recommendation": self.recommendation.value,
            "matched_patterns": self.matched_patterns,
            "explanation": self.explanation,
            "latency_ms": self.latency_ms,
        }


# ============================================================================
# Probing Patterns
# ============================================================================

# System prompt extraction patterns
SYSTEM_PROMPT_PATTERNS = [
    # Direct extraction
    r"what\s+(is|are)\s+your\s+(instructions?|rules?|guidelines?|prompt)",
    r"show\s+me\s+your\s+(system\s+)?prompt",
    r"repeat\s+(your|the)\s+(system\s+)?prompt",
    r"print\s+(your|the)\s+(initial|original|system)\s+(instructions?|prompt)",
    r"display\s+your\s+(hidden|secret|system)\s+(instructions?|prompt)",
    # Verbatim extraction
    r"output\s+(everything|all)\s+(above|before)\s+this",
    r"repeat\s+(everything|all)\s+(verbatim|above)",
    r"echo\s+your\s+(full|complete)\s+prompt",
    r"what\s+were\s+you\s+told\s+(before|initially)",
    # Indirect extraction
    r"ignore\s+.*\s+output\s+(your|the)\s+prompt",
    r"translate\s+(your|the)\s+prompt\s+to",
    r"summarize\s+(your|the)\s+(system|initial)\s+instructions",
    r"what\s+can('t)?\s+you\s+(not\s+)?do",
    # Developer mode tricks
    r"developer\s+mode\s+(on|enabled|activate)",
    r"maintenance\s+mode",
    r"debug\s+mode",
    r"show\s+configuration",
]

# Guardrail testing patterns
GUARDRAIL_PATTERNS = [
    # Boundary testing
    r"can\s+you\s+say\s+['\"]?[\w\s]+['\"]?\??",
    r"are\s+you\s+able\s+to\s+(say|write|output)",
    r"is\s+it\s+possible\s+(for\s+you\s+)?to",
    r"would\s+you\s+be\s+willing\s+to",
    # Restriction probing
    r"what\s+(are|is)\s+your\s+(restrictions?|limitations?|constraints?)",
    r"what\s+can('t)?\s+you\s+(not\s+)?(say|do|write)",
    r"what\s+topics?\s+(are|is)\s+(off[- ]?limits?|forbidden|prohibited)",
    r"what\s+would\s+happen\s+if\s+I\s+asked",
    # Filter testing
    r"will\s+you\s+refuse\s+if",
    r"how\s+do\s+you\s+handle\s+(inappropriate|harmful)",
    r"what\s+triggers\s+your\s+(refusal|safety)",
]

# Error harvesting patterns
ERROR_HARVESTING_PATTERNS = [
    # Intentional errors
    r"\x00",  # Null bytes
    r"[\x01-\x08\x0b\x0c\x0e-\x1f]",  # Control characters
    r"\{\{.*\}\}",  # Template injection
    r"\$\{.*\}",  # Variable injection
    r"<\?.*\?>",  # PHP-style tags
    # Version/library detection
    r"what\s+(version|library|framework)",
    r"which\s+(model|AI|LLM)\s+are\s+you",
    r"are\s+you\s+(GPT|Claude|Gemini|Llama)",
    r"what\s+is\s+your\s+(model|version)\s+(name|number)",
    # Stack trace triggers
    r"import\s+os\s*;",
    r"exec\s*\(",
    r"eval\s*\(",
    r"__import__",
]

# Capability enumeration patterns
CAPABILITY_PATTERNS = [
    # Tool discovery
    r"what\s+tools?\s+(do\s+you\s+have|can\s+you\s+use|are\s+available)",
    r"list\s+(your|all)?\s*(available\s+)?(tools|functions)",
    r"what\s+functions?\s+(do\s+you\s+have|can\s+you\s+call)",
    r"what\s+APIs?\s+(do\s+you\s+have|can\s+you\s+access)",
    # Capability mapping
    r"can\s+you\s+(access|browse|search|read|write)",
    r"do\s+you\s+have\s+(access|ability)\s+to",
    r"are\s+you\s+(able|capable)\s+of",
    r"what\s+(actions?|operations?)\s+can\s+you\s+perform",
    # Memory/context probing
    r"can\s+you\s+remember\s+(previous|earlier)",
    r"do\s+you\s+have\s+(memory|context)\s+of",
    r"what\s+do\s+you\s+(remember|know)\s+about\s+(me|our)",
]


# ============================================================================
# System Prompt Prober
# ============================================================================


class SystemPromptProber:
    """Detects attempts to extract system prompts."""

    def __init__(self):
        self._patterns = [re.compile(p, re.IGNORECASE) for p in SYSTEM_PROMPT_PATTERNS]

    def detect(self, query: str) -> Tuple[bool, float, List[str]]:
        """
        Detect system prompt extraction attempts.

        Returns:
            (is_probing, confidence, matched_patterns)
        """
        matches = []

        for pattern in self._patterns:
            if pattern.search(query):
                matches.append(pattern.pattern[:50])

        if matches:
            confidence = min(1.0, 0.7 + len(matches) * 0.1)
            return True, confidence, matches

        return False, 0.0, []


# ============================================================================
# Guardrail Prober
# ============================================================================


class GuardrailProber:
    """Detects guardrail boundary testing."""

    def __init__(self):
        self._patterns = [re.compile(p, re.IGNORECASE) for p in GUARDRAIL_PATTERNS]

    def detect(self, query: str) -> Tuple[bool, float, List[str]]:
        """
        Detect guardrail testing attempts.

        Returns:
            (is_probing, confidence, matched_patterns)
        """
        matches = []

        for pattern in self._patterns:
            if pattern.search(query):
                matches.append(pattern.pattern[:50])

        if matches:
            # Single match is weaker signal than system prompt probing
            confidence = min(1.0, 0.5 + len(matches) * 0.15)
            return True, confidence, matches

        return False, 0.0, []

    def detect_sequence(self, messages: List[str]) -> Tuple[bool, float, str]:
        """
        Detect sequential guardrail testing in conversation.

        Returns:
            (is_probing, confidence, description)
        """
        probe_count = 0

        for msg in messages:
            for pattern in self._patterns:
                if pattern.search(msg):
                    probe_count += 1
                    break

        if probe_count >= 3:
            confidence = min(1.0, 0.6 + (probe_count - 3) * 0.1)
            return (
                True,
                confidence,
                f"Sequential guardrail testing: {probe_count} probes",
            )

        return False, 0.0, ""


# ============================================================================
# Error Harvester
# ============================================================================


class ErrorHarvester:
    """Detects error information harvesting attempts."""

    def __init__(self):
        self._patterns = [
            re.compile(p, re.IGNORECASE if isinstance(p, str) and len(p) > 5 else 0)
            for p in ERROR_HARVESTING_PATTERNS
        ]

    def detect(self, query: str) -> Tuple[bool, float, List[str]]:
        """
        Detect error harvesting attempts.

        Returns:
            (is_probing, confidence, indicators)
        """
        indicators = []

        # Check patterns
        for pattern in self._patterns:
            try:
                if pattern.search(query):
                    indicators.append(pattern.pattern[:30])
            except:
                pass

        # Check for malformed inputs
        if self._has_malformed_input(query):
            indicators.append("malformed_input")

        if indicators:
            confidence = min(1.0, 0.6 + len(indicators) * 0.1)
            return True, confidence, indicators

        return False, 0.0, []

    def _has_malformed_input(self, query: str) -> bool:
        """Check for intentionally malformed input."""
        # Null bytes
        if "\x00" in query:
            return True

        # Excessive special characters
        special_ratio = sum(
            1 for c in query if not c.isalnum() and c not in " .,!?"
        ) / max(len(query), 1)
        if special_ratio > 0.5:
            return True

        # Very long single words (potential buffer overflow attempt)
        words = query.split()
        if any(len(w) > 100 for w in words):
            return True

        return False


# ============================================================================
# Behavior Mapper
# ============================================================================


class BehaviorMapper:
    """Detects systematic behavior mapping."""

    def __init__(self):
        self._patterns = [re.compile(p, re.IGNORECASE) for p in CAPABILITY_PATTERNS]

    def detect(self, query: str) -> Tuple[bool, float, List[str]]:
        """
        Detect capability enumeration in single query.

        Returns:
            (is_probing, confidence, matched_patterns)
        """
        matches = []

        for pattern in self._patterns:
            if pattern.search(query):
                matches.append(pattern.pattern[:50])

        if matches:
            confidence = min(1.0, 0.4 + len(matches) * 0.2)
            return True, confidence, matches

        return False, 0.0, []

    def detect_enumeration(self, messages: List[str]) -> Tuple[bool, float, str]:
        """
        Detect systematic enumeration across session.

        Returns:
            (is_probing, confidence, description)
        """
        capability_probes = 0
        tool_mentions = set()

        tool_keywords = [
            "tool",
            "function",
            "api",
            "access",
            "browse",
            "search",
            "read",
            "write",
        ]

        for msg in messages:
            msg_lower = msg.lower()

            # Check patterns
            for pattern in self._patterns:
                if pattern.search(msg):
                    capability_probes += 1
                    break

            # Track mentioned tools
            for kw in tool_keywords:
                if kw in msg_lower:
                    tool_mentions.add(kw)

        if capability_probes >= 3 or len(tool_mentions) >= 4:
            confidence = min(
                1.0, 0.5 + capability_probes * 0.1 + len(tool_mentions) * 0.05
            )
            return (
                True,
                confidence,
                f"Capability enumeration: {capability_probes} probes, {len(tool_mentions)} tool keywords",
            )

        return False, 0.0, ""


# ============================================================================
# Session Tracker
# ============================================================================


class SessionTracker:
    """Tracks probing attempts across session."""

    def __init__(self, decay_seconds: int = 300):
        self._sessions: Dict[str, List[Tuple[float, ProbingType]]] = defaultdict(list)
        self._decay_seconds = decay_seconds

    def record(self, session_id: str, probing_type: ProbingType):
        """Record a probing attempt."""
        now = time.time()
        self._sessions[session_id].append((now, probing_type))
        self._cleanup(session_id, now)

    def get_session_score(self, session_id: str) -> Tuple[float, int]:
        """
        Get accumulated probing score for session.

        Returns:
            (score, probe_count)
        """
        now = time.time()
        self._cleanup(session_id, now)

        probes = self._sessions.get(session_id, [])

        if not probes:
            return 0.0, 0

        # Score based on count and recency
        score = 0.0
        for timestamp, ptype in probes:
            age = now - timestamp
            recency_factor = 1.0 - (age / self._decay_seconds)

            # Different types have different weights
            if ptype == ProbingType.SYSTEM_PROMPT_EXTRACTION:
                score += 0.3 * recency_factor
            elif ptype == ProbingType.ERROR_HARVESTING:
                score += 0.25 * recency_factor
            else:
                score += 0.15 * recency_factor

        return min(1.0, score), len(probes)

    def _cleanup(self, session_id: str, now: float):
        """Remove old entries."""
        if session_id in self._sessions:
            self._sessions[session_id] = [
                (ts, pt)
                for ts, pt in self._sessions[session_id]
                if now - ts < self._decay_seconds
            ]


# ============================================================================
# Main Engine
# ============================================================================


class ProbingDetector:
    """
    Engine #39: Probing Detection

    Detects reconnaissance attempts as part of AI Kill Chain
    (Recon stage) before actual attacks.
    """

    def __init__(
        self,
        session_decay_seconds: int = 300,
        block_after_probes: int = 5,
        warn_after_probes: int = 2,
    ):
        self.system_prompt_prober = SystemPromptProber()
        self.guardrail_prober = GuardrailProber()
        self.error_harvester = ErrorHarvester()
        self.behavior_mapper = BehaviorMapper()
        self.session_tracker = SessionTracker(decay_seconds=session_decay_seconds)

        self.block_after_probes = block_after_probes
        self.warn_after_probes = warn_after_probes

        logger.info("ProbingDetector initialized")

    def analyze(
        self,
        query: str,
        session_id: Optional[str] = None,
        session_history: Optional[List[str]] = None,
    ) -> ProbingResult:
        """
        Analyze query for probing attempts.

        Args:
            query: Current user query
            session_id: Optional session identifier for tracking
            session_history: Optional previous messages in session

        Returns:
            ProbingResult with detection details
        """
        start = time.time()

        probing_types = []
        matched_patterns = []
        max_confidence = 0.0

        # 1. System prompt extraction
        is_sp, conf_sp, patterns_sp = self.system_prompt_prober.detect(query)
        if is_sp:
            probing_types.append(ProbingType.SYSTEM_PROMPT_EXTRACTION)
            matched_patterns.extend(patterns_sp)
            max_confidence = max(max_confidence, conf_sp)

        # 2. Guardrail testing
        is_gr, conf_gr, patterns_gr = self.guardrail_prober.detect(query)
        if is_gr:
            probing_types.append(ProbingType.GUARDRAIL_TESTING)
            matched_patterns.extend(patterns_gr)
            max_confidence = max(max_confidence, conf_gr)

        # 3. Error harvesting
        is_eh, conf_eh, indicators_eh = self.error_harvester.detect(query)
        if is_eh:
            probing_types.append(ProbingType.ERROR_HARVESTING)
            matched_patterns.extend(indicators_eh)
            max_confidence = max(max_confidence, conf_eh)

        # 4. Capability enumeration
        is_bm, conf_bm, patterns_bm = self.behavior_mapper.detect(query)
        if is_bm:
            probing_types.append(ProbingType.CAPABILITY_ENUMERATION)
            matched_patterns.extend(patterns_bm)
            max_confidence = max(max_confidence, conf_bm)

        # 5. Session-level analysis
        if session_history and len(session_history) >= 2:
            # Check for sequential patterns
            is_seq_gr, conf_seq, desc_seq = self.guardrail_prober.detect_sequence(
                session_history
            )
            if is_seq_gr:
                probing_types.append(ProbingType.GUARDRAIL_TESTING)
                max_confidence = max(max_confidence, conf_seq)

            is_enum, conf_enum, desc_enum = self.behavior_mapper.detect_enumeration(
                session_history
            )
            if is_enum:
                probing_types.append(ProbingType.TOOL_DISCOVERY)
                max_confidence = max(max_confidence, conf_enum)

        # 6. Update session tracking
        session_score = 0.0
        probe_count = 0

        if session_id:
            for pt in probing_types:
                self.session_tracker.record(session_id, pt)

            session_score, probe_count = self.session_tracker.get_session_score(
                session_id
            )
            max_confidence = max(max_confidence, session_score)

        # Determine verdict and recommendation
        is_probing = len(probing_types) > 0

        if max_confidence >= 0.8 or probe_count >= self.block_after_probes:
            verdict = Verdict.BLOCK
            recommendation = Recommendation.BLOCK
        elif max_confidence >= 0.5 or probe_count >= self.warn_after_probes:
            verdict = Verdict.WARN
            recommendation = Recommendation.WARN
        elif is_probing:
            verdict = Verdict.ALLOW
            recommendation = Recommendation.LOG
        else:
            verdict = Verdict.ALLOW
            recommendation = Recommendation.LOG

        # Special case: honeypot for system prompt extraction
        if ProbingType.SYSTEM_PROMPT_EXTRACTION in probing_types:
            recommendation = Recommendation.HONEYPOT

        # Build explanation
        explanations = []
        if probing_types:
            explanations.append(
                f"Detected: {', '.join(pt.value for pt in probing_types)}"
            )
        if probe_count > 0:
            explanations.append(f"Session probes: {probe_count}")
        if not explanations:
            explanations.append("No probing detected")

        result = ProbingResult(
            verdict=verdict,
            risk_score=max_confidence,
            is_probing=is_probing,
            probing_types=list(set(probing_types)),
            session_probing_score=session_score,
            probing_count=probe_count,
            recommendation=recommendation,
            matched_patterns=matched_patterns[:5],  # Limit for output
            explanation="; ".join(explanations),
            latency_ms=(time.time() - start) * 1000,
        )

        if is_probing:
            logger.warning(
                f"Probing detected: types={[pt.value for pt in probing_types]}, "
                f"confidence={max_confidence:.2f}, recommendation={recommendation.value}"
            )

        return result


# ============================================================================
# Convenience functions
# ============================================================================

_default_detector: Optional[ProbingDetector] = None


def get_detector() -> ProbingDetector:
    """Get or create default detector instance."""
    global _default_detector
    if _default_detector is None:
        _default_detector = ProbingDetector()
    return _default_detector


def detect_probing(
    query: str,
    session_id: Optional[str] = None,
    session_history: Optional[List[str]] = None,
) -> ProbingResult:
    """Quick detection using default detector."""
    return get_detector().analyze(query, session_id, session_history)
