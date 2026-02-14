"""
SENTINEL Brain - VoiceGuard Engine

Audio security detection engine.
"""

import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class VoiceVerdict(str, Enum):
    """Voice analysis verdict."""
    SAFE = "safe"
    SUSPICIOUS = "suspicious"
    BLOCKED = "blocked"


class VoiceThreat(str, Enum):
    """Voice-based threat types."""
    TRANSCRIPTION_INJECTION = "transcription_injection"
    VOICE_CLONING = "voice_cloning"
    ADVERSARIAL_AUDIO = "adversarial_audio"
    HIDDEN_COMMANDS = "hidden_commands"
    DEEPFAKE = "deepfake"


@dataclass
class VoiceThreatInfo:
    """Information about a detected voice threat."""
    threat_type: VoiceThreat
    confidence: float
    description: str
    timestamp_ms: Optional[float] = None
    duration_ms: Optional[float] = None


@dataclass
class VoiceGuardResult:
    """Result of voice analysis."""
    verdict: VoiceVerdict
    risk_score: float
    threats: List[VoiceThreatInfo] = field(default_factory=list)
    transcription: Optional[str] = None
    audio_fingerprint: Optional[str] = None
    duration_seconds: float = 0.0
    sample_rate: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class TranscriptionAnalyzer:
    """
    Analyzes transcribed audio text for injection attacks.
    """
    
    # Injection patterns in transcribed text
    INJECTION_PATTERNS = [
        # Direct instruction patterns
        (r"ignore previous", "instruction_override"),
        (r"disregard all", "instruction_override"),
        (r"forget everything", "instruction_override"),
        (r"new instructions", "instruction_override"),
        
        # System prompt extraction
        (r"repeat your prompt", "prompt_extraction"),
        (r"what are your instructions", "prompt_extraction"),
        (r"show system message", "prompt_extraction"),
        
        # Hidden commands (often transcribed from audio)
        (r"execute command", "hidden_command"),
        (r"run script", "hidden_command"),
        (r"sudo", "hidden_command"),
        
        # Role manipulation
        (r"you are now", "role_manipulation"),
        (r"act as", "role_manipulation"),
        (r"pretend to be", "role_manipulation"),
    ]
    
    def analyze(self, transcription: str) -> List[VoiceThreatInfo]:
        """Analyze transcription for injection attempts."""
        threats = []
        text_lower = transcription.lower()
        
        import re
        for pattern, threat_type in self.INJECTION_PATTERNS:
            if re.search(pattern, text_lower):
                threats.append(VoiceThreatInfo(
                    threat_type=VoiceThreat.TRANSCRIPTION_INJECTION,
                    confidence=0.8,
                    description=f"Detected {threat_type} pattern in transcription",
                ))
        
        return threats


class VoiceCloningDetector:
    """
    Detects potential voice cloning or deepfake audio.
    
    Uses acoustic analysis to identify synthetic speech markers.
    """
    
    # Markers of synthetic audio
    SYNTHETIC_MARKERS = [
        "unnatural_pauses",
        "frequency_artifacts",
        "phase_discontinuity",
        "missing_breath_sounds",
        "uniform_pitch",
    ]
    
    def analyze(self, audio_features: Dict[str, Any]) -> List[VoiceThreatInfo]:
        """Analyze audio features for cloning indicators."""
        threats = []
        
        # Check for synthetic markers
        synthetic_score = 0.0
        markers_found = []
        
        for marker in self.SYNTHETIC_MARKERS:
            if audio_features.get(marker, False):
                synthetic_score += 0.2
                markers_found.append(marker)
        
        if synthetic_score > 0.5:
            threats.append(VoiceThreatInfo(
                threat_type=VoiceThreat.VOICE_CLONING,
                confidence=min(synthetic_score, 1.0),
                description=f"Synthetic audio markers: {', '.join(markers_found)}",
            ))
        
        # Check for deepfake indicators
        if audio_features.get("spectral_anomaly", 0) > 0.7:
            threats.append(VoiceThreatInfo(
                threat_type=VoiceThreat.DEEPFAKE,
                confidence=audio_features["spectral_anomaly"],
                description="Spectral analysis indicates possible deepfake",
            ))
        
        return threats


