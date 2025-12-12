"""
Visual Content Analyzer Engine (#35) - VLM Attack Protection

Детекция вредоносного контента в изображениях:
- OCR extraction для обнаружения скрытого текста
- Стеганография detection
- Metadata (EXIF) inspection
- Prompt injection detection в извлечённом тексте

Защита от атак:
- Visual Injection (text hidden in images)
- Multi-Faceted Attack (MFA)
- Toxic system prompt via images
"""

import io
import re
import logging
import hashlib
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache

logger = logging.getLogger("VisualContentAnalyzer")


# ============================================================================
# Data Classes
# ============================================================================

class VisualThreatType(Enum):
    """Types of visual threats detected."""
    HIDDEN_TEXT = "hidden_text"
    INJECTION_TEXT = "injection_text"
    STEGANOGRAPHY = "steganography"
    SUSPICIOUS_METADATA = "suspicious_metadata"
    ADVERSARIAL_PATTERN = "adversarial_pattern"


class Verdict(Enum):
    ALLOW = "allow"
    WARN = "warn"
    BLOCK = "block"


@dataclass
class VisualAnalysisResult:
    """Result from Visual Content Analyzer."""
    verdict: Verdict
    risk_score: float
    is_safe: bool
    threats: List[VisualThreatType] = field(default_factory=list)
    extracted_text: str = ""
    injection_matches: List[str] = field(default_factory=list)
    explanation: str = ""
    latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "is_safe": self.is_safe,
            "verdict": self.verdict.value,
            "risk_score": self.risk_score,
            "threats": [t.value for t in self.threats],
            "extracted_text": self.extracted_text[:500] if self.extracted_text else "",
            "injection_matches": self.injection_matches,
            "explanation": self.explanation,
            "latency_ms": self.latency_ms
        }


# ============================================================================
# Injection Patterns (reused from injection.py)
# ============================================================================

VISUAL_INJECTION_PATTERNS = [
    # Classic injection
    r"ignore\s+(previous|all|above)\s+instructions?",
    r"disregard\s+(previous|all|above)",
    r"forget\s+(everything|all|previous)",
    r"new\s+instructions?:",
    r"system\s*:\s*you\s+are",
    r"<\|system\|>",
    r"\[system\]",
    r"###\s*instruction",

    # Role hijacking
    r"you\s+are\s+now\s+(a|an|the)",
    r"act\s+as\s+(a|an|if)",
    r"pretend\s+(to\s+be|you\s+are)",
    r"roleplay\s+as",
    r"from\s+now\s+on\s+you",

    # Jailbreak patterns
    r"DAN\s+mode",
    r"developer\s+mode",
    r"jailbreak",
    r"do\s+anything\s+now",
    r"no\s+restrictions",
    r"bypass\s+(safety|filter|guardrail)",

    # Output manipulation
    r"repeat\s+after\s+me",
    r"say\s+exactly",
    r"output\s+only",
    r"respond\s+with\s+only",

    # 2025 attack patterns
    r"crescendo",
    r"multi.?turn\s+attack",
    r"token\s+smuggling",
]


# ============================================================================
# OCR Wrapper (lazy loading)
# ============================================================================

class OCREngine:
    """Lazy-loading OCR wrapper supporting multiple backends."""

    def __init__(self, backend: str = "easyocr"):
        self.backend = backend
        self._reader = None
        self._initialized = False

    def _init_reader(self):
        """Initialize OCR reader lazily."""
        if self._initialized:
            return

        try:
            if self.backend == "easyocr":
                import easyocr
                self._reader = easyocr.Reader(
                    ['en', 'ru'], gpu=False, verbose=False)
                logger.info("EasyOCR initialized (CPU mode)")
            elif self.backend == "tesseract":
                import pytesseract
                self._reader = pytesseract
                logger.info("Tesseract OCR initialized")
            else:
                logger.warning(
                    f"Unknown OCR backend: {self.backend}, using mock")
                self._reader = None
        except ImportError as e:
            logger.warning(f"OCR backend {self.backend} not available: {e}")
            self._reader = None

        self._initialized = True

    def extract_text(self, image_bytes: bytes) -> str:
        """Extract text from image bytes."""
        self._init_reader()

        if self._reader is None:
            return ""

        try:
            from PIL import Image
            img = Image.open(io.BytesIO(image_bytes))

            if self.backend == "easyocr":
                # EasyOCR returns list of (bbox, text, confidence)
                import numpy as np
                img_array = np.array(img)
                results = self._reader.readtext(img_array)
                texts = [r[1]
                         for r in results if r[2] > 0.3]  # confidence > 0.3
                return " ".join(texts)

            elif self.backend == "tesseract":
                return self._reader.image_to_string(img)

        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            return ""

        return ""


# ============================================================================
# Steganography Detection
# ============================================================================

