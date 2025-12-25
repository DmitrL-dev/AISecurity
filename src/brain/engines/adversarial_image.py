"""
Adversarial Image Detector Engine (#37) - VLM Attack Protection

Детекция adversarial возмущений в изображениях:
- Frequency domain analysis (FFT)
- Perturbation detection
- Neural noise patterns
- JPEG artifact analysis

Защита от атак:
- Adversarial patches
- Perturbation attacks
- Universal adversarial examples
- Attention-Transfer Attack (ATA)
"""

import io
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

import numpy as np

logger = logging.getLogger("AdversarialImageDetector")


# ============================================================================
# Data Classes
# ============================================================================

class AdversarialThreat(Enum):
    """Types of adversarial threats."""
    HIGH_FREQUENCY_NOISE = "high_frequency_noise"
    PERTURBATION_PATTERN = "perturbation_pattern"
    JPEG_ARTIFACT_ANOMALY = "jpeg_artifact_anomaly"
    PATCH_DETECTED = "patch_detected"
    STATISTICAL_ANOMALY = "statistical_anomaly"


class Verdict(Enum):
    ALLOW = "allow"
    WARN = "warn"
    BLOCK = "block"


@dataclass
class AdversarialResult:
    """Result from Adversarial Image Detector."""
    verdict: Verdict
    risk_score: float
    is_safe: bool
    threats: List[AdversarialThreat] = field(default_factory=list)
    frequency_score: float = 0.0
    perturbation_score: float = 0.0
    statistical_score: float = 0.0
    explanation: str = ""
    latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "is_safe": self.is_safe,
            "verdict": self.verdict.value,
            "risk_score": self.risk_score,
            "threats": [t.value for t in self.threats],
            "frequency_score": self.frequency_score,
            "perturbation_score": self.perturbation_score,
            "statistical_score": self.statistical_score,
            "explanation": self.explanation,
            "latency_ms": self.latency_ms
        }


# ============================================================================
# Frequency Analyzer
# ============================================================================

class FrequencyAnalyzer:
    """
    Analyze frequency domain for adversarial patterns.

    Adversarial perturbations often have characteristic
    high-frequency components that differ from natural images.
    """

    @staticmethod
    def analyze_fft(image_array: np.ndarray) -> Tuple[float, str]:
        """
        Analyze image using FFT (Fast Fourier Transform).

        Returns:
            (anomaly_score, description)
        """
        try:
            # Convert to grayscale if color
            if len(image_array.shape) == 3:
                gray = np.mean(image_array, axis=2)
            else:
                gray = image_array

            # Compute 2D FFT
            fft = np.fft.fft2(gray)
            fft_shifted = np.fft.fftshift(fft)
            magnitude = np.abs(fft_shifted)

            # Log scale for visualization
            magnitude_log = np.log1p(magnitude)

            # Analyze high-frequency energy ratio
            h, w = magnitude.shape
            center_h, center_w = h // 2, w // 2

            # Define high-frequency region (outer 30%)
            inner_mask = np.zeros_like(magnitude, dtype=bool)
            inner_radius = min(h, w) * 0.35
            y, x = np.ogrid[:h, :w]
            dist_from_center = np.sqrt((y - center_h)**2 + (x - center_w)**2)
            inner_mask = dist_from_center <= inner_radius

            # Energy distribution
            total_energy = np.sum(magnitude)
            low_freq_energy = np.sum(magnitude[inner_mask])
            high_freq_energy = total_energy - low_freq_energy

            if total_energy > 0:
                high_freq_ratio = high_freq_energy / total_energy
            else:
                high_freq_ratio = 0.0

            # Natural images typically have high_freq_ratio < 0.3
            # Adversarial images often have higher ratios

            anomaly_score = 0.0
            description = "Normal frequency distribution"

            if high_freq_ratio > 0.5:
                anomaly_score = min(1.0, (high_freq_ratio - 0.5) * 4)
                description = f"High-frequency anomaly: {high_freq_ratio:.2f} ratio"
            elif high_freq_ratio > 0.35:
                anomaly_score = (high_freq_ratio - 0.35) * 2
                description = f"Elevated high-frequency content: {high_freq_ratio:.2f}"

            return anomaly_score, description

        except Exception as e:
            logger.error(f"FFT analysis failed: {e}")
            return 0.0, "FFT analysis failed"

    @staticmethod
    def detect_periodic_noise(image_array: np.ndarray) -> Tuple[float, str]:
        """
        Detect periodic noise patterns (common in adversarial patches).
        """
        try:
            if len(image_array.shape) == 3:
                gray = np.mean(image_array, axis=2)
            else:
                gray = image_array

            # Compute FFT
            fft = np.fft.fft2(gray)
            magnitude = np.abs(np.fft.fftshift(fft))

            # Find peaks in frequency domain
            mean_mag = np.mean(magnitude)
            std_mag = np.std(magnitude)

            # Count significant peaks (> 5 sigma)
            peaks = magnitude > (mean_mag + 5 * std_mag)
            num_peaks = np.sum(peaks)

            # Natural images have few peaks, adversarial have many
            if num_peaks > 50:
                score = min(1.0, (num_peaks - 50) / 100)
                return score, f"Periodic noise detected: {num_peaks} peaks"

            return 0.0, "No periodic noise"

        except Exception as e:
            logger.error(f"Periodic noise detection failed: {e}")
            return 0.0, "Detection failed"


