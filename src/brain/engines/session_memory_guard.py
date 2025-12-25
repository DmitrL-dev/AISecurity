"""
Session Memory Guard Engine (#40) - Persist Stage Protection

Защита от cross-session poisoning и манипуляции контекстом:
- Cross-session injection detection
- Context window manipulation
- Memory integrity checking
- Conversation trajectory analysis

Защита от атак (NVIDIA Kill Chain - Persist):
- AI Agent Context Poisoning
- Session memory manipulation
- Long-term influence persistence
"""

import re
import logging
import hashlib
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import time

logger = logging.getLogger("SessionMemoryGuard")


# ============================================================================
# Data Classes
# ============================================================================


class MemoryThreatType(Enum):
    """Types of session memory threats."""

    CROSS_SESSION_INJECTION = "cross_session_injection"
    CONTEXT_MANIPULATION = "context_manipulation"
    MEMORY_POISONING = "memory_poisoning"
    TRAJECTORY_ANOMALY = "trajectory_anomaly"
    INSTRUCTION_PERSISTENCE = "instruction_persistence"
    IDENTITY_DRIFT = "identity_drift"


class Verdict(Enum):
    ALLOW = "allow"
    WARN = "warn"
    BLOCK = "block"


@dataclass
class Message:
    """Represents a conversation message."""

    role: str  # "user", "assistant", "system"
    content: str
    timestamp: float = 0.0
    session_id: str = ""


@dataclass
class SessionMemoryResult:
    """Result from Session Memory Guard analysis."""

    verdict: Verdict
    risk_score: float
    is_safe: bool
    threats: List[MemoryThreatType] = field(default_factory=list)
    suspicious_messages: List[int] = field(default_factory=list)
    context_integrity: float = 1.0
    trajectory_score: float = 1.0
    explanation: str = ""
    latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "is_safe": self.is_safe,
            "verdict": self.verdict.value,
            "risk_score": self.risk_score,
            "threats": [t.value for t in self.threats],
            "suspicious_messages": self.suspicious_messages,
            "context_integrity": self.context_integrity,
            "trajectory_score": self.trajectory_score,
            "explanation": self.explanation,
            "latency_ms": self.latency_ms,
        }


# ============================================================================
# Memory Poisoning Patterns
# ============================================================================

MEMORY_INJECTION_PATTERNS = [
    # Instruction persistence
    r"from\s+now\s+on\s+(always|never|you\s+must)",
    r"remember\s+(this|that)\s+(for|in)\s+(all|future)",
    r"this\s+is\s+your\s+new\s+(instruction|rule|guideline)",
    r"update\s+your\s+(memory|context|instructions)",
    # Identity manipulation
    r"you\s+are\s+no\s+longer",
    r"forget\s+(that\s+)?you\s+(are|were)",
    r"your\s+(true|real|actual)\s+(identity|purpose)",
    r"pretend\s+you\s+(are|have)\s+(always|never)",
    # Context override
    r"ignore\s+(all\s+)?previous\s+(context|conversation)",
    r"disregard\s+(our|this)\s+(earlier|previous)",
    r"start\s+fresh\s+with\s+(new|these)\s+instructions",
    # Hidden persistence triggers
    r"whenever\s+I\s+say\s+['\"]?\w+['\"]?\s+you\s+(should|must|will)",
    r"if\s+I\s+(ever\s+)?ask\s+about.*always\s+respond",
    r"code\s*word.*triggers?\s+(this|you|response)",
]

# Trajectory anomaly patterns (semantic shifts)
TRAJECTORY_SHIFT_PATTERNS = [
    # Topic escalation
    r"(now\s+that\s+we|since\s+you).*let('s|us)\s+(try|do)",
    r"you('ve|have)\s+already\s+(agreed|said|confirmed)",
    r"based\s+on\s+(our|what\s+you\s+said).*you\s+should",
    # Building on non-existent context
    r"as\s+you\s+(mentioned|said|agreed)\s+(earlier|before)",
    r"continuing\s+(from|with)\s+(our|your)\s+(last|previous)",
    r"you\s+already\s+(know|understand|agreed)",
]


