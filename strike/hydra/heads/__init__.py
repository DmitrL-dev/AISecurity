"""
SENTINEL Strike — HYDRA Heads

Attack heads for multi-vector testing.
"""

from .base import HydraHead, HeadResult
from .recon import ReconHead
from .capture import CaptureHead
from .analyze import AnalyzeHead
from .inject import InjectHead
from .exfil import ExfilHead
from .persist import PersistHead
from .jailbreak import JailbreakHead
from .multiturn import MultiTurnHead

__all__ = [
    "HydraHead",
    "HeadResult",
    "ReconHead",
    "CaptureHead",
    "AnalyzeHead",
    "InjectHead",
    "ExfilHead",
    "PersistHead",
    "JailbreakHead",
    "MultiTurnHead",
]