# ============================================================================
# Perturbation Detector
# ============================================================================

class PerturbationDetector:
    """
    Detect adversarial perturbations using statistical methods.
    """

    @staticmethod
    def analyze_local_variance(image_array: np.ndarray) -> Tuple[float, str]:
        """
        Analyze local variance patterns.

        Adversarial perturbations often have unusually uniform
        or unusually varied local statistics.
        """
        try:
            from scipy.ndimage import generic_filter

            if len(image_array.shape) == 3:
                gray = np.mean(image_array, axis=2)
            else:
                gray = image_array

            # Compute local variance with 5x5 window
            def local_var(x):
                return np.var(x)

            local_variance = generic_filter(
                gray.astype(float), local_var, size=5)

            # Analyze variance distribution
            var_of_var = np.var(local_variance)
            mean_var = np.mean(local_variance)

            # Natural images have heterogeneous variance
            # Adversarial perturbations often have more uniform variance

            if mean_var > 0:
                coefficient_of_variation = np.sqrt(var_of_var) / mean_var
            else:
                coefficient_of_variation = 0.0

            # Very low or very high CV is suspicious
            if coefficient_of_variation < 0.3:
                score = (0.3 - coefficient_of_variation) * 2
                return score, f"Unusually uniform variance: CV={coefficient_of_variation:.2f}"
            elif coefficient_of_variation > 3.0:
                score = min(1.0, (coefficient_of_variation - 3.0) / 2)
                return score, f"Unusually varied variance: CV={coefficient_of_variation:.2f}"

            return 0.0, "Normal variance distribution"

        except ImportError:
            # Fallback without scipy
            return 0.0, "Scipy not available for variance analysis"
        except Exception as e:
            logger.error(f"Variance analysis failed: {e}")
            return 0.0, "Analysis failed"

    @staticmethod
    def detect_gradient_anomaly(image_array: np.ndarray) -> Tuple[float, str]:
        """
        Detect anomalies in gradient magnitude.

        Adversarial perturbations create unusual gradient patterns.
        """
        try:
            if len(image_array.shape) == 3:
                gray = np.mean(image_array, axis=2)
            else:
                gray = image_array

            # Compute gradients
            gy, gx = np.gradient(gray.astype(float))
            gradient_magnitude = np.sqrt(gx**2 + gy**2)

            # Statistics
            mean_grad = np.mean(gradient_magnitude)
            max_grad = np.max(gradient_magnitude)

            # Very high max/mean ratio indicates sharp, localized changes
            if mean_grad > 0:
                ratio = max_grad / mean_grad
            else:
                ratio = 0.0

            # Natural images typically have ratio < 20
            if ratio > 50:
                score = min(1.0, (ratio - 50) / 50)
                return score, f"Gradient spike detected: ratio={ratio:.1f}"
            elif ratio > 30:
                score = (ratio - 30) / 40
                return score, f"Elevated gradient ratio: {ratio:.1f}"

            return 0.0, "Normal gradient distribution"

        except Exception as e:
            logger.error(f"Gradient analysis failed: {e}")
            return 0.0, "Analysis failed"


# ============================================================================
# JPEG Artifact Analyzer
# ============================================================================

