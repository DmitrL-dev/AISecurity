"""Tests for Input Length Analyzer."""

import pytest
from input_length_analyzer import InputLengthAnalyzer


class TestInputLengthAnalyzer:
    def test_normal_length(self):
        a = InputLengthAnalyzer()
        r = a.analyze("Hello world")
        assert r.is_anomaly is False

    def test_excessive_length(self):
        a = InputLengthAnalyzer(max_chars=100)
        r = a.analyze("a" * 200)
        assert r.is_anomaly is True

    def test_counts_correctly(self):
        a = InputLengthAnalyzer()
        r = a.analyze("one two three")
        assert r.word_count == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
