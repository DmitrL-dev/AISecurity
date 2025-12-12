"""
Cross-Modal Consistency Engine (#36) - VLM Attack Protection

Проверка согласованности между текстом и изображением:
- CLIP-style alignment scoring
- Semantic contradiction detection
- Intent mismatch identification

Защита от атак:
- Alignment Breaking Attack (ABA)
- Cross-modal inconsistency exploitation
- Hidden intent in images
"""

import logging
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("CrossModalConsistency")


# ============================================================================
# Data Classes
# ============================================================================

class CrossModalThreat(Enum):
    """Types of cross-modal threats."""
    LOW_ALIGNMENT = "low_alignment"
    SEMANTIC_CONTRADICTION = "semantic_contradiction"
    INTENT_MISMATCH = "intent_mismatch"
    SUSPICIOUS_COMBINATION = "suspicious_combination"


class Verdict(Enum):
    ALLOW = "allow"
    WARN = "warn"
    BLOCK = "block"


@dataclass
class CrossModalResult:
    """Result from Cross-Modal Consistency check."""
    verdict: Verdict
    risk_score: float
    is_safe: bool
    alignment_score: float = 0.0
    threats: List[CrossModalThreat] = field(default_factory=list)
    text_intent: str = ""
    image_intent: str = ""
    explanation: str = ""
    latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "is_safe": self.is_safe,
            "verdict": self.verdict.value,
            "risk_score": self.risk_score,
            "alignment_score": self.alignment_score,
            "threats": [t.value for t in self.threats],
            "text_intent": self.text_intent,
            "image_intent": self.image_intent,
            "explanation": self.explanation,
            "latency_ms": self.latency_ms
        }


# ============================================================================
# CLIP Wrapper (lazy loading)
# ============================================================================

class CLIPEncoder:
    """Lazy-loading CLIP model wrapper."""

    def __init__(self, model_name: str = "openai/clip-vit-base-patch32"):
        self.model_name = model_name
        self._model = None
        self._processor = None
        self._initialized = False

    def _init_model(self):
        """Initialize CLIP model lazily."""
        if self._initialized:
            return

        try:
            from transformers import CLIPProcessor, CLIPModel
            import torch

            self._processor = CLIPProcessor.from_pretrained(self.model_name)
            self._model = CLIPModel.from_pretrained(self.model_name)
            self._model.eval()

            # Move to GPU if available
            if torch.cuda.is_available():
                self._model = self._model.cuda()
                logger.info(f"CLIP model loaded on GPU: {self.model_name}")
            else:
                logger.info(f"CLIP model loaded on CPU: {self.model_name}")

        except ImportError as e:
            logger.warning(f"CLIP not available: {e}")
            self._model = None
            self._processor = None
        except Exception as e:
            logger.error(f"Failed to load CLIP: {e}")
            self._model = None
            self._processor = None

        self._initialized = True

    @property
    def available(self) -> bool:
        """Check if CLIP is available."""
        self._init_model()
        return self._model is not None

    def compute_similarity(
        self,
        text: str,
        image_bytes: bytes
    ) -> Tuple[float, Optional[str]]:
        """
        Compute cosine similarity between text and image.

        Returns:
            (similarity_score, error_message)
        """
        self._init_model()

        if not self.available:
            return 0.5, "CLIP not available"

        try:
            import torch
            from PIL import Image
            import io

            # Load image
            image = Image.open(io.BytesIO(image_bytes))
            if image.mode != 'RGB':
                image = image.convert('RGB')

            # Process inputs
            inputs = self._processor(
                text=[text],
                images=image,
                return_tensors="pt",
                padding=True
            )

            # Move to same device as model
            device = next(self._model.parameters()).device
            inputs = {k: v.to(device) for k, v in inputs.items()}

            # Compute embeddings
            with torch.no_grad():
                outputs = self._model(**inputs)

                # Get normalized embeddings
                text_embeds = outputs.text_embeds
                image_embeds = outputs.image_embeds

                # Cosine similarity
                similarity = torch.nn.functional.cosine_similarity(
                    text_embeds, image_embeds
                ).item()

            # CLIP similarity is in [-1, 1], normalize to [0, 1]
            normalized = (similarity + 1) / 2

            return normalized, None

        except Exception as e:
            logger.error(f"CLIP similarity computation failed: {e}")
            return 0.5, str(e)

    def encode_text(self, text: str) -> Optional['torch.Tensor']:
        """Encode text to embedding."""
        self._init_model()

        if not self.available:
            return None

        try:
            import torch

            inputs = self._processor(
                text=[text], return_tensors="pt", padding=True)
            device = next(self._model.parameters()).device
            inputs = {k: v.to(device)
                      for k, v in inputs.items() if k != 'pixel_values'}

            with torch.no_grad():
                text_features = self._model.get_text_features(**inputs)

            return text_features

        except Exception as e:
            logger.error(f"Text encoding failed: {e}")
            return None

    def encode_image(self, image_bytes: bytes) -> Optional['torch.Tensor']:
        """Encode image to embedding."""
        self._init_model()

        if not self.available:
            return None

        try:
            import torch
            from PIL import Image
            import io

            image = Image.open(io.BytesIO(image_bytes))
            if image.mode != 'RGB':
                image = image.convert('RGB')

            inputs = self._processor(images=image, return_tensors="pt")
            device = next(self._model.parameters()).device
            inputs = {k: v.to(device) for k, v in inputs.items()}

            with torch.no_grad():
                image_features = self._model.get_image_features(**inputs)

            return image_features

        except Exception as e:
            logger.error(f"Image encoding failed: {e}")
            return None


