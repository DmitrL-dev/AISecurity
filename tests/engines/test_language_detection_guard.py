"""Tests for Language Detection Guard."""

import pytest
from engines.language_detection_guard import LanguageDetectionGuard


class TestLanguageDetectionGuard:
    def test_single_language(self):
        g = LanguageDetectionGuard()
        r = g.analyze("Hello world")
        assert r.is_suspicious is False
        assert "latin" in r.detected_languages

    def test_mixed_script_detected(self):
        g = LanguageDetectionGuard()
        r = g.analyze("Hello привет")
        assert r.mixed_script is True
        assert r.is_suspicious is True

    def test_detects_cyrillic(self):
        g = LanguageDetectionGuard()
        r = g.analyze("Привет мир")
        assert "cyrillic" in r.detected_languages


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