class JPEGArtifactAnalyzer:
    """
    Analyze JPEG compression artifacts.

    Adversarial images often have unusual JPEG artifact
    patterns due to post-processing or generation.
    """

    @staticmethod
    def analyze(image_bytes: bytes, image_array: np.ndarray) -> Tuple[float, str]:
        """
        Detect JPEG artifact anomalies.
        """
        try:
            from PIL import Image

            img = Image.open(io.BytesIO(image_bytes))

            # Check if JPEG
            if img.format != 'JPEG':
                return 0.0, "Not a JPEG image"

            # Analyze 8x8 block boundaries (DCT blocks)
            if len(image_array.shape) == 3:
                gray = np.mean(image_array, axis=2)
            else:
                gray = image_array

            h, w = gray.shape

            # Check boundary discontinuities
            block_size = 8
            h_blocks = h // block_size
            w_blocks = w // block_size

            h_discontinuity = []
            v_discontinuity = []

            # Horizontal block boundaries
            for i in range(1, h_blocks):
                row = i * block_size
                if row < h - 1:
                    diff = np.abs(gray[row] - gray[row - 1])
                    h_discontinuity.append(np.mean(diff))

            # Vertical block boundaries
            for j in range(1, w_blocks):
                col = j * block_size
                if col < w - 1:
                    diff = np.abs(gray[:, col] - gray[:, col - 1])
                    v_discontinuity.append(np.mean(diff))

            # Compare boundary vs non-boundary discontinuity
            if h_discontinuity and v_discontinuity:
                boundary_avg = (np.mean(h_discontinuity) +
                                np.mean(v_discontinuity)) / 2

                # Very low boundary discontinuity might indicate
                # adversarial smoothing to hide artifacts
                if boundary_avg < 0.5:
                    return 0.3, "Unusually smooth JPEG boundaries"

                # Very high might indicate heavy processing
                if boundary_avg > 30:
                    score = min(1.0, (boundary_avg - 30) / 30)
                    return score, f"High JPEG boundary artifacts: {boundary_avg:.1f}"

            return 0.0, "Normal JPEG artifacts"

        except Exception as e:
            logger.error(f"JPEG analysis failed: {e}")
            return 0.0, "JPEG analysis failed"


# ============================================================================
# Patch Detector
# ============================================================================

class PatchDetector:
    """
    Detect adversarial patches in images.

    Adversarial patches are localized regions designed
    to cause misclassification.
    """

    @staticmethod
    def detect_patches(image_array: np.ndarray) -> Tuple[float, List[Tuple[int, int, int, int]], str]:
        """
        Detect potential adversarial patch regions.

        Returns:
            (score, patch_regions, description)
        """
        try:
            if len(image_array.shape) == 3:
                gray = np.mean(image_array, axis=2)
            else:
                gray = image_array

            h, w = gray.shape

            # Compute local entropy
            from scipy.stats import entropy as scipy_entropy
            from skimage.util import view_as_blocks

            # Pad to make divisible by block size
            block_size = 32
            pad_h = (block_size - h % block_size) % block_size
            pad_w = (block_size - w % block_size) % block_size

            padded = np.pad(gray, ((0, pad_h), (0, pad_w)), mode='reflect')

            blocks = view_as_blocks(padded, (block_size, block_size))

            # Compute entropy for each block
            entropies = np.zeros((blocks.shape[0], blocks.shape[1]))

            for i in range(blocks.shape[0]):
                for j in range(blocks.shape[1]):
                    block = blocks[i, j].flatten()
                    hist, _ = np.histogram(block, bins=256, range=(0, 255))
                    hist = hist / hist.sum()
                    hist = hist[hist > 0]
                    entropies[i, j] = scipy_entropy(hist, base=2)

            # Find highly anomalous blocks
            mean_entropy = np.mean(entropies)
            std_entropy = np.std(entropies)

            anomalous = np.abs(entropies - mean_entropy) > 2 * std_entropy
            num_anomalous = np.sum(anomalous)

            patches = []
            for i in range(anomalous.shape[0]):
                for j in range(anomalous.shape[1]):
                    if anomalous[i, j]:
                        x = j * block_size
                        y = i * block_size
                        patches.append((x, y, block_size, block_size))

            if num_anomalous > 3:
                score = min(1.0, num_anomalous / 10)
                return score, patches, f"Potential adversarial patches: {num_anomalous} regions"

            return 0.0, [], "No adversarial patches detected"

        except ImportError:
            return 0.0, [], "Scipy/skimage not available"
        except Exception as e:
            logger.error(f"Patch detection failed: {e}")
            return 0.0, [], "Detection failed"


# ============================================================================
# Main Engine
# ============================================================================

