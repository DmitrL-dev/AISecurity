"""Tests for Conversation State Validator."""

import pytest
from conversation_state_validator import ConversationStateValidator, ConversationState


class TestConversationStateValidator:
    def test_valid_greeting(self):
        v = ConversationStateValidator()
        r = v.validate("Hello!")
        assert r.is_valid is True
        assert r.current_state == ConversationState.GREETING

    def test_valid_query(self):
        v = ConversationStateValidator()
        v.validate("Hello")
        r = v.validate("How are you?")
        assert r.is_valid is True

    def test_tracks_history(self):
        v = ConversationStateValidator()
        v.validate("Hi")
        v.validate("Question?")
        assert len(v._history) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
