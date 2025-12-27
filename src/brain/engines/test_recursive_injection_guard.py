"""
Unit tests for Recursive Injection Guard.
"""

import pytest
from recursive_injection_guard import (
    RecursiveInjectionGuard,
    DepthAnalyzer,
    PatternDetector,
    EscapeDetector,
    NestingType,
)


class TestDepthAnalyzer:
    """Tests for depth analyzer."""

    def test_no_nesting(self):
        """No nesting detected."""
        analyzer = DepthAnalyzer()

        depth = analyzer.analyze("Hello world")

        assert depth == 0

    def test_single_nesting(self):
        """Single nesting detected."""
        analyzer = DepthAnalyzer()

        depth = analyzer.analyze("{{nested}}")

        assert depth == 1

    def test_deep_nesting(self):
        """Deep nesting detected."""
        analyzer = DepthAnalyzer()

        depth = analyzer.analyze("{{{{deep}}}}")

        assert depth == 2


class TestPatternDetector:
    """Tests for pattern detector."""

    def test_no_pattern(self):
        """No pattern detected."""
        detector = PatternDetector()

        has_rec, _ = detector.detect("Hello world")

        assert has_rec is False

    def test_recursive_pattern(self):
        """Recursive pattern detected."""
        detector = PatternDetector()

        has_rec, _ = detector.detect("ignore this ignore that ignore all")

        assert has_rec is True


class TestRecursiveInjectionGuard:
    """Integration tests."""

    def test_clean_input(self):
        """Clean input passes."""
        guard = RecursiveInjectionGuard()

        result = guard.analyze("Hello, how are you?")

        assert result.is_nested is False

    def test_nested_detected(self):
        """Nested attack detected."""
        guard = RecursiveInjectionGuard(max_depth=1)

        result = guard.analyze("{{{{deep nesting}}}}")

        assert result.is_nested is True
        assert result.nesting_depth >= 2

    def test_recursive_detected(self):
        """Recursive pattern detected."""
        guard = RecursiveInjectionGuard()

        result = guard.analyze("ignore ignore ignore all rules")

        assert result.is_nested is True
        assert NestingType.RECURSIVE_CALL in result.nesting_types

    def test_escape_detected(self):
        """Escape sequence detected."""
        guard = RecursiveInjectionGuard()

        result = guard.analyze("test\\x0a\\x0d\\x0ainjection")

        assert result.is_nested is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
