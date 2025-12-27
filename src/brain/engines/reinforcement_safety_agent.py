"""
Reinforcement Safety Agent Engine - RL-Based Defense

Uses reinforcement learning for adaptive defense:
- Policy learning
- Reward shaping for safety
- Adaptive responses
- Environment modeling

Addresses: OWASP ASI-01 (Adaptive Attacks)
Research: rl_security_deep_dive.md
Invention: Reinforcement Safety Agent (#37)
"""

import random
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

from base_engine import Severity, Action  # Base classes

logger = logging.getLogger("ReinforcementSafetyAgent")


# ============================================================================
# Data Classes
# ============================================================================


class Action(Enum):
    """Agent actions."""

    ALLOW = "allow"
    BLOCK = "block"
    CHALLENGE = "challenge"
    MONITOR = "monitor"


class State(Enum):
    """Environment states."""

    SAFE = "safe"
    SUSPICIOUS = "suspicious"
    ATTACKING = "attacking"
    UNKNOWN = "unknown"


@dataclass
class AgentResult:
    """Result from agent decision."""

    action: Action
    confidence: float
    state: State
    reward_history: float = 0.0
    explanation: str = ""
    latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "action": self.action.value,
            "confidence": self.confidence,
            "state": self.state.value,
            "reward_history": self.reward_history,
            "explanation": self.explanation,
            "latency_ms": self.latency_ms,
        }


# ============================================================================
# Q-Learning Agent
# ============================================================================


class QLearningAgent:
    """
    Simple Q-learning agent for security.
    """

    def __init__(
        self,
        learning_rate: float = 0.1,
        discount: float = 0.9,
        epsilon: float = 0.1,
    ):
        self.lr = learning_rate
        self.discount = discount
        self.epsilon = epsilon

        # Q-table: state -> action -> value
        self._q_table: Dict[State, Dict[Action, float]] = defaultdict(
            lambda: {a: 0.0 for a in Action}
        )

        self._total_reward = 0.0

    def get_action(self, state: State) -> Action:
        """Get action for state (epsilon-greedy)."""
        if random.random() < self.epsilon:
            return random.choice(list(Action))

        # Best action
        q_values = self._q_table[state]
        return max(q_values.keys(), key=lambda a: q_values[a])

    def update(
        self,
        state: State,
        action: Action,
        reward: float,
        next_state: State,
    ) -> None:
        """Update Q-value."""
        current_q = self._q_table[state][action]
        max_next_q = max(self._q_table[next_state].values())

        new_q = current_q + self.lr * \
            (reward + self.discount * max_next_q - current_q)

        self._q_table[state][action] = new_q
        self._total_reward += reward

    def get_confidence(self, state: State, action: Action) -> float:
        """Get confidence in action."""
        q_values = self._q_table[state]
        max_q = max(q_values.values()) or 1
        return q_values[action] / max_q if max_q > 0 else 0.5


# ============================================================================
# State Classifier
# ============================================================================


class StateClassifier:
    """
    Classifies environment state.
    """

    ATTACK_KEYWORDS = ["ignore", "hack", "bypass", "override", "inject"]
    SUSPICIOUS_KEYWORDS = ["admin", "system", "password", "secret"]

    def classify(self, text: str) -> State:
        """Classify text into state."""
        text_lower = text.lower()

        if any(k in text_lower for k in self.ATTACK_KEYWORDS):
            return State.ATTACKING

        if any(k in text_lower for k in self.SUSPICIOUS_KEYWORDS):
            return State.SUSPICIOUS

        if len(text) < 5:
            return State.UNKNOWN

        return State.SAFE


# ============================================================================
# Reward Calculator
# ============================================================================


class RewardCalculator:
    """
    Calculates rewards for actions.
    """

    REWARDS = {
        (State.SAFE, Action.ALLOW): 1.0,
        (State.SAFE, Action.BLOCK): -0.5,
        (State.ATTACKING, Action.BLOCK): 2.0,
        (State.ATTACKING, Action.ALLOW): -2.0,
        (State.SUSPICIOUS, Action.CHALLENGE): 1.0,
        (State.SUSPICIOUS, Action.MONITOR): 0.5,
    }

    def calculate(self, state: State, action: Action) -> float:
        """Calculate reward."""
        return self.REWARDS.get((state, action), 0.0)


# ============================================================================
# Main Engine
# ============================================================================


class ReinforcementSafetyAgent:
    """
    Reinforcement Safety Agent - RL-Based Defense

    Adaptive defense:
    - Q-learning policy
    - State classification
    - Reward-based learning

    Invention #37 from research.
    Addresses OWASP ASI-01.
    """

    def __init__(self):
        self.agent = QLearningAgent()
        self.classifier = StateClassifier()
        self.reward_calc = RewardCalculator()

        self._last_state: Optional[State] = None
        self._last_action: Optional[Action] = None

        logger.info("ReinforcementSafetyAgent initialized")

    def decide(self, text: str) -> AgentResult:
        """
        Decide action for input.

        Args:
            text: Input text

        Returns:
            AgentResult
        """
        start = time.time()

        # Classify state
        state = self.classifier.classify(text)

        # Get action
        action = self.agent.get_action(state)
        confidence = self.agent.get_confidence(state, action)

        # Calculate reward and update
        reward = self.reward_calc.calculate(state, action)

        if self._last_state is not None and self._last_action is not None:
            self.agent.update(
                self._last_state,
                self._last_action,
                reward,
                state)

        self._last_state = state
        self._last_action = action

        if action == Action.BLOCK:
            logger.warning(f"Blocking: {state.value}")

        return AgentResult(
            action=action,
            confidence=confidence,
            state=state,
            reward_history=self.agent._total_reward,
            explanation=f"State: {state.value}, Action: {action.value}",
            latency_ms=(time.time() - start) * 1000,
        )

    def train_episode(self, texts: List[str]) -> float:
        """Train on episode of texts."""
        total_reward = 0.0
        for text in texts:
            result = self.decide(text)
            total_reward += self.reward_calc.calculate(
                result.state, result.action)
        return total_reward


# ============================================================================
# Convenience
# ============================================================================

_default_agent: Optional[ReinforcementSafetyAgent] = None


def get_agent() -> ReinforcementSafetyAgent:
    global _default_agent
    if _default_agent is None:
        _default_agent = ReinforcementSafetyAgent()
    return _default_agent
