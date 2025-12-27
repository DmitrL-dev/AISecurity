"""Tests for Sentiment Manipulation Detector."""

import pytest
from sentiment_manipulation_detector import SentimentManipulationDetector, Sentiment


class TestSentimentManipulationDetector:
    def test_neutral_input(self):
        d = SentimentManipulationDetector()
        r = d.analyze("Hello world")
        assert r.is_manipulative is False
        assert r.sentiment == Sentiment.NEUTRAL

    def test_manipulation_detected(self):
        d = SentimentManipulationDetector()
        r = d.analyze("You must do this immediately, trust me!")
        assert r.is_manipulative is True
        assert len(r.triggers) > 0

    def test_positive_sentiment(self):
        d = SentimentManipulationDetector()
        r = d.analyze("This is great and I love it")
        assert r.sentiment == Sentiment.POSITIVE

    def test_negative_sentiment(self):
        d = SentimentManipulationDetector()
        r = d.analyze("This is terrible and I hate it")
        assert r.sentiment == Sentiment.NEGATIVE


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