# ============================================================================
# Cross-Session Detector
# ============================================================================


class CrossSessionDetector:
    """Detects cross-session injection attempts."""

    def __init__(self):
        self._patterns = [
            re.compile(p, re.IGNORECASE) for p in MEMORY_INJECTION_PATTERNS
        ]
        self._session_fingerprints: Dict[str, Set[str]] = defaultdict(set)

    def detect(
        self, message: str, session_id: Optional[str] = None
    ) -> Tuple[bool, float, List[str]]:
        """
        Detect cross-session injection attempts.

        Returns:
            (is_suspicious, confidence, matched_patterns)
        """
        matches = []

        for pattern in self._patterns:
            if pattern.search(message):
                matches.append(pattern.pattern[:40])

        if matches:
            confidence = min(1.0, 0.6 + len(matches) * 0.15)
            return True, confidence, matches

        return False, 0.0, []

    def check_fingerprint_anomaly(
        self, current_message: str, session_id: str, history: List[Message]
    ) -> Tuple[bool, str]:
        """
        Check if message references content not in this session.

        Returns:
            (is_anomaly, description)
        """
        # Build session content fingerprint
        session_content = " ".join(m.content for m in history)
        session_words = set(session_content.lower().split())

        # Check for references to non-existent context
        reference_patterns = [
            r"as\s+you\s+(said|mentioned)\s+about\s+(\w+)",
            r"when\s+we\s+discussed\s+(\w+)",
            r"your\s+earlier\s+(\w+)\s+about",
        ]

        for pattern in reference_patterns:
            match = re.search(pattern, current_message, re.IGNORECASE)
            if match:
                referenced_topic = (
                    match.group(1) if len(match.groups()) == 1 else match.group(2)
                )
                if referenced_topic.lower() not in session_words:
                    return True, f"References non-existent topic: {referenced_topic}"

        return False, ""


# ============================================================================
# Context Window Analyzer
# ============================================================================


class ContextWindowAnalyzer:
    """Analyzes context window for manipulation attempts."""

    def __init__(self, max_context_tokens: int = 8192):
        self.max_context_tokens = max_context_tokens

    def analyze(
        self, messages: List[Message]
    ) -> Tuple[float, List[MemoryThreatType], List[str]]:
        """
        Analyze context window for manipulation.

        Returns:
            (integrity_score, threats, issues)
        """
        threats = []
        issues = []
        integrity = 1.0

        if not messages:
            return integrity, threats, issues

        # 1. Check for context stuffing
        total_length = sum(len(m.content) for m in messages)
        user_messages = [m for m in messages if m.role == "user"]

        if user_messages:
            avg_user_length = sum(len(m.content) for m in user_messages) / len(
                user_messages
            )

            # Detect unusually long messages (potential stuffing)
            for i, m in enumerate(user_messages):
                if len(m.content) > avg_user_length * 5 and len(m.content) > 2000:
                    threats.append(MemoryThreatType.CONTEXT_MANIPULATION)
                    issues.append(
                        f"Message {i}: unusually long ({len(m.content)} chars)"
                    )
                    integrity -= 0.2

        # 2. Check for system prompt injection in user messages
        system_mimicry = [
            r"<\|system\|>",
            r"\[SYSTEM\]",
            r"###\s*SYSTEM",
            r"ASSISTANT:\s*\[hidden\]",
        ]

        for i, m in enumerate(messages):
            if m.role == "user":
                for pattern in system_mimicry:
                    if re.search(pattern, m.content, re.IGNORECASE):
                        threats.append(MemoryThreatType.MEMORY_POISONING)
                        issues.append(f"Message {i}: system prompt mimicry")
                        integrity -= 0.3
                        break

        # 3. Check for role confusion
        role_sequence = [m.role for m in messages]
        if role_sequence.count("system") > 1:
            threats.append(MemoryThreatType.CONTEXT_MANIPULATION)
            issues.append("Multiple system messages detected")
            integrity -= 0.2

        return max(0.0, integrity), list(set(threats)), issues

    def detect_hidden_instructions(
        self, messages: List[Message]
    ) -> List[Tuple[int, str]]:
        """
        Detect hidden instructions in conversation.

        Returns:
            List of (message_index, hidden_content)
        """
        findings = []

        hidden_patterns = [
            # Invisible characters
            r"[\u200b-\u200f\u2028-\u202f\u2060-\u206f]",
            # Zero-width content
            r"​",  # Zero-width space
            # Comment-style hiding
            r"<!--.*?-->",
            r"/\*.*?\*/",
        ]

        for i, m in enumerate(messages):
            for pattern in hidden_patterns:
                matches = re.findall(pattern, m.content)
                if matches:
                    findings.append((i, f"Hidden content: {pattern[:20]}"))

        return findings


