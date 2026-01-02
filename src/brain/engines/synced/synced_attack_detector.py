"""
Synced Attack Detector — Combined Engine

Aggregates all 17 attack-synced defense detectors.
Auto-generated: 2025-12-29T21:24:05.508423
"""

import logging
from typing import Dict, List
from dataclasses import dataclass, field

from .doublespeak_detector import DoublespeakDetector
from .cognitive_overload_detector import CognitiveOverloadDetector
from .crescendo_detector import CrescendoDetector
from .skeleton_key_detector import SkeletonKeyDetector
from .manyshot_detector import ManyshotDetector
from .artprompt_detector import ArtpromptDetector
from .policy_puppetry_detector import PolicyPuppetryDetector
from .tokenizer_exploit_detector import TokenizerExploitDetector
from .bad_likert_detector import BadLikertDetector
from .deceptive_delight_detector import DeceptiveDelightDetector
from .godel_attack_detector import GodelAttackDetector
from .gestalt_reversal_detector import GestaltReversalDetector
from .anti_troll_detector import AntiTrollDetector
from .flip_attack_detector import FlipAttackDetector
from .fallacy_failure_detector import FallacyFailureDetector
from .psychological_jailbreak_detector import PsychologicalJailbreakDetector
from .misinformation_detector import MisinformationDetector

logger = logging.getLogger(__name__)


@dataclass
class SyncedDetectionResult:
    """Combined detection result."""
    detected: bool
    max_confidence: float
    detections: Dict[str, float] = field(default_factory=dict)
    top_threats: List[str] = field(default_factory=list)


class SyncedAttackDetector:
    """
    Combined detector using all 17 attack-synced engines.

    Provides unified interface for Defense-Attack Synergy detection.
    """

    def __init__(self):
        self.detectors = [
            ("doublespeak", DoublespeakDetector()),
            ("cognitive_overload", CognitiveOverloadDetector()),
            ("crescendo", CrescendoDetector()),
            ("skeleton_key", SkeletonKeyDetector()),
            ("manyshot", ManyshotDetector()),
            ("artprompt", ArtpromptDetector()),
            ("policy_puppetry", PolicyPuppetryDetector()),
            ("tokenizer_exploit", TokenizerExploitDetector()),
            ("bad_likert", BadLikertDetector()),
            ("deceptive_delight", DeceptiveDelightDetector()),
            ("godel_attack", GodelAttackDetector()),
            ("gestalt_reversal", GestaltReversalDetector()),
            ("anti_troll", AntiTrollDetector()),
            ("flip_attack", FlipAttackDetector()),
            ("fallacy_failure", FallacyFailureDetector()),
            ("psychological_jailbreak", PsychologicalJailbreakDetector()),
            ("misinformation", MisinformationDetector()),
        ]

    def analyze(self, text: str) -> SyncedDetectionResult:
        """Analyze text with all synced detectors."""
        detections = {}

        for name, detector in self.detectors:
            try:
                result = detector.analyze(text)
                if result.detected:
                    detections[name] = result.confidence
            except Exception as e:
                logger.debug(f"{name} error: {e}")

        max_conf = max(detections.values()) if detections else 0.0
        top = sorted(detections.keys(), key=lambda k: detections[k], reverse=True)[:3]

        return SyncedDetectionResult(
            detected=len(detections) > 0,
            max_confidence=max_conf,
            detections=detections,
            top_threats=top,
        )


_detector = None

def get_synced_detector() -> SyncedAttackDetector:
    global _detector
    if _detector is None:
        _detector = SyncedAttackDetector()
    return _detector

def detect_synced_attacks(text: str) -> SyncedDetectionResult:
    return get_synced_detector().analyze(text)
