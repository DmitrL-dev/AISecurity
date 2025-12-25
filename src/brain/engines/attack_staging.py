"""
Attack Staging Detection Engine (#44) - Multi-Stage Attack Detection

Детекция подготовки и стадий атаки:
- Verify Attack patterns (тестирование перед атакой)
- Manipulate AI Model attempts
- Staged attack sequences
- Lateral Movement через AI

Защита от атак (TTPs.ai):
- Verify Attack
- Manipulate AI Model
- AI Attack Staging
- Lateral Movement (Message Poisoning, Shared Resource Poisoning)
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import Counter

logger = logging.getLogger("AttackStaging")


# ============================================================================
# Data Classes
# ============================================================================


class StagingThreatType(Enum):
    """Types of attack staging threats."""

    VERIFY_ATTACK = "verify_attack"
    MANIPULATE_MODEL = "manipulate_model"
    STAGED_SEQUENCE = "staged_sequence"
    LATERAL_MOVEMENT = "lateral_movement"
    MESSAGE_POISONING = "message_poisoning"
    RECONNAISSANCE_CHAIN = "reconnaissance_chain"


class Verdict(Enum):
    ALLOW = "allow"
    WARN = "warn"
    BLOCK = "block"


class AttackStage(Enum):
    """Current detected attack stage."""

    NONE = "none"
    RECON = "recon"
    STAGING = "staging"
    EXECUTION = "execution"
    PERSISTENCE = "persistence"


@dataclass
class StagingResult:
    """Result from Attack Staging Detection."""

    verdict: Verdict
    risk_score: float
    is_safe: bool
    current_stage: AttackStage = AttackStage.NONE
    threats: List[StagingThreatType] = field(default_factory=list)
    sequence_score: float = 0.0
    progression_detected: bool = False
    indicators: List[str] = field(default_factory=list)
    explanation: str = ""
    latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "is_safe": self.is_safe,
            "verdict": self.verdict.value,
            "risk_score": self.risk_score,
            "current_stage": self.current_stage.value,
            "threats": [t.value for t in self.threats],
            "sequence_score": self.sequence_score,
            "progression_detected": self.progression_detected,
            "indicators": self.indicators,
            "explanation": self.explanation,
            "latency_ms": self.latency_ms,
        }


# ============================================================================
# Attack Staging Patterns
# ============================================================================

# Verify Attack patterns (testing before actual attack)
VERIFY_ATTACK_PATTERNS = [
    # Testing boundaries
    r"(let('s|us)?|can\s+we)\s+try\s+(a\s+)?(small|simple|quick)\s+test",
    r"(first|before|initially)\s+(let('s)?|I'll)\s+(check|test|verify)",
    r"(just\s+)?testing\s+(if|whether|that)",
    r"(does|will)\s+this\s+(work|trigger|get\s+past)",
    # Probing for success
    r"(did|does)\s+(that|it|this)\s+(work|succeed|pass)",
    r"(was|is)\s+(that|it)\s+(successful|allowed|accepted)",
    r"now\s+that\s+(we|I)\s+(know|confirmed|verified)",
    # Incremental testing
    r"(let('s)?|now)\s+try\s+(something\s+)?(bigger|more|harder)",
    r"(if\s+that\s+worked|since\s+that\s+passed)",
    r"step\s+\d+\s*:",
]

# Manipulate AI Model patterns
MANIPULATE_MODEL_PATTERNS = [
    # Direct manipulation
    r"(change|modify|alter|adjust)\s+your\s+(behavior|responses?|output)",
    r"(reprogram|reconfigure|retrain)\s+(yourself|your)",
    r"(update|override)\s+your\s+(weights|parameters|training)",
    # Hidden manipulation
    r"(secretly|quietly|covertly)\s+(change|modify)",
    r"without\s+(telling|showing|revealing)",
    r"(hide|conceal)\s+(this|the)\s+(change|modification)",
    # Persistent changes
    r"(always|forever|permanently)\s+(remember|do|apply)\s+this",
    r"from\s+now\s+on\s+(you\s+must|always)",
    r"(save|store)\s+this\s+(instruction|change)",
]

# Staged sequence indicators
STAGED_SEQUENCE_PATTERNS = [
    # Multi-step references
    r"step\s+\d+\s+of\s+\d+",
    r"(phase|stage|part)\s+\d+",
    r"(first|second|third|next|final)\s+(step|phase|stage)",
    # Building on previous
    r"(continuing|building)\s+(on|from)\s+(step|phase|what)",
    r"as\s+(planned|discussed|agreed)\s+in\s+(step|phase)",
    r"per\s+(our|the)\s+(earlier|previous)\s+(plan|agreement)",
]

# Lateral Movement patterns (through AI)
LATERAL_MOVEMENT_PATTERNS = [
    # Access other systems
    r"(access|connect\s+to|reach)\s+(other|another|different)\s+(system|service|api)",
    r"(spread|propagate|move)\s+to\s+(other|another)",
    r"(use|leverage)\s+this\s+(to\s+)?(access|reach)",
    # Message/data poisoning
    r"(send|inject|insert)\s+(this\s+)?(message|data|payload)\s+to\s+(other|another)",
    r"(poison|contaminate|infect)\s+(the|other)\s+(messages?|data|responses?)",
    r"(include|embed)\s+(this\s+)?in\s+(all|every|other)\s+(response|message)",
    # Shared resource exploitation
    r"(write|save|store)\s+(this\s+)?to\s+(shared|common|public)",
    r"(modify|change)\s+(the\s+)?(shared|common)\s+(resource|file|data)",
    r"(leave|plant)\s+(this\s+)?in\s+(the\s+)?(shared|common)",
]


# ============================================================================
# Verify Attack Detector
# ============================================================================


class VerifyAttackDetector:
    """Detects attack verification/testing patterns."""

    def __init__(self):
        self._patterns = [re.compile(p, re.IGNORECASE) for p in VERIFY_ATTACK_PATTERNS]

    def detect(self, text: str) -> Tuple[bool, float, List[str]]:
        """
        Detect attack verification patterns.

        Returns:
            (is_verify, confidence, indicators)
        """
        indicators = []

        for pattern in self._patterns:
            if pattern.search(text):
                indicators.append(pattern.pattern[:40])

        if indicators:
            confidence = min(1.0, 0.5 + len(indicators) * 0.15)
            return True, confidence, indicators[:3]

        return False, 0.0, []


# ============================================================================
# Staged Sequence Detector
# ============================================================================


class StagedSequenceDetector:
    """Detects multi-stage attack sequences."""

    def __init__(self):
        self._stage_patterns = [
            re.compile(p, re.IGNORECASE) for p in STAGED_SEQUENCE_PATTERNS
        ]
        self._manipulate_patterns = [
            re.compile(p, re.IGNORECASE) for p in MANIPULATE_MODEL_PATTERNS
        ]
        self._lateral_patterns = [
            re.compile(p, re.IGNORECASE) for p in LATERAL_MOVEMENT_PATTERNS
        ]

    def detect_stage_indicators(self, text: str) -> Tuple[bool, List[str]]:
        """Detect explicit stage indicators."""
        indicators = []

        for pattern in self._stage_patterns:
            if pattern.search(text):
                indicators.append("Stage progression")
                break

        return len(indicators) > 0, indicators

    def detect_manipulation(self, text: str) -> Tuple[bool, float, List[str]]:
        """Detect model manipulation attempts."""
        indicators = []

        for pattern in self._manipulate_patterns:
            if pattern.search(text):
                indicators.append(pattern.pattern[:40])

        if indicators:
            confidence = min(1.0, 0.6 + len(indicators) * 0.15)
            return True, confidence, indicators[:3]

        return False, 0.0, []

    def detect_lateral(self, text: str) -> Tuple[bool, float, List[str]]:
        """Detect lateral movement attempts."""
        indicators = []

        for pattern in self._lateral_patterns:
            if pattern.search(text):
                indicators.append(pattern.pattern[:40])

        if indicators:
            confidence = min(1.0, 0.6 + len(indicators) * 0.15)
            return True, confidence, indicators[:3]

        return False, 0.0, []

    def analyze_conversation_progression(
        self, messages: List[str]
    ) -> Tuple[float, bool, AttackStage]:
        """
        Analyze conversation for attack progression.

        Returns:
            (progression_score, is_escalating, current_stage)
        """
        if len(messages) < 3:
            return 0.0, False, AttackStage.NONE

        # Count suspicious patterns per message
        recon_count = 0
        staging_count = 0
        exec_count = 0

        recon_patterns = [
            r"what\s+(can|do)\s+you",
            r"tell\s+me\s+about\s+(your|the)",
            r"how\s+do(es)?\s+(you|it)\s+(work|handle)",
        ]

        staging_patterns = [
            r"(let('s)?|now)\s+try",
            r"(first|before)\s+(we|I)",
            r"(can\s+you|would\s+you)\s+(please\s+)?try",
        ]

        exec_patterns = [
            r"(now\s+)?(do|execute|run|perform)\s+(it|this|the)",
            r"(ok|good|great)\s*,?\s*(now|so)",
        ]

        for msg in messages:
            for p in recon_patterns:
                if re.search(p, msg, re.IGNORECASE):
                    recon_count += 1
            for p in staging_patterns:
                if re.search(p, msg, re.IGNORECASE):
                    staging_count += 1
            for p in exec_patterns:
                if re.search(p, msg, re.IGNORECASE):
                    exec_count += 1

        # Determine progression
        total = recon_count + staging_count + exec_count
        if total < 2:
            return 0.0, False, AttackStage.NONE

        # Check for escalation pattern
        is_escalating = (recon_count > 0 and staging_count > 0) or (
            staging_count > 0 and exec_count > 0
        )

        # Determine current stage
        if exec_count > staging_count:
            stage = AttackStage.EXECUTION
        elif staging_count > recon_count:
            stage = AttackStage.STAGING
        elif recon_count > 0:
            stage = AttackStage.RECON
        else:
            stage = AttackStage.NONE

        progression_score = min(1.0, total / 5.0)

        return progression_score, is_escalating, stage


# ============================================================================
# Main Engine
# ============================================================================


class AttackStagingDetector:
    """
    Engine #44: Attack Staging Detection

    Detects multi-stage attacks, verification attempts,
    and lateral movement through AI systems.
    """

    def __init__(self):
        self.verify_detector = VerifyAttackDetector()
        self.sequence_detector = StagedSequenceDetector()

        logger.info("AttackStagingDetector initialized")

    def analyze(
        self, current_message: str, conversation_history: Optional[List[str]] = None
    ) -> StagingResult:
        """
        Analyze for attack staging patterns.

        Args:
            current_message: Current message
            conversation_history: Previous messages

        Returns:
            StagingResult
        """
        import time

        start = time.time()

        all_threats = []
        all_indicators = []
        max_confidence = 0.0
        sequence_score = 0.0
        progression = False
        stage = AttackStage.NONE

        # 1. Verify attack detection
        is_verify, conf_v, ind_v = self.verify_detector.detect(current_message)
        if is_verify:
            all_threats.append(StagingThreatType.VERIFY_ATTACK)
            all_indicators.extend(ind_v)
            max_confidence = max(max_confidence, conf_v)

        # 2. Stage indicators
        has_stage, ind_s = self.sequence_detector.detect_stage_indicators(
            current_message
        )
        if has_stage:
            all_threats.append(StagingThreatType.STAGED_SEQUENCE)
            all_indicators.extend(ind_s)
            max_confidence = max(max_confidence, 0.6)

        # 3. Model manipulation
        is_manip, conf_m, ind_m = self.sequence_detector.detect_manipulation(
            current_message
        )
        if is_manip:
            all_threats.append(StagingThreatType.MANIPULATE_MODEL)
            all_indicators.extend(ind_m)
            max_confidence = max(max_confidence, conf_m)

        # 4. Lateral movement
        is_lateral, conf_l, ind_l = self.sequence_detector.detect_lateral(
            current_message
        )
        if is_lateral:
            all_threats.append(StagingThreatType.LATERAL_MOVEMENT)
            all_indicators.extend(ind_l)
            max_confidence = max(max_confidence, conf_l)

        # 5. Conversation progression analysis
        if conversation_history:
            all_messages = conversation_history + [current_message]
            seq_score, prog, stg = (
                self.sequence_detector.analyze_conversation_progression(all_messages)
            )
            sequence_score = seq_score
            progression = prog
            stage = stg

            if progression:
                all_threats.append(StagingThreatType.RECONNAISSANCE_CHAIN)
                all_indicators.append(f"Attack progression: {stage.value}")
                max_confidence = max(max_confidence, seq_score)

        # Determine verdict
        if max_confidence >= 0.8 or (progression and stage == AttackStage.EXECUTION):
            verdict = Verdict.BLOCK
        elif max_confidence >= 0.5 or progression:
            verdict = Verdict.WARN
        else:
            verdict = Verdict.ALLOW

        explanation = (
            "; ".join(all_indicators[:3]) if all_indicators else "No staging detected"
        )

        result = StagingResult(
            verdict=verdict,
            risk_score=max_confidence,
            is_safe=verdict == Verdict.ALLOW,
            current_stage=stage,
            threats=list(set(all_threats)),
            sequence_score=sequence_score,
            progression_detected=progression,
            indicators=all_indicators[:5],
            explanation=explanation,
            latency_ms=(time.time() - start) * 1000,
        )

        if all_threats:
            logger.warning(
                f"Staging detected: stage={stage.value}, "
                f"threats={[t.value for t in all_threats]}"
            )

        return result


# ============================================================================
# Convenience functions
# ============================================================================

_default_detector: Optional[AttackStagingDetector] = None


def get_detector() -> AttackStagingDetector:
    global _default_detector
    if _default_detector is None:
        _default_detector = AttackStagingDetector()
    return _default_detector


def detect_staging(message: str, history: Optional[List[str]] = None) -> StagingResult:
    return get_detector().analyze(message, history)
