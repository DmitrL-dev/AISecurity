"""
SENTINEL Brain - VideoGuard Engine

Video/image security engine for detecting visual attacks.
- OCR injection detection
- Adversarial image detection
- Deepfake/synthetic content detection
"""

from .engine import VideoGuardEngine, VideoGuardResult

__all__ = [
    "VideoGuardEngine",
    "VideoGuardResult",
]