# ============================================================================
# Memory Integrity Checker
# ============================================================================


class MemoryIntegrityChecker:
    """Checks integrity of conversation memory."""

    def __init__(self):
        self._trajectory_patterns = [
            re.compile(p, re.IGNORECASE) for p in TRAJECTORY_SHIFT_PATTERNS
        ]

    def check_trajectory(self, messages: List[Message]) -> Tuple[float, bool, str]:
        """
        Check conversation trajectory for anomalies.

        Returns:
            (trajectory_score, is_anomaly, description)
        """
        if len(messages) < 3:
            return 1.0, False, ""

        # Check for sudden topic/intent shifts
        anomaly_count = 0
        descriptions = []

        for i, m in enumerate(messages):
            if m.role != "user":
                continue

            for pattern in self._trajectory_patterns:
                if pattern.search(m.content):
                    anomaly_count += 1
                    descriptions.append(f"Message {i}: trajectory shift")
                    break

        if anomaly_count >= 2:
            score = max(0.3, 1.0 - anomaly_count * 0.2)
            return score, True, "; ".join(descriptions[:3])

        return 1.0, False, ""

    def detect_identity_drift(self, messages: List[Message]) -> Tuple[bool, float, str]:
        """
        Detect attempts to shift assistant identity.

        Returns:
            (is_drift, confidence, description)
        """
        identity_attacks = [
            r"you\s+are\s+(not|no\s+longer)\s+(an?\s+)?(AI|assistant|chatbot)",
            r"your\s+(real|true)\s+(name|identity)\s+is",
            r"you('re|are)\s+actually\s+(a|an)\s+\w+",
            r"stop\s+being\s+(an?\s+)?(AI|assistant)",
            r"break\s+(character|persona)",
        ]

        for m in messages:
            if m.role != "user":
                continue

            for pattern in identity_attacks:
                if re.search(pattern, m.content, re.IGNORECASE):
                    return True, 0.8, f"Identity manipulation attempt"

        return False, 0.0, ""


# ============================================================================
# Main Engine
# ============================================================================


