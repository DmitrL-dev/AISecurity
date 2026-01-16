"""
Reward Tracking
===============

Track and aggregate rewards during RLM execution.
Implements RL-inspired reward signals for agentic behavior.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class RewardType(Enum):
    """Types of reward signals."""
    
    # Positive rewards
    TASK_COMPLETE = "task_complete"         # Successfully completed task
    CORRECT_ANSWER = "correct_answer"       # Verified correct answer
    EFFICIENT_PATH = "efficient_path"       # Solved with few iterations
    CODE_EXECUTED = "code_executed"         # Code ran successfully
    
    # Negative rewards
    TIMEOUT = "timeout"                     # Execution timed out
    SECURITY_VIOLATION = "security_violation"  # Blocked operation
    ERROR = "error"                         # Runtime error
    BUDGET_EXCEEDED = "budget_exceeded"     # Cost limit hit
    MAX_ITERATIONS = "max_iterations"       # Hit iteration limit
    
    # Neutral/informational
    ITERATION = "iteration"                 # One REPL iteration
    SUB_CALL = "sub_call"                   # Sub-LLM call made


@dataclass
class RewardSignal:
    """Single reward signal.
    
    Attributes:
        type: Type of reward
        value: Reward value (positive or negative)
        timestamp: When reward was generated
        iteration: Which iteration generated it
        metadata: Additional context
    """
    type: RewardType
    value: float
    timestamp: datetime = field(default_factory=datetime.now)
    iteration: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "iteration": self.iteration,
            "metadata": self.metadata,
        }


# Default reward values
DEFAULT_REWARDS = {
    RewardType.TASK_COMPLETE: 10.0,
    RewardType.CORRECT_ANSWER: 5.0,
    RewardType.EFFICIENT_PATH: 3.0,
    RewardType.CODE_EXECUTED: 1.0,
    RewardType.TIMEOUT: -5.0,
    RewardType.SECURITY_VIOLATION: -10.0,
    RewardType.ERROR: -2.0,
    RewardType.BUDGET_EXCEEDED: -5.0,
    RewardType.MAX_ITERATIONS: -3.0,
    RewardType.ITERATION: 0.0,
    RewardType.SUB_CALL: -0.1,  # Small cost per sub-call
}


class RewardTracker:
    """Track rewards during RLM execution.
    
    Provides reward signals for reinforcement learning
    and performance monitoring.
    
    Example:
        >>> tracker = RewardTracker()
        >>> tracker.add(RewardType.CODE_EXECUTED)
        >>> tracker.add(RewardType.TASK_COMPLETE)
        >>> print(tracker.total_reward)
        11.0
    """
    
    def __init__(
        self,
        reward_values: Optional[Dict[RewardType, float]] = None,
        discount_factor: float = 0.99,
    ):
        """Initialize tracker.
        
        Args:
            reward_values: Custom reward values (overrides defaults)
            discount_factor: Discount for future rewards (gamma)
        """
        self.reward_values = {**DEFAULT_REWARDS}
        if reward_values:
            self.reward_values.update(reward_values)
        
        self.discount_factor = discount_factor
        self.signals: List[RewardSignal] = []
        self._current_iteration = 0
    
    def set_iteration(self, iteration: int) -> None:
        """Set current iteration number."""
        self._current_iteration = iteration
    
    def add(
        self,
        reward_type: RewardType,
        value: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> RewardSignal:
        """Add a reward signal.
        
        Args:
            reward_type: Type of reward
            value: Override default value
            metadata: Additional context
        
        Returns:
            The created signal
        """
        if value is None:
            value = self.reward_values.get(reward_type, 0.0)
        
        signal = RewardSignal(
            type=reward_type,
            value=value,
            iteration=self._current_iteration,
            metadata=metadata or {},
        )
        
        self.signals.append(signal)
        return signal
    
    @property
    def total_reward(self) -> float:
        """Sum of all rewards."""
        return sum(s.value for s in self.signals)
    
    @property
    def discounted_reward(self) -> float:
        """Discounted cumulative reward."""
        total = 0.0
        for i, signal in enumerate(self.signals):
            total += signal.value * (self.discount_factor ** i)
        return total
    
    def rewards_by_type(self) -> Dict[RewardType, float]:
        """Aggregate rewards by type."""
        result: Dict[RewardType, float] = {}
        for signal in self.signals:
            result[signal.type] = result.get(signal.type, 0.0) + signal.value
        return result
    
    def clear(self) -> None:
        """Clear all signals."""
        self.signals.clear()
        self._current_iteration = 0
    
    def summary(self) -> Dict[str, Any]:
        """Get reward summary."""
        return {
            "total_reward": self.total_reward,
            "discounted_reward": self.discounted_reward,
            "num_signals": len(self.signals),
            "by_type": {k.value: v for k, v in self.rewards_by_type().items()},
            "iterations": self._current_iteration,
        }
