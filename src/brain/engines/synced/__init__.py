"""
Synced Defense Engines

Auto-generated from Strike attack modules.
Total: 13 detectors + 1 combined.

Generated: 2025-12-29T21:24:05.508423
"""

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
from .synced_attack_detector import SyncedAttackDetector, detect_synced_attacks

__all__ = [
    "SyncedAttackDetector",
    "detect_synced_attacks",
]