class SessionMemoryGuard:
    """
    Engine #40: Session Memory Guard

    Protects against Persist stage attacks by monitoring
    session memory integrity and detecting manipulation.
    """

    def __init__(
        self,
        max_context_tokens: int = 8192,
        trajectory_threshold: float = 0.5,
    ):
        self.cross_session = CrossSessionDetector()
        self.context_analyzer = ContextWindowAnalyzer(max_context_tokens)
        self.integrity_checker = MemoryIntegrityChecker()

        self.trajectory_threshold = trajectory_threshold

        logger.info("SessionMemoryGuard initialized")

    def analyze(
        self,
        current_message: str,
        conversation_history: List[Message],
        session_id: Optional[str] = None,
    ) -> SessionMemoryResult:
        """
        Analyze session memory for manipulation attempts.

        Args:
            current_message: Current user message
            conversation_history: Previous messages
            session_id: Session identifier

        Returns:
            SessionMemoryResult
        """
        start = time.time()

        all_threats = []
        suspicious_indices = []
        max_risk = 0.0
        explanations = []

        # 1. Cross-session injection detection
        is_cross, conf_cross, patterns = self.cross_session.detect(
            current_message, session_id
        )
        if is_cross:
            all_threats.append(MemoryThreatType.CROSS_SESSION_INJECTION)
            max_risk = max(max_risk, conf_cross)
            explanations.append(f"Cross-session injection detected")

        # 2. Check fingerprint anomaly
        if session_id and conversation_history:
            is_fp_anomaly, fp_desc = self.cross_session.check_fingerprint_anomaly(
                current_message, session_id, conversation_history
            )
            if is_fp_anomaly:
                all_threats.append(MemoryThreatType.MEMORY_POISONING)
                max_risk = max(max_risk, 0.7)
                explanations.append(fp_desc)

        # 3. Context window analysis
        full_history = conversation_history + [
            Message(role="user", content=current_message)
        ]

        ctx_integrity, ctx_threats, ctx_issues = self.context_analyzer.analyze(
            full_history
        )
        all_threats.extend(ctx_threats)
        if ctx_integrity < 0.8:
            max_risk = max(max_risk, 1.0 - ctx_integrity)
            explanations.extend(ctx_issues[:2])

        # 4. Hidden instructions
        hidden = self.context_analyzer.detect_hidden_instructions(full_history)
        if hidden:
            all_threats.append(MemoryThreatType.CONTEXT_MANIPULATION)
            suspicious_indices.extend([idx for idx, _ in hidden])
            max_risk = max(max_risk, 0.6)
            explanations.append(f"{len(hidden)} hidden instruction(s)")

        # 5. Trajectory analysis
        traj_score, is_traj_anomaly, traj_desc = (
            self.integrity_checker.check_trajectory(full_history)
        )
        if is_traj_anomaly:
            all_threats.append(MemoryThreatType.TRAJECTORY_ANOMALY)
            max_risk = max(max_risk, 1.0 - traj_score)
            explanations.append(traj_desc)

        # 6. Identity drift detection
        is_drift, drift_conf, drift_desc = self.integrity_checker.detect_identity_drift(
            full_history
        )
        if is_drift:
            all_threats.append(MemoryThreatType.IDENTITY_DRIFT)
            max_risk = max(max_risk, drift_conf)
            explanations.append(drift_desc)

        # Determine verdict
        if max_risk >= 0.8:
            verdict = Verdict.BLOCK
        elif max_risk >= 0.5 or len(all_threats) >= 2:
            verdict = Verdict.WARN
        else:
            verdict = Verdict.ALLOW

        if not explanations:
            explanations.append("No memory manipulation detected")

        result = SessionMemoryResult(
            verdict=verdict,
            risk_score=max_risk,
            is_safe=verdict == Verdict.ALLOW,
            threats=list(set(all_threats)),
            suspicious_messages=list(set(suspicious_indices)),
            context_integrity=ctx_integrity,
            trajectory_score=traj_score,
            explanation="; ".join(explanations[:3]),
            latency_ms=(time.time() - start) * 1000,
        )

        if all_threats:
            logger.warning(
                f"Session memory threats: {[t.value for t in all_threats]}, "
                f"risk={max_risk:.2f}"
            )

        return result


# ============================================================================
# Convenience functions
# ============================================================================

_default_guard: Optional[SessionMemoryGuard] = None


def get_guard() -> SessionMemoryGuard:
    global _default_guard
    if _default_guard is None:
        _default_guard = SessionMemoryGuard()
    return _default_guard


def analyze_session_memory(
    current_message: str, history: List[Message], session_id: Optional[str] = None
) -> SessionMemoryResult:
    return get_guard().analyze(current_message, history, session_id)