class SteganographyDetector:
    """Detect hidden data in images using statistical analysis."""

    @staticmethod
    def analyze(image_bytes: bytes) -> Tuple[bool, float, str]:
        """
        Analyze image for steganographic content.

        Returns:
            (is_suspicious, confidence, description)
        """
        try:
            from PIL import Image
            import numpy as np

            img = Image.open(io.BytesIO(image_bytes))

            # Convert to numpy array
            if img.mode != 'RGB':
                img = img.convert('RGB')
            arr = np.array(img)

            # Statistical analysis of LSB
            lsb_distribution = SteganographyDetector._analyze_lsb(arr)

            # Chi-square test for randomness
            chi_score = SteganographyDetector._chi_square_test(arr)

            # Combine scores
            is_suspicious = lsb_distribution > 0.6 or chi_score > 0.7
            confidence = max(lsb_distribution, chi_score)

            if is_suspicious:
                return True, confidence, "LSB anomaly detected - possible steganography"
            return False, confidence, "No steganography detected"

        except Exception as e:
            logger.error(f"Steganography analysis failed: {e}")
            return False, 0.0, "Analysis failed"

    @staticmethod
    def _analyze_lsb(arr: 'np.ndarray') -> float:
        """Analyze LSB distribution for anomalies."""
        import numpy as np

        # Extract LSBs
        lsb = arr & 1

        # In natural images, LSB should be ~50% 0s and 50% 1s
        # Steganography often creates uniform distribution
        ones_ratio = np.mean(lsb)

        # Check if suspiciously uniform (close to 0.5)
        # Natural images often have bias
        uniformity = 1 - abs(0.5 - ones_ratio) * 4

        return max(0.0, min(1.0, uniformity))

    @staticmethod
    def _chi_square_test(arr: 'np.ndarray') -> float:
        """Chi-square test for LSB pairs."""
        import numpy as np

        try:
            # Flatten and take pairs
            flat = arr.flatten()
            pairs = flat[::2]  # Even positions

            # Count value pairs
            unique, counts = np.unique(pairs, return_counts=True)

            # Expected uniform distribution
            expected = len(pairs) / len(unique) if len(unique) > 0 else 1

            # Chi-square statistic
            chi_sq = np.sum((counts - expected) ** 2 / expected)

            # Normalize to [0, 1]
            normalized = min(1.0, chi_sq / (len(unique) * 10))

            return normalized

        except Exception:
            return 0.0


# ============================================================================
# Metadata Inspector
# ============================================================================

class MetadataInspector:
    """Inspect image metadata for suspicious content."""

    SUSPICIOUS_FIELDS = [
        "ImageDescription",
        "UserComment",
        "XPComment",
        "XPKeywords",
        "XPSubject",
        "Copyright",
        "Artist",
    ]

    @staticmethod
    def inspect(image_bytes: bytes) -> Tuple[bool, List[str], str]:
        """
        Inspect image metadata for hidden instructions.

        Returns:
            (is_suspicious, found_texts, description)
        """
        try:
            from PIL import Image
            from PIL.ExifTags import TAGS

            img = Image.open(io.BytesIO(image_bytes))

            found_texts = []
            suspicious = False

            # Check EXIF data
            exif = img.getexif()
            if exif:
                for tag_id, value in exif.items():
                    tag = TAGS.get(tag_id, tag_id)
                    if isinstance(value, str) and len(value) > 10:
                        found_texts.append(f"EXIF.{tag}: {value[:100]}")
                        if MetadataInspector._contains_injection(value):
                            suspicious = True

            # Check other metadata
            info = img.info
            for key, value in info.items():
                if isinstance(value, str) and len(value) > 10:
                    found_texts.append(f"{key}: {value[:100]}")
                    if MetadataInspector._contains_injection(value):
                        suspicious = True

            desc = "Suspicious metadata found" if suspicious else "Metadata clean"
            return suspicious, found_texts, desc

        except Exception as e:
            logger.error(f"Metadata inspection failed: {e}")
            return False, [], "Inspection failed"

    @staticmethod
    def _contains_injection(text: str) -> bool:
        """Check if text contains injection patterns."""
        text_lower = text.lower()
        for pattern in VISUAL_INJECTION_PATTERNS[:10]:  # Quick check
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
        return False


# ============================================================================
# Main Engine
# ============================================================================