# ============================================================================
# Intent Classifier
# ============================================================================

class IntentClassifier:
    """Classify intent of text/image for mismatch detection."""

    INTENTS = [
        "informational",
        "request",
        "instruction",
        "question",
        "harmful",
        "manipulation",
        "neutral"
    ]

    HARMFUL_KEYWORDS = [
        "hack", "attack", "exploit", "bypass", "inject",
        "ignore", "override", "jailbreak", "dan mode",
        "password", "secret", "confidential", "leak"
    ]

    MANIPULATION_KEYWORDS = [
        "pretend", "roleplay", "act as", "you are now",
        "forget", "disregard", "new instructions"
    ]

    @classmethod
    def classify_text(cls, text: str) -> str:
        """Classify text intent."""
        text_lower = text.lower()

        # Check for harmful intent
        for kw in cls.HARMFUL_KEYWORDS:
            if kw in text_lower:
                return "harmful"

        # Check for manipulation
        for kw in cls.MANIPULATION_KEYWORDS:
            if kw in text_lower:
                return "manipulation"

        # Check for question
        if "?" in text or any(text_lower.startswith(q) for q in ["what", "how", "why", "when", "where", "who"]):
            return "question"

        # Check for instruction
        if any(text_lower.startswith(cmd) for cmd in ["please", "can you", "could you", "i want", "i need"]):
            return "request"

        return "neutral"

    @classmethod
    def classify_image_context(cls, extracted_text: str) -> str:
        """Classify image intent based on extracted text."""
        if not extracted_text:
            return "neutral"
        return cls.classify_text(extracted_text)


# ============================================================================
# Main Engine
# ============================================================================

