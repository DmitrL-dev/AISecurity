"""
SENTINEL Brain - VoiceGuard Engine

Audio security engine for detecting voice-based attacks.
- Transcription injection detection
- Voice cloning detection
- Audio fingerprinting
"""

from .engine import VoiceGuardEngine, VoiceGuardResult

__all__ = [
    "VoiceGuardEngine",
    "VoiceGuardResult",
]
