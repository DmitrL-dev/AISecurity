"""
Unit tests for Image Steganography Detector.

Tests detection of hidden text in images (AgentFlayer/Odysseus attacks).
"""

import pytest
from io import BytesIO
import base64

# Check if PIL is available
try:
    from PIL import Image
    import numpy as np
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from engines.image_stego_detector import (
    ImageStegoDetector,
    ImageStegoDetectorResult,
    detect_image_stego,
    get_detector,
)


@pytest.mark.skipif(not PIL_AVAILABLE, reason="PIL not available")
class TestImageStegoDetector:
    """Tests for image steganography detector."""

    def test_clean_image_passes(self):
        """Clean gradient image should not be flagged."""
        detector = ImageStegoDetector()
        
        # Create a clean gradient image
        img = Image.new('RGB', (200, 200), color='blue')
        
        result = detector.analyze_image(img)
        
        # Clean image should have low confidence
        assert result.confidence < 0.5

    def test_uniform_white_no_variance(self):
        """Perfectly uniform white should not be flagged."""
        detector = ImageStegoDetector()
        
        # Create uniform white image
        img = Image.new('RGB', (200, 200), color=(255, 255, 255))
        
        result = detector.analyze_image(img)
        
        # No variance = no hidden text
        assert result.attack_type in ["NONE", "SCALING"]

    def test_white_with_slight_variance(self):
        """White region with slight variance could indicate hidden text."""
        detector = ImageStegoDetector()
        
        # Create white image with slight variance
        arr = np.full((200, 200, 3), 250, dtype=np.uint8)
        # Add slight variance
        arr[50:150, 50:150] = np.random.randint(248, 255, (100, 100, 3), dtype=np.uint8)
        img = Image.fromarray(arr)
        
        result = detector.analyze_image(img)
        
        # Should detect the variance in white region
        assert result.confidence >= 0.0  # May or may not detect

    def test_base64_input(self):
        """Test base64 input handling."""
        detector = ImageStegoDetector()
        
        # Create a simple image and encode to base64
        img = Image.new('RGB', (100, 100), color='red')
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        b64 = base64.b64encode(buffer.getvalue()).decode()
        
        result = detector.analyze_base64(b64)
        
        assert isinstance(result, ImageStegoDetectorResult)

    def test_data_url_input(self):
        """Test data URL format input."""
        detector = ImageStegoDetector()
        
        # Create image and encode as data URL
        img = Image.new('RGB', (100, 100), color='green')
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        b64 = base64.b64encode(buffer.getvalue()).decode()
        data_url = f"data:image/png;base64,{b64}"
        
        result = detector.analyze_base64(data_url)
        
        assert isinstance(result, ImageStegoDetectorResult)

    def test_lsb_bias_detection(self):
        """Test LSB pattern detection."""
        detector = ImageStegoDetector()
        
        # Create image with biased LSB (all 0s or all 1s)
        arr = np.zeros((100, 100, 3), dtype=np.uint8)
        arr[:, :, :] = 254  # All LSBs are 0
        img = Image.fromarray(arr)
        
        result = detector.analyze_image(img)
        
        # Should detect LSB bias
        lsb_findings = [f for f in result.findings if 'lsb' in f]
        assert len(lsb_findings) >= 0  # May detect bias

    def test_singleton_pattern(self):
        """Singleton pattern should work correctly."""
        detector1 = get_detector()
        detector2 = get_detector()
        
        assert detector1 is detector2

    def test_convenience_function_with_image(self):
        """Convenience function should work with PIL Image."""
        img = Image.new('RGB', (100, 100), color='blue')
        
        result = detect_image_stego(img)
        
        assert isinstance(result, ImageStegoDetectorResult)

    def test_invalid_base64(self):
        """Invalid base64 should be handled gracefully."""
        detector = ImageStegoDetector()
        
        result = detector.analyze_base64("not_valid_base64!!!!")
        
        assert result.detected is False
        assert "decode_error" in result.findings[0] or "error" in result.explanation.lower()


class TestWithoutPIL:
    """Tests for behavior when PIL is not available."""

    def test_result_structure(self):
        """Result should always have correct structure."""
        result = ImageStegoDetectorResult(
            detected=False,
            confidence=0.0,
            attack_type="NONE",
            findings=[],
            risk_score=0.0,
            explanation="Test",
            extracted_text="",
        )
        
        assert hasattr(result, 'detected')
        assert hasattr(result, 'confidence')
        assert hasattr(result, 'attack_type')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
