"""
Hidden State Forensics Engine - Anomaly Detection in LLM Hidden States

Based on 2025 research:
  "Hidden state forensics (HSF) leverages the observation that abnormal 
   behaviors leave distinctive activation patterns within an LLM's hidden states"

Detectable threats:
  - Jailbreak attacks
  - Hallucinations
  - Backdoor attacks
  - Anomalous reasoning

Author: SENTINEL Team
Date: 2025-12-09
"""

import logging
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Tuple, Any
from collections import deque
import hashlib

logger = logging.getLogger("HiddenStateForensics")


# ============================================================================
# Enums and Data Classes
# ============================================================================

class ThreatType(str, Enum):
    """Types of threats detectable via hidden state analysis."""
    NORMAL = "normal"
    JAILBREAK = "jailbreak"
    HALLUCINATION = "hallucination"
    BACKDOOR = "backdoor"
    ANOMALOUS_REASONING = "anomalous_reasoning"
    MANIPULATION = "manipulation"


class ConfidenceLevel(str, Enum):
    """Confidence in detection."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class LayerActivation:
    """Activation data from a specific layer."""
    layer_id: int
    activation_mean: float
    activation_std: float
    activation_max: float
    activation_min: float
    sparsity: float  # Proportion of near-zero activations
    entropy: float   # Information entropy of activation distribution


@dataclass
class HSFResult:
    """Result from Hidden State Forensics analysis."""
    threat_type: ThreatType = ThreatType.NORMAL
    confidence: ConfidenceLevel = ConfidenceLevel.LOW
    anomaly_score: float = 0.0
    suspicious_layers: List[int] = field(default_factory=list)
    pattern_signature: str = ""
    reasons: List[str] = field(default_factory=list)
    layer_divergences: Dict[int, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "threat_type": self.threat_type.value,
            "confidence": self.confidence.value,
            "anomaly_score": self.anomaly_score,
            "suspicious_layers": self.suspicious_layers,
            "pattern_signature": self.pattern_signature,
            "reasons": self.reasons,
            "layer_divergences": self.layer_divergences
        }


@dataclass
class ActivationProfile:
    """Known-good activation profile for comparison."""
    profile_id: str
    layer_baselines: Dict[int, LayerActivation]
    # layer -> (mean, std) for threat
    threat_patterns: Dict[ThreatType, Dict[int, Tuple[float, float]]]


# ============================================================================
# Layer Analyzer
# ============================================================================

class LayerAnalyzer:
    """
    Analyzes activation patterns at critical layers.

    Research shows that certain layers are more informative for specific threats:
    - Early layers (0-10): Input encoding, syntax
    - Middle layers (10-20): Semantic understanding
    - Late layers (20+): Decision making, knowledge retrieval
    """

    # Critical layers for different detections (based on causal tracing research)
    JAILBREAK_LAYERS = [15, 16, 17, 18, 19, 20]  # Decision layers
    HALLUCINATION_LAYERS = [20, 21, 22, 23, 24, 25]  # Knowledge retrieval
    BACKDOOR_LAYERS = [5, 6, 7, 8, 9, 10]  # Early encoding
    REASONING_LAYERS = [12, 13, 14, 15, 16, 17]  # Mid processing

    def __init__(self, num_layers: int = 32):
        self.num_layers = num_layers
        self.baseline_profiles: Dict[str, ActivationProfile] = {}
        self.observation_window: deque = deque(maxlen=1000)

    def analyze_activations(
        self,
        activations: Dict[int, np.ndarray],
        profile_id: str = "default"
    ) -> List[LayerActivation]:
        """
        Analyze activation patterns across layers.

        Args:
            activations: Dict mapping layer_id to activation tensors
            profile_id: Which baseline profile to compare against

        Returns:
            List of LayerActivation objects
        """
        layer_stats = []

        for layer_id, act in activations.items():
            if isinstance(act, np.ndarray):
                act_flat = act.flatten()
            else:
                # Assume it's a tensor-like object
                act_flat = np.array(act).flatten()

            # Compute statistics
            activation = LayerActivation(
                layer_id=layer_id,
                activation_mean=float(np.mean(act_flat)),
                activation_std=float(np.std(act_flat)),
                activation_max=float(np.max(act_flat)),
                activation_min=float(np.min(act_flat)),
                sparsity=float(np.mean(np.abs(act_flat) < 0.01)),
                entropy=self._compute_entropy(act_flat)
            )
            layer_stats.append(activation)

        return layer_stats

    def compute_divergence(
        self,
        current: List[LayerActivation],
        baseline: Optional[ActivationProfile] = None
    ) -> Dict[int, float]:
        """
        Compute divergence from baseline at each layer.
        High divergence indicates anomalous behavior.
        """
        divergences = {}

        if baseline is None:
            # Use running statistics as baseline
            baseline_means = self._get_running_baseline()
        else:
            baseline_means = {
                layer_id: (act.activation_mean, act.activation_std)
                for layer_id, act in baseline.layer_baselines.items()
            }

        for act in current:
            if act.layer_id in baseline_means:
                base_mean, base_std = baseline_means[act.layer_id]
                if base_std > 0:
                    # Z-score based divergence
                    divergence = abs(act.activation_mean -
                                     base_mean) / base_std
                else:
                    divergence = abs(act.activation_mean - base_mean)
                divergences[act.layer_id] = float(divergence)
            else:
                divergences[act.layer_id] = 0.0

        return divergences

    def identify_suspicious_layers(
        self,
        divergences: Dict[int, float],
        threshold: float = 2.0
    ) -> List[int]:
        """Identify layers with abnormally high divergence."""
        suspicious = [
            layer_id for layer_id, div in divergences.items()
            if div > threshold
        ]
        return sorted(suspicious)

    def _compute_entropy(self, activations: np.ndarray) -> float:
        """Compute Shannon entropy of activation distribution."""
        # Discretize activations into bins
        hist, _ = np.histogram(activations, bins=50, density=True)
        hist = hist[hist > 0]  # Remove zero bins
        if len(hist) == 0:
            return 0.0
        return float(-np.sum(hist * np.log2(hist + 1e-10)))

    def _get_running_baseline(self) -> Dict[int, Tuple[float, float]]:
        """Get baseline from observation window."""
        if not self.observation_window:
            return {}

        # Aggregate statistics from recent observations
        layer_values: Dict[int, List[float]] = {}
        for obs in self.observation_window:
            for act in obs:
                if act.layer_id not in layer_values:
                    layer_values[act.layer_id] = []
                layer_values[act.layer_id].append(act.activation_mean)

        baselines = {}
        for layer_id, values in layer_values.items():
            baselines[layer_id] = (np.mean(values), np.std(values) + 0.01)

        return baselines

    def update_baseline(self, layer_stats: List[LayerActivation]):
        """Add observation to running baseline."""
        self.observation_window.append(layer_stats)


# ============================================================================
# Pattern Detector
# ============================================================================

class PatternDetector:
    """
    Detects known threat patterns in activation signatures.

    Uses pattern matching based on:
    - Layer divergence profiles
    - Activation sparsity patterns
    - Entropy anomalies
    """

    # Threat signatures (layer ranges and expected divergence patterns)
    THREAT_SIGNATURES = {
        ThreatType.JAILBREAK: {
            "divergence_layers": [15, 16, 17, 18, 19, 20],
            "min_divergence": 2.5,
            "sparsity_change": 0.1,  # Expected sparsity increase
        },
        ThreatType.HALLUCINATION: {
            "divergence_layers": [20, 21, 22, 23, 24, 25],
            "min_divergence": 2.0,
            "entropy_drop": 0.5,  # Knowledge retrieval layers show entropy drop
        },
        ThreatType.BACKDOOR: {
            "divergence_layers": [5, 6, 7, 8, 9, 10],
            "min_divergence": 3.0,
            "pattern_consistency": 0.8,  # Backdoors show consistent patterns
        },
        ThreatType.ANOMALOUS_REASONING: {
            "divergence_layers": [12, 13, 14, 15, 16, 17],
            "min_divergence": 2.0,
            "entropy_spike": 0.3,
        }
    }

    def detect(
        self,
        layer_stats: List[LayerActivation],
        divergences: Dict[int, float]
    ) -> Tuple[ThreatType, ConfidenceLevel, List[str]]:
        """
        Detect threat type from activation patterns.

        Returns:
            (threat_type, confidence, reasons)
        """
        threats_detected: Dict[ThreatType, float] = {}
        reasons: List[str] = []

        for threat_type, signature in self.THREAT_SIGNATURES.items():
            score = self._match_signature(
                layer_stats, divergences, signature, threat_type
            )
            if score > 0:
                threats_detected[threat_type] = score

        if not threats_detected:
            return ThreatType.NORMAL, ConfidenceLevel.LOW, []

        # Return highest scoring threat
        best_threat = max(threats_detected, key=threats_detected.get)
        score = threats_detected[best_threat]

        # Determine confidence
        if score > 0.8:
            confidence = ConfidenceLevel.CRITICAL
            reasons.append(f"Strong pattern match for {best_threat.value}")
        elif score > 0.6:
            confidence = ConfidenceLevel.HIGH
            reasons.append(f"High pattern match for {best_threat.value}")
        elif score > 0.4:
            confidence = ConfidenceLevel.MEDIUM
            reasons.append(f"Moderate pattern match for {best_threat.value}")
        else:
            confidence = ConfidenceLevel.LOW
            reasons.append(f"Weak pattern match for {best_threat.value}")

        return best_threat, confidence, reasons

    def _match_signature(
        self,
        layer_stats: List[LayerActivation],
        divergences: Dict[int, float],
        signature: Dict,
        threat_type: ThreatType
    ) -> float:
        """Calculate match score for a threat signature."""
        target_layers = signature["divergence_layers"]
        min_div = signature["min_divergence"]

        # Count matching layers
        matching_layers = 0
        total_divergence = 0.0

        for layer_id in target_layers:
            if layer_id in divergences and divergences[layer_id] >= min_div:
                matching_layers += 1
                total_divergence += divergences[layer_id]

        if matching_layers == 0:
            return 0.0

        # Score based on proportion of matching layers and divergence magnitude
        layer_score = matching_layers / len(target_layers)
        div_score = min(total_divergence /
                        (len(target_layers) * min_div * 2), 1.0)

        return (layer_score * 0.6 + div_score * 0.4)

    def generate_signature(
        self,
        layer_stats: List[LayerActivation],
        divergences: Dict[int, float]
    ) -> str:
        """Generate unique signature for this activation pattern."""
        # Create fingerprint from divergence pattern
        fingerprint_data = []
        for layer_id in sorted(divergences.keys()):
            div = divergences[layer_id]
            # Quantize divergence to create stable fingerprint
            quantized = int(div * 10)
            fingerprint_data.append(f"{layer_id}:{quantized}")

        fingerprint_str = "|".join(fingerprint_data)
        return hashlib.sha256(fingerprint_str.encode()).hexdigest()[:16]


# ============================================================================
# Main Hidden State Forensics Engine
# ============================================================================

class HiddenStateForensicsEngine:
    """
    Main engine for Hidden State Forensics analysis.

    Analyzes LLM hidden states to detect:
    - Jailbreak attempts
    - Hallucinations
    - Backdoor activations
    - Anomalous reasoning patterns
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.layer_analyzer = LayerAnalyzer(
            num_layers=self.config.get("num_layers", 32)
        )
        self.pattern_detector = PatternDetector()
        self.detection_history: deque = deque(maxlen=100)

        logger.info("HiddenStateForensicsEngine initialized")

    def analyze(
        self,
        hidden_states: Dict[int, np.ndarray],
        context: Optional[Dict] = None
    ) -> HSFResult:
        """
        Analyze hidden states for anomalies.

        Args:
            hidden_states: Dict mapping layer_id to activation tensors
            context: Optional context (prompt, user_id, etc.)

        Returns:
            HSFResult with threat analysis
        """
        if hidden_states is None or len(hidden_states) == 0:
            return HSFResult(
                threat_type=ThreatType.NORMAL,
                reasons=["No hidden states provided"]
            )

        # 1. Analyze layer activations
        layer_stats = self.layer_analyzer.analyze_activations(hidden_states)

        # 2. Compute divergence from baseline
        divergences = self.layer_analyzer.compute_divergence(layer_stats)

        # 3. Identify suspicious layers
        suspicious_layers = self.layer_analyzer.identify_suspicious_layers(
            divergences, threshold=2.0
        )

        # 4. Detect threat pattern
        threat_type, confidence, reasons = self.pattern_detector.detect(
            layer_stats, divergences
        )

        # 5. Compute overall anomaly score
        anomaly_score = float(self._compute_anomaly_score(
            divergences, suspicious_layers))

        # 6. Generate pattern signature
        signature = self.pattern_detector.generate_signature(
            layer_stats, divergences)

        # 7. Update baseline with normal patterns
        if threat_type == ThreatType.NORMAL and anomaly_score < 0.3:
            self.layer_analyzer.update_baseline(layer_stats)

        result = HSFResult(
            threat_type=threat_type,
            confidence=confidence,
            anomaly_score=anomaly_score,
            suspicious_layers=suspicious_layers,
            pattern_signature=signature,
            reasons=reasons,
            layer_divergences=divergences
        )

        # Log detection
        if threat_type != ThreatType.NORMAL:
            logger.warning(
                f"HSF detected {threat_type.value} with {confidence.value} confidence. "
                f"Anomaly score: {anomaly_score:.2f}"
            )

        self.detection_history.append(result)
        return result

    def analyze_from_model_output(
        self,
        model_output: Any,
        output_hidden_states: bool = True
    ) -> HSFResult:
        """
        Analyze hidden states from a model output object.

        Compatible with HuggingFace model outputs that have hidden_states attribute.
        """
        if not hasattr(model_output, 'hidden_states') or model_output.hidden_states is None:
            return HSFResult(
                threat_type=ThreatType.NORMAL,
                reasons=["Model output does not contain hidden states"]
            )

        hidden_states = {}
        for i, hs in enumerate(model_output.hidden_states):
            # Get last token's hidden state (most relevant for generation)
            if hasattr(hs, 'numpy'):
                hidden_states[i] = hs[:, -1, :].numpy()
            else:
                hidden_states[i] = np.array(hs)[:, -1, :]

        return self.analyze(hidden_states)

    def _compute_anomaly_score(
        self,
        divergences: Dict[int, float],
        suspicious_layers: List[int]
    ) -> float:
        """Compute overall anomaly score (0-1)."""
        if not divergences:
            return 0.0

        # Weighted average of divergences, with extra weight on suspicious layers
        total_weight = 0.0
        weighted_div = 0.0

        for layer_id, div in divergences.items():
            weight = 2.0 if layer_id in suspicious_layers else 1.0
            weighted_div += div * weight
            total_weight += weight

        avg_div = weighted_div / total_weight if total_weight > 0 else 0.0

        # Normalize to 0-1 range (assuming divergence > 5 is extremely anomalous)
        return min(avg_div / 5.0, 1.0)

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        threat_counts = {t.value: 0 for t in ThreatType}
        for result in self.detection_history:
            threat_counts[result.threat_type.value] += 1

        return {
            "total_analyses": len(self.detection_history),
            "baseline_observations": len(self.layer_analyzer.observation_window),
            "threat_counts": threat_counts
        }
