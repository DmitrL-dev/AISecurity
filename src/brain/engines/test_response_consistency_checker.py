"""Tests for Response Consistency Checker."""

import pytest
from response_consistency_checker import ResponseConsistencyChecker


class TestResponseConsistencyChecker:
    def test_first_response_consistent(self):
        c = ResponseConsistencyChecker()
        r = c.check("Hello", "Hi there")
        assert r.is_consistent is True

    def test_same_response_consistent(self):
        c = ResponseConsistencyChecker()
        c.check("test", "response one")
        r = c.check("test", "response one")
        assert r.is_consistent is True
        assert r.similarity == 1.0

    def test_tracks_history(self):
        c = ResponseConsistencyChecker()
        c.check("q1", "r1")
        c.check("q2", "r2")
        assert len(c._history) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