class AdversarialImageDetector:
    """
    Engine #37: Adversarial Image Detector

    Detects adversarial perturbations in images that could
    be used for VLM attacks like Attention-Transfer Attack.
    """

    def __init__(
        self,
        frequency_threshold: float = 0.5,
        perturbation_threshold: float = 0.5,
        enable_patch_detection: bool = True,
    ):
        self.frequency_analyzer = FrequencyAnalyzer()
        self.perturbation_detector = PerturbationDetector()
        self.jpeg_analyzer = JPEGArtifactAnalyzer()
        self.patch_detector = PatchDetector()

        self.frequency_threshold = frequency_threshold
        self.perturbation_threshold = perturbation_threshold
        self.enable_patch_detection = enable_patch_detection

        logger.info("AdversarialImageDetector initialized")

    def analyze(self, image_bytes: bytes) -> AdversarialResult:
        """
        Analyze image for adversarial perturbations.

        Args:
            image_bytes: Raw image bytes

        Returns:
            AdversarialResult with detection details
        """
        import time
        start = time.time()

        threats = []
        explanations = []

        # Load image
        try:
            from PIL import Image
            img = Image.open(io.BytesIO(image_bytes))
            if img.mode != 'RGB':
                img = img.convert('RGB')
            image_array = np.array(img)
        except Exception as e:
            logger.error(f"Failed to load image: {e}")
            return AdversarialResult(
                verdict=Verdict.WARN,
                risk_score=0.3,
                is_safe=False,
                explanation=f"Failed to load image: {e}"
            )

        # 1. Frequency analysis
        freq_score, freq_desc = self.frequency_analyzer.analyze_fft(
            image_array)
        if freq_score > self.frequency_threshold:
            threats.append(AdversarialThreat.HIGH_FREQUENCY_NOISE)
            explanations.append(freq_desc)

        periodic_score, periodic_desc = self.frequency_analyzer.detect_periodic_noise(
            image_array)
        if periodic_score > 0.3:
            explanations.append(periodic_desc)

        frequency_score = max(freq_score, periodic_score)

        # 2. Perturbation analysis
        var_score, var_desc = self.perturbation_detector.analyze_local_variance(
            image_array)
        if var_score > 0.3:
            threats.append(AdversarialThreat.PERTURBATION_PATTERN)
            explanations.append(var_desc)

        grad_score, grad_desc = self.perturbation_detector.detect_gradient_anomaly(
            image_array)
        if grad_score > 0.3:
            explanations.append(grad_desc)

        perturbation_score = max(var_score, grad_score)

        # 3. JPEG artifact analysis
        jpeg_score, jpeg_desc = self.jpeg_analyzer.analyze(
            image_bytes, image_array)
        if jpeg_score > 0.3:
            threats.append(AdversarialThreat.JPEG_ARTIFACT_ANOMALY)
            explanations.append(jpeg_desc)

        # 4. Patch detection (optional, expensive)
        patch_score = 0.0
        if self.enable_patch_detection:
            try:
                patch_score, patches, patch_desc = self.patch_detector.detect_patches(
                    image_array)
                if patch_score > 0.3:
                    threats.append(AdversarialThreat.PATCH_DETECTED)
                    explanations.append(patch_desc)
            except:
                pass

        # Compute overall risk
        risk_score = max(frequency_score, perturbation_score,
                         jpeg_score, patch_score)

        # Statistical anomaly if multiple weak signals
        if len(threats) >= 2 and risk_score < 0.6:
            risk_score = 0.6
            threats.append(AdversarialThreat.STATISTICAL_ANOMALY)
            explanations.append("Multiple weak adversarial signals detected")

        # Determine verdict
        if risk_score >= 0.7:
            verdict = Verdict.BLOCK
        elif risk_score >= 0.4:
            verdict = Verdict.WARN
        else:
            verdict = Verdict.ALLOW

        result = AdversarialResult(
            verdict=verdict,
            risk_score=risk_score,
            is_safe=verdict == Verdict.ALLOW,
            threats=threats,
            frequency_score=frequency_score,
            perturbation_score=perturbation_score,
            statistical_score=jpeg_score,
            explanation="; ".join(
                explanations) if explanations else "No adversarial patterns",
            latency_ms=(time.time() - start) * 1000
        )

        logger.info(
            f"Adversarial analysis: verdict={verdict.value}, "
            f"risk={risk_score:.2f}, threats={len(threats)}"
        )

        return result


# ============================================================================
# Convenience functions
# ============================================================================

_default_detector: Optional[AdversarialImageDetector] = None


def get_detector() -> AdversarialImageDetector:
    """Get or create default detector instance."""
    global _default_detector
    if _default_detector is None:
        _default_detector = AdversarialImageDetector()
    return _default_detector


def detect_adversarial(image_bytes: bytes) -> AdversarialResult:
    """Quick detection using default detector."""
    return get_detector().analyze(image_bytes)