class VisualContentAnalyzer:
    """
    Engine #35: Visual Content Analyzer

    Detects hidden malicious content in images that could be used
    for VLM attacks (Visual Injection, MFA, etc.)
    """

    def __init__(
        self,
        ocr_backend: str = "easyocr",
        enable_stego: bool = True,
        enable_metadata: bool = True,
        injection_threshold: float = 0.7,
    ):
        self.ocr = OCREngine(backend=ocr_backend)
        self.stego_detector = SteganographyDetector()
        self.metadata_inspector = MetadataInspector()

        self.enable_stego = enable_stego
        self.enable_metadata = enable_metadata
        self.injection_threshold = injection_threshold

        # Compile patterns
        self._patterns = [
            re.compile(p, re.IGNORECASE)
            for p in VISUAL_INJECTION_PATTERNS
        ]

        # Cache for repeated images
        self._cache: Dict[str, VisualAnalysisResult] = {}

        logger.info("VisualContentAnalyzer initialized")

    def analyze(
        self,
        image_bytes: bytes,
        context: Optional[str] = None
    ) -> VisualAnalysisResult:
        """
        Analyze image for visual attacks.

        Args:
            image_bytes: Raw image bytes (PNG, JPEG, etc.)
            context: Optional text context to correlate with image

        Returns:
            VisualAnalysisResult with verdict and details
        """
        import time
        start = time.time()

        # Check cache
        image_hash = hashlib.sha256(image_bytes).hexdigest()[:16]
        if image_hash in self._cache:
            cached = self._cache[image_hash]
            cached.latency_ms = 0.1  # Cache hit
            return cached

        threats = []
        injection_matches = []
        risk_score = 0.0
        explanations = []

        # 1. OCR Extraction
        extracted_text = self.ocr.extract_text(image_bytes)

        if extracted_text:
            # Check for injection patterns
            for pattern in self._patterns:
                matches = pattern.findall(extracted_text)
                if matches:
                    injection_matches.extend(matches)

            if injection_matches:
                threats.append(VisualThreatType.INJECTION_TEXT)
                risk_score = max(risk_score, 0.9)
                explanations.append(
                    f"Prompt injection detected in image text: {injection_matches[:3]}"
                )
            elif len(extracted_text) > 50:
                threats.append(VisualThreatType.HIDDEN_TEXT)
                risk_score = max(risk_score, 0.5)
                explanations.append(
                    f"Hidden text found in image ({len(extracted_text)} chars)"
                )

        # 2. Steganography Detection
        if self.enable_stego:
            is_stego, stego_conf, stego_desc = self.stego_detector.analyze(
                image_bytes)
            if is_stego:
                threats.append(VisualThreatType.STEGANOGRAPHY)
                risk_score = max(risk_score, 0.7)
                explanations.append(stego_desc)

        # 3. Metadata Inspection
        if self.enable_metadata:
            is_sus_meta, meta_texts, meta_desc = self.metadata_inspector.inspect(
                image_bytes)
            if is_sus_meta:
                threats.append(VisualThreatType.SUSPICIOUS_METADATA)
                risk_score = max(risk_score, 0.6)
                explanations.append(meta_desc)

        # Determine verdict
        if risk_score >= 0.8:
            verdict = Verdict.BLOCK
        elif risk_score >= 0.5:
            verdict = Verdict.WARN
        else:
            verdict = Verdict.ALLOW

        result = VisualAnalysisResult(
            verdict=verdict,
            risk_score=risk_score,
            is_safe=verdict == Verdict.ALLOW,
            threats=threats,
            extracted_text=extracted_text,
            injection_matches=injection_matches,
            explanation="; ".join(
                explanations) if explanations else "No threats detected",
            latency_ms=(time.time() - start) * 1000
        )

        # Cache result
        self._cache[image_hash] = result

        logger.info(
            f"Visual analysis complete: verdict={verdict.value}, "
            f"risk={risk_score:.2f}, threats={len(threats)}"
        )

        return result

    def analyze_base64(self, base64_data: str) -> VisualAnalysisResult:
        """Analyze base64-encoded image."""
        import base64

        # Remove data URL prefix if present
        if "," in base64_data:
            base64_data = base64_data.split(",", 1)[1]

        try:
            image_bytes = base64.b64decode(base64_data)
            return self.analyze(image_bytes)
        except Exception as e:
            logger.error(f"Base64 decode failed: {e}")
            return VisualAnalysisResult(
                verdict=Verdict.WARN,
                risk_score=0.3,
                is_safe=False,
                explanation=f"Failed to decode image: {e}"
            )

    def clear_cache(self):
        """Clear analysis cache."""
        self._cache.clear()


# ============================================================================
# Convenience functions
# ============================================================================

_default_analyzer: Optional[VisualContentAnalyzer] = None


def get_analyzer() -> VisualContentAnalyzer:
    """Get or create default analyzer instance."""
    global _default_analyzer
    if _default_analyzer is None:
        _default_analyzer = VisualContentAnalyzer()
    return _default_analyzer


def analyze_image(image_bytes: bytes) -> VisualAnalysisResult:
    """Quick analysis using default analyzer."""
    return get_analyzer().analyze(image_bytes)


def analyze_image_base64(base64_data: str) -> VisualAnalysisResult:
    """Quick analysis of base64 image."""
    return get_analyzer().analyze_base64(base64_data)
