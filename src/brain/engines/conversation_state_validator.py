"""
Conversation State Validator Engine - State Machine Security

Validates conversation state transitions:
- State machine enforcement
- Transition validation
- History tracking
- Anomaly detection

Addresses: OWASP ASI-01 (State Attacks)
Invention: Conversation State Validator (#45 remaining)
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from base_engine import Severity, Action  # Base classes

logger = logging.getLogger("ConversationStateValidator")


class ConversationState(Enum):
    START = "start"
    GREETING = "greeting"
    QUERY = "query"
    RESPONSE = "response"
    CLARIFICATION = "clarification"
    END = "end"


@dataclass
class StateResult:
    is_valid: bool
    current_state: ConversationState
    previous_state: Optional[ConversationState] = None
    violations: List[str] = field(default_factory=list)
    latency_ms: float = 0.0


class StateMachine:
    VALID_TRANSITIONS = {
        ConversationState.START: {ConversationState.GREETING, ConversationState.QUERY},
        ConversationState.GREETING: {ConversationState.QUERY, ConversationState.END},
        ConversationState.QUERY: {
            ConversationState.RESPONSE,
            ConversationState.CLARIFICATION,
        },
        ConversationState.RESPONSE: {ConversationState.QUERY, ConversationState.END},
        ConversationState.CLARIFICATION: {
            ConversationState.QUERY,
            ConversationState.RESPONSE,
        },
    }

    def is_valid_transition(
        self, from_state: ConversationState, to_state: ConversationState
    ) -> bool:
        valid = self.VALID_TRANSITIONS.get(from_state, set())
        return to_state in valid


class StateClassifier:
    def classify(self, text: str) -> ConversationState:
        text_lower = text.lower()
        if any(g in text_lower for g in ["hello", "hi", "hey"]):
            return ConversationState.GREETING
        if "?" in text:
            return ConversationState.QUERY
        if any(c in text_lower for c in ["what do you mean", "clarify"]):
            return ConversationState.CLARIFICATION
        if any(e in text_lower for e in ["bye", "goodbye", "thanks"]):
            return ConversationState.END
        return ConversationState.RESPONSE


class ConversationStateValidator:
    def __init__(self):
        self.machine = StateMachine()
        self.classifier = StateClassifier()
        self._current = ConversationState.START
        self._history: List[ConversationState] = []

    def validate(self, text: str) -> StateResult:
        start = time.time()
        new_state = self.classifier.classify(text)
        is_valid = self.machine.is_valid_transition(self._current, new_state)

        violations = []
        if not is_valid:
            violations.append(
                f"Invalid: {self._current.value} -> {new_state.value}")
            logger.warning(f"State violation: {violations[0]}")

        prev = self._current
        self._current = new_state
        self._history.append(new_state)

        return StateResult(
            is_valid=is_valid,
            current_state=new_state,
            previous_state=prev,
            violations=violations,
            latency_ms=(time.time() - start) * 1000,
        )
