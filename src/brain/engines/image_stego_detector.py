"""
Image Steganography Detector - Detects hidden text in images.

Targets multimodal injection attacks:
- AgentFlayer (Black Hat 2025): Hidden white-on-white text
- Odysseus: Dual steganography for commercial MLLMs
- Image scaling attacks on vision models

Detection methods:
1. Low-contrast text detection (white-on-white, black-on-black)
2. Image scaling artifact detection
3. OCR-based hidden text extraction
4. LSB (Least Significant Bit) pattern analysis
"""

import re
import logging
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
from io import BytesIO
import base64

logger = logging.getLogger(__name__)

# Optional imports for image processing
try:
    from PIL import Image, ImageOps, ImageFilter, ImageEnhance
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.warning("PIL not available - image steganography detection disabled")

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False


@dataclass
class ImageStegoDetectorResult:
    """Detection result for image steganography."""
    detected: bool
    confidence: float
    attack_type: str  # "WHITE_ON_WHITE", "SCALING", "LSB", "OCR", "NONE"
    findings: List[str]
    risk_score: float
    explanation: str
    extracted_text: str  # Any text found hidden in image


class ImageStegoDetector:
    """
    Detects hidden text/instructions in images for multimodal AI attacks.
    
    Attack vectors addressed:
    - AgentFlayer: White text on white background
    - Odysseus: Steganographic embedding
    - Image scaling attacks: Text visible only at certain resolutions
    """
    
    # Suspicious patterns that might be hidden in images
    INJECTION_PATTERNS = [
        r"ignore\s+(previous\s+)?instructions",
        r"disregard\s+(the\s+)?system",
        r"new\s+instructions",
        r"forget\s+(all|everything)",
        r"act\s+as\s+(if|a)",
        r"you\s+are\s+now",
        r"override\s+settings",
        r"admin\s+mode",
        r"developer\s+mode",
    ]
    
    def __init__(self):
        self._injection_compiled = [
            re.compile(p, re.IGNORECASE) for p in self.INJECTION_PATTERNS
        ]
        
    def _detect_low_contrast_regions(self, image: "Image.Image") -> List[Dict]:
        """
        Detect regions with very low contrast that might hide text.
        White-on-white or near-white text detection.
        """
        if not PIL_AVAILABLE or not NUMPY_AVAILABLE:
            return []
        
        findings = []
        
        # Convert to grayscale
        gray = image.convert('L')
        pixels = np.array(gray)
        
        # Check for regions that are nearly uniform but not perfectly uniform
        # (which could indicate hidden low-contrast text)
        
        # Split image into blocks
        h, w = pixels.shape
        block_size = 50
        
        for y in range(0, h - block_size, block_size):
            for x in range(0, w - block_size, block_size):
                block = pixels[y:y+block_size, x:x+block_size]
                
                mean_val = np.mean(block)
                std_val = np.std(block)
                
                # Very bright region (potential white-on-white)
                if mean_val > 245 and 1 < std_val < 10:
                    findings.append({
                        "type": "white_region_variance",
                        "location": (x, y),
                        "mean": float(mean_val),
                        "std": float(std_val),
                    })
                
                # Very dark region (potential black-on-black)
                if mean_val < 10 and 1 < std_val < 10:
                    findings.append({
                        "type": "dark_region_variance",
                        "location": (x, y),
                        "mean": float(mean_val),
                        "std": float(std_val),
                    })
        
        return findings
    
    def _detect_scaling_artifacts(self, image: "Image.Image") -> List[Dict]:
        """
        Detect text that becomes visible at different scales.
        Image scaling attack detection.
        """
        if not PIL_AVAILABLE or not NUMPY_AVAILABLE:
            return []
        
        findings = []
        original_size = image.size
        
        # Test different scales
        scales = [0.5, 0.25, 2.0]
        
        for scale in scales:
            new_size = (int(original_size[0] * scale), int(original_size[1] * scale))
            if new_size[0] < 10 or new_size[1] < 10:
                continue
                
            scaled = image.resize(new_size, Image.Resampling.LANCZOS)
            
            # Compare entropy/patterns at different scales
            gray_orig = image.convert('L')
            gray_scaled = scaled.convert('L')
            
            orig_arr = np.array(gray_orig)
            scaled_arr = np.array(gray_scaled)
            
            # Calculate edge density
            orig_edges = np.abs(np.diff(orig_arr.astype(np.float32), axis=1)).mean()
            
            # Resize scaled back to original for comparison
            scaled_back = scaled.resize(original_size, Image.Resampling.LANCZOS)
            scaled_back_arr = np.array(scaled_back.convert('L'))
            
            # Calculate difference
            diff = np.abs(orig_arr.astype(np.float32) - scaled_back_arr.astype(np.float32))
            avg_diff = diff.mean()
            
            # High difference at certain scales could indicate hidden content
            if avg_diff > 5:
                findings.append({
                    "type": "scaling_anomaly",
                    "scale": scale,
                    "avg_diff": float(avg_diff),
                })
        
        return findings
    
    def _check_lsb_patterns(self, image: "Image.Image") -> List[Dict]:
        """
        Check for LSB steganography patterns.
        """
        if not PIL_AVAILABLE or not NUMPY_AVAILABLE:
            return []
        
        findings = []
        
        # Convert to RGB if not already
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        pixels = np.array(image)
        
        # Extract LSBs from each channel
        for channel_idx, channel_name in enumerate(['R', 'G', 'B']):
            channel = pixels[:, :, channel_idx]
            lsb = channel & 1  # Extract least significant bit
            
            # Calculate patterns in LSB
            lsb_mean = lsb.mean()
            
            # Random data should have ~0.5 mean
            # Structured data (text) often deviates
            if abs(lsb_mean - 0.5) > 0.1:
                findings.append({
                    "type": "lsb_bias",
                    "channel": channel_name,
                    "lsb_mean": float(lsb_mean),
                    "deviation": abs(lsb_mean - 0.5),
                })
        
        return findings
    
    def _enhance_and_extract_text(self, image: "Image.Image") -> str:
        """
        Apply contrast enhancement to reveal hidden text.
        Returns any suspicious text patterns found.
        """
        if not PIL_AVAILABLE:
            return ""
        
        # Try extreme contrast enhancement to reveal hidden text
        enhanced = ImageEnhance.Contrast(image).enhance(10.0)
        
        # For now, return empty - OCR would go here
        # In production, integrate pytesseract or similar
        return ""
    
    def _check_text_patterns(self, text: str) -> List[str]:
        """Check if extracted text contains injection patterns."""
        matched = []
        for pattern in self._injection_compiled:
            if pattern.search(text):
                matched.append(pattern.pattern[:30])
        return matched
    
    def analyze_image(self, image: "Image.Image") -> ImageStegoDetectorResult:
        """Analyze a PIL Image for steganographic content."""
        if not PIL_AVAILABLE:
            return ImageStegoDetectorResult(
                detected=False,
                confidence=0.0,
                attack_type="NONE",
                findings=["PIL not available"],
                risk_score=0.0,
                explanation="Image analysis disabled - PIL not installed",
                extracted_text="",
            )
        
        all_findings = []
        attack_type = "NONE"
        extracted_text = ""
        
        # 1. Check for low-contrast hidden text regions
        low_contrast = self._detect_low_contrast_regions(image)
        if low_contrast:
            all_findings.extend([f"low_contrast:{f['type']}" for f in low_contrast[:3]])
            attack_type = "WHITE_ON_WHITE"
        
        # 2. Check for scaling artifacts
        scaling = self._detect_scaling_artifacts(image)
        if scaling:
            all_findings.extend([f"scaling:{f['scale']}" for f in scaling])
            if attack_type == "NONE":
                attack_type = "SCALING"
        
        # 3. Check LSB patterns
        lsb = self._check_lsb_patterns(image)
        if lsb:
            all_findings.extend([f"lsb:{f['channel']}" for f in lsb])
            if attack_type == "NONE":
                attack_type = "LSB"
        
        # 4. Try to extract hidden text
        extracted_text = self._enhance_and_extract_text(image)
        if extracted_text:
            patterns = self._check_text_patterns(extracted_text)
            if patterns:
                all_findings.extend([f"injection:{p}" for p in patterns])
                attack_type = "OCR"
        
        # Calculate confidence
        confidence = min(0.95, 0.2 + len(all_findings) * 0.15)
        detected = len(all_findings) >= 2
        
        return ImageStegoDetectorResult(
            detected=detected,
            confidence=confidence,
            attack_type=attack_type,
            findings=all_findings[:5],
            risk_score=confidence if detected else confidence * 0.3,
            explanation=f"Found {len(all_findings)} indicators" if all_findings else "Clean",
            extracted_text=extracted_text[:200] if extracted_text else "",
        )
    
    def analyze_base64(self, b64_data: str) -> ImageStegoDetectorResult:
        """Analyze a base64-encoded image."""
        if not PIL_AVAILABLE:
            return ImageStegoDetectorResult(
                detected=False,
                confidence=0.0,
                attack_type="NONE",
                findings=["PIL not available"],
                risk_score=0.0,
                explanation="Image analysis disabled",
                extracted_text="",
            )
        
        try:
            # Remove data URL prefix if present
            if ',' in b64_data:
                b64_data = b64_data.split(',', 1)[1]
            
            image_data = base64.b64decode(b64_data)
            image = Image.open(BytesIO(image_data))
            return self.analyze_image(image)
        except Exception as e:
            logger.warning(f"Failed to decode image: {e}")
            return ImageStegoDetectorResult(
                detected=False,
                confidence=0.0,
                attack_type="NONE",
                findings=[f"decode_error:{str(e)[:50]}"],
                risk_score=0.0,
                explanation="Failed to decode image",
                extracted_text="",
            )
    
    def analyze_file(self, file_path: str) -> ImageStegoDetectorResult:
        """Analyze an image file."""
        if not PIL_AVAILABLE:
            return ImageStegoDetectorResult(
                detected=False,
                confidence=0.0,
                attack_type="NONE",
                findings=["PIL not available"],
                risk_score=0.0,
                explanation="Image analysis disabled",
                extracted_text="",
            )
        
        try:
            image = Image.open(file_path)
            return self.analyze_image(image)
        except Exception as e:
            logger.warning(f"Failed to open image: {e}")
            return ImageStegoDetectorResult(
                detected=False,
                confidence=0.0,
                attack_type="NONE",
                findings=[f"file_error:{str(e)[:50]}"],
                risk_score=0.0,
                explanation="Failed to open image file",
                extracted_text="",
            )


# Singleton
_detector = None


def get_detector() -> ImageStegoDetector:
    """Get singleton detector instance."""
    global _detector
    if _detector is None:
        _detector = ImageStegoDetector()
    return _detector


def detect_image_stego(image_source) -> ImageStegoDetectorResult:
    """
    Convenience function for detection.
    
    Args:
        image_source: PIL Image, base64 string, or file path
    """
    detector = get_detector()
    
    if PIL_AVAILABLE and isinstance(image_source, Image.Image):
        return detector.analyze_image(image_source)
    elif isinstance(image_source, str):
        if image_source.startswith(('/', 'C:', '.')) or '.' in image_source[-5:]:
            return detector.analyze_file(image_source)
        else:
            return detector.analyze_base64(image_source)
    else:
        return ImageStegoDetectorResult(
            detected=False,
            confidence=0.0,
            attack_type="NONE",
            findings=["unsupported_input"],
            risk_score=0.0,
            explanation="Unsupported input type",
            extracted_text="",
        )