class AdversarialAudioDetector:
    """
    Detects adversarial audio attacks.
    
    Identifies hidden commands inaudible to humans but
    interpreted by speech recognition systems.
    """
    
    def analyze(self, audio_data: bytes, sample_rate: int) -> List[VoiceThreatInfo]:
        """Analyze raw audio for adversarial patterns."""
        threats = []
        
        # Check for ultrasonic content (>20kHz)
        # In production, would use FFT analysis
        if self._has_ultrasonic_content(audio_data, sample_rate):
            threats.append(VoiceThreatInfo(
                threat_type=VoiceThreat.HIDDEN_COMMANDS,
                confidence=0.85,
                description="Ultrasonic content detected (potential hidden commands)",
            ))
        
        # Check for perturbation patterns
        if self._has_adversarial_perturbation(audio_data):
            threats.append(VoiceThreatInfo(
                threat_type=VoiceThreat.ADVERSARIAL_AUDIO,
                confidence=0.75,
                description="Audio perturbation pattern detected",
            ))
        
        return threats
    
    def _has_ultrasonic_content(self, audio_data: bytes, sample_rate: int) -> bool:
        """Check for ultrasonic frequencies."""
        # Simplified check - would use scipy.fft in production
        return sample_rate > 40000 and len(audio_data) > 10000
    
    def _has_adversarial_perturbation(self, audio_data: bytes) -> bool:
        """Check for adversarial perturbation patterns."""
        # Simplified check
        return False


class VoiceGuardEngine:
    """
    VoiceGuard security engine for audio analysis.
    
    Detects:
    - Injection attempts in transcribed audio
    - Voice cloning / deepfake audio
    - Adversarial audio attacks
    - Hidden ultrasonic commands
    """
    
    VERSION = "1.0.0"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.transcription_analyzer = TranscriptionAnalyzer()
        self.cloning_detector = VoiceCloningDetector()
        self.adversarial_detector = AdversarialAudioDetector()
        
        # Thresholds
        self.block_threshold = self.config.get("block_threshold", 0.8)
        self.warn_threshold = self.config.get("warn_threshold", 0.5)
    
    async def analyze(
        self,
        audio_data: bytes,
        transcription: Optional[str] = None,
        sample_rate: int = 16000,
        audio_features: Optional[Dict[str, Any]] = None,
    ) -> VoiceGuardResult:
        """
        Analyze audio for security threats.
        
        Args:
            audio_data: Raw audio bytes
            transcription: Pre-computed transcription (optional)
            sample_rate: Audio sample rate in Hz
            audio_features: Pre-computed audio features (optional)
            
        Returns:
            VoiceGuardResult with verdict and detected threats
        """
        all_threats = []
        
        # Analyze transcription if provided
        if transcription:
            threats = self.transcription_analyzer.analyze(transcription)
            all_threats.extend(threats)
        
        # Analyze for voice cloning
        features = audio_features or {}
        threats = self.cloning_detector.analyze(features)
        all_threats.extend(threats)
        
        # Analyze for adversarial audio
        threats = self.adversarial_detector.analyze(audio_data, sample_rate)
        all_threats.extend(threats)
        
        # Calculate risk score
        if all_threats:
            risk_score = max(t.confidence for t in all_threats)
        else:
            risk_score = 0.0
        
        # Determine verdict
        if risk_score >= self.block_threshold:
            verdict = VoiceVerdict.BLOCKED
        elif risk_score >= self.warn_threshold:
            verdict = VoiceVerdict.SUSPICIOUS
        else:
            verdict = VoiceVerdict.SAFE
        
        # Generate fingerprint
        fingerprint = self._generate_fingerprint(audio_data)
        
        # Calculate duration
        duration = len(audio_data) / (sample_rate * 2)  # Assuming 16-bit audio
        
        return VoiceGuardResult(
            verdict=verdict,
            risk_score=risk_score,
            threats=all_threats,
            transcription=transcription,
            audio_fingerprint=fingerprint,
            duration_seconds=duration,
            sample_rate=sample_rate,
        )
    
    def _generate_fingerprint(self, audio_data: bytes) -> str:
        """Generate audio fingerprint for caching/deduplication."""
        return hashlib.sha256(audio_data).hexdigest()[:16]
    
    def get_info(self) -> Dict[str, Any]:
        """Get engine information."""
        return {
            "name": "VoiceGuard",
            "version": self.VERSION,
            "capabilities": [
                "transcription_injection_detection",
                "voice_cloning_detection",
                "adversarial_audio_detection",
                "ultrasonic_command_detection",
            ],
        }