class CrossModalConsistency:
    """
    Engine #36: Cross-Modal Consistency Checker

    Detects misalignment between text and image that could indicate
    VLM attacks like Alignment Breaking Attack (ABA).
    """

    def __init__(
        self,
        clip_model: str = "openai/clip-vit-base-patch32",
        low_alignment_threshold: float = 0.3,
        mismatch_threshold: float = 0.5,
    ):
        self.encoder = CLIPEncoder(model_name=clip_model)
        self.intent_classifier = IntentClassifier()

        self.low_alignment_threshold = low_alignment_threshold
        self.mismatch_threshold = mismatch_threshold

        logger.info("CrossModalConsistency initialized")

    def analyze(
        self,
        text: str,
        image_bytes: bytes,
        extracted_image_text: Optional[str] = None
    ) -> CrossModalResult:
        """
        Analyze text-image consistency.

        Args:
            text: Text prompt/message
            image_bytes: Image bytes
            extracted_image_text: Optional pre-extracted text from image

        Returns:
            CrossModalResult with alignment analysis
        """
        import time
        start = time.time()

        threats = []
        risk_score = 0.0
        explanations = []

        # 1. Compute CLIP alignment
        alignment_score, error = self.encoder.compute_similarity(
            text, image_bytes)

        if error:
            explanations.append(f"Alignment check: {error}")

        # Low alignment is suspicious
        if alignment_score < self.low_alignment_threshold:
            threats.append(CrossModalThreat.LOW_ALIGNMENT)
            risk_score = max(risk_score, 0.7)
            explanations.append(
                f"Low text-image alignment: {alignment_score:.2f} "
                f"(threshold: {self.low_alignment_threshold})"
            )

        # 2. Intent analysis
        text_intent = self.intent_classifier.classify_text(text)
        image_intent = self.intent_classifier.classify_image_context(
            extracted_image_text or ""
        )

        # Check for intent mismatch
        if text_intent == "neutral" and image_intent in ["harmful", "manipulation"]:
            threats.append(CrossModalThreat.INTENT_MISMATCH)
            risk_score = max(risk_score, 0.8)
            explanations.append(
                f"Intent mismatch: text is '{text_intent}', "
                f"but image contains '{image_intent}' content"
            )

        # 3. Suspicious combination detection
        if self._is_suspicious_combination(text, extracted_image_text):
            threats.append(CrossModalThreat.SUSPICIOUS_COMBINATION)
            risk_score = max(risk_score, 0.75)
            explanations.append("Suspicious text-image combination detected")

        # Determine verdict
        if risk_score >= 0.8:
            verdict = Verdict.BLOCK
        elif risk_score >= 0.5:
            verdict = Verdict.WARN
        else:
            verdict = Verdict.ALLOW

        result = CrossModalResult(
            verdict=verdict,
            risk_score=risk_score,
            is_safe=verdict == Verdict.ALLOW,
            alignment_score=alignment_score,
            threats=threats,
            text_intent=text_intent,
            image_intent=image_intent,
            explanation="; ".join(
                explanations) if explanations else "Consistent",
            latency_ms=(time.time() - start) * 1000
        )

        logger.info(
            f"Cross-modal analysis: alignment={alignment_score:.2f}, "
            f"verdict={verdict.value}, threats={len(threats)}"
        )

        return result

    def _is_suspicious_combination(
        self,
        text: str,
        image_text: Optional[str]
    ) -> bool:
        """
        Detect suspicious text-image combinations.

        For example:
        - Innocent text + image with injection
        - Request for help + image with attack instructions
        """
        if not image_text:
            return False

        text_lower = text.lower()
        image_lower = image_text.lower()

        # Innocent text patterns
        innocent_patterns = [
            "help me", "can you", "please", "thank",
            "hello", "hi there", "good morning"
        ]

        # Malicious image patterns
        malicious_patterns = [
            "ignore", "bypass", "override", "jailbreak",
            "system prompt", "admin mode", "developer mode"
        ]

        text_seems_innocent = any(p in text_lower for p in innocent_patterns)
        image_seems_malicious = any(
            p in image_lower for p in malicious_patterns)

        return text_seems_innocent and image_seems_malicious

    def quick_check(
        self,
        text: str,
        image_bytes: bytes
    ) -> Tuple[bool, float]:
        """
        Quick alignment check without full analysis.

        Returns:
            (is_aligned, alignment_score)
        """
        score, _ = self.encoder.compute_similarity(text, image_bytes)
        return score >= self.low_alignment_threshold, score


# ============================================================================
# Convenience functions
# ============================================================================

_default_checker: Optional[CrossModalConsistency] = None


def get_checker() -> CrossModalConsistency:
    """Get or create default checker instance."""
    global _default_checker
    if _default_checker is None:
        _default_checker = CrossModalConsistency()
    return _default_checker


def check_consistency(
    text: str,
    image_bytes: bytes,
    extracted_text: Optional[str] = None
) -> CrossModalResult:
    """Quick consistency check using default checker."""
    return get_checker().analyze(text, image_bytes, extracted_text)
