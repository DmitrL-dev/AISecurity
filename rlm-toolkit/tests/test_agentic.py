"""Unit tests for agentic module."""

import pytest
from rlm_toolkit.agentic.rewards import RewardTracker, RewardSignal, RewardType
from rlm_toolkit.agentic.reasoning import ReasoningChain, ReasoningStep, StepType


class TestRewardTracker:
    """Tests for RewardTracker."""
    
    def test_add_reward(self):
        """Test adding a reward signal."""
        tracker = RewardTracker()
        signal = tracker.add(RewardType.CODE_EXECUTED)
        
        assert signal.type == RewardType.CODE_EXECUTED
        assert signal.value == 1.0  # Default value
    
    def test_total_reward(self):
        """Test total reward calculation."""
        tracker = RewardTracker()
        tracker.add(RewardType.CODE_EXECUTED)  # +1
        tracker.add(RewardType.TASK_COMPLETE)  # +10
        
        assert tracker.total_reward == 11.0
    
    def test_custom_value(self):
        """Test custom reward value."""
        tracker = RewardTracker()
        tracker.add(RewardType.CODE_EXECUTED, value=5.0)
        
        assert tracker.total_reward == 5.0
    
    def test_negative_rewards(self):
        """Test negative reward signals."""
        tracker = RewardTracker()
        tracker.add(RewardType.TASK_COMPLETE)  # +10
        tracker.add(RewardType.ERROR)  # -2
        
        assert tracker.total_reward == 8.0
    
    def test_rewards_by_type(self):
        """Test aggregation by type."""
        tracker = RewardTracker()
        tracker.add(RewardType.CODE_EXECUTED)
        tracker.add(RewardType.CODE_EXECUTED)
        tracker.add(RewardType.ERROR)
        
        by_type = tracker.rewards_by_type()
        assert by_type[RewardType.CODE_EXECUTED] == 2.0
        assert by_type[RewardType.ERROR] == -2.0
    
    def test_clear(self):
        """Test clearing tracker."""
        tracker = RewardTracker()
        tracker.add(RewardType.TASK_COMPLETE)
        tracker.clear()
        
        assert tracker.total_reward == 0.0
        assert len(tracker.signals) == 0
    
    def test_summary(self):
        """Test summary output."""
        tracker = RewardTracker()
        tracker.add(RewardType.CODE_EXECUTED)
        
        summary = tracker.summary()
        assert "total_reward" in summary
        assert "num_signals" in summary
    
    def test_iteration_tracking(self):
        """Test iteration number tracking."""
        tracker = RewardTracker()
        tracker.set_iteration(5)
        signal = tracker.add(RewardType.CODE_EXECUTED)
        
        assert signal.iteration == 5


class TestReasoningChain:
    """Tests for ReasoningChain."""
    
    def test_observe(self):
        """Test adding observation."""
        chain = ReasoningChain(goal="test")
        step = chain.observe("Found a fact")
        
        assert step.step_type == StepType.OBSERVATION
        assert step.content == "Found a fact"
    
    def test_hypothesize(self):
        """Test adding hypothesis."""
        chain = ReasoningChain()
        step = chain.hypothesize("Maybe X is true")
        
        assert step.step_type == StepType.HYPOTHESIS
    
    def test_conclude(self):
        """Test adding conclusion."""
        chain = ReasoningChain()
        chain.observe("fact")
        chain.conclude("therefore, answer")
        
        assert chain.conclusion == "therefore, answer"
    
    def test_chain_length(self):
        """Test chain grows correctly."""
        chain = ReasoningChain()
        chain.observe("o1")
        chain.observe("o2")
        chain.hypothesize("h1")
        chain.conclude("c1")
        
        assert len(chain.steps) == 4
    
    def test_average_confidence(self):
        """Test average confidence calculation."""
        chain = ReasoningChain()
        chain.add(StepType.OBSERVATION, "o1", confidence=0.8)
        chain.add(StepType.OBSERVATION, "o2", confidence=0.6)
        
        assert chain.average_confidence == 0.7
    
    def test_to_markdown(self):
        """Test markdown export."""
        chain = ReasoningChain(goal="test goal")
        chain.observe("saw something")
        chain.conclude("done")
        
        md = chain.to_markdown()
        assert "test goal" in md
        assert "Observation" in md
        assert "Conclusion" in md
    
    def test_evidence(self):
        """Test evidence list."""
        chain = ReasoningChain()
        step = chain.observe("fact", evidence=["source1", "source2"])
        
        assert len(step.evidence) == 2


class TestReasoningStep:
    """Tests for ReasoningStep."""
    
    def test_step_creation(self):
        """Test step creation."""
        step = ReasoningStep(
            step_type=StepType.OBSERVATION,
            content="test",
        )
        
        assert step.step_type == StepType.OBSERVATION
        assert step.content == "test"
        assert step.confidence == 1.0
    
    def test_to_dict(self):
        """Test dictionary export."""
        step = ReasoningStep(
            step_type=StepType.CONCLUSION,
            content="final answer",
            confidence=0.9,
        )
        
        d = step.to_dict()
        assert d["type"] == "conclusion"
        assert d["content"] == "final answer"
        assert d["confidence"] == 0.9


class TestRewardSignal:
    """Tests for RewardSignal."""
    
    def test_signal_creation(self):
        """Test signal creation."""
        signal = RewardSignal(
            type=RewardType.TASK_COMPLETE,
            value=10.0,
        )
        
        assert signal.type == RewardType.TASK_COMPLETE
        assert signal.value == 10.0
    
    def test_to_dict(self):
        """Test dictionary export."""
        signal = RewardSignal(
            type=RewardType.ERROR,
            value=-2.0,
            iteration=3,
        )
        
        d = signal.to_dict()
        assert d["type"] == "error"
        assert d["value"] == -2.0
        assert d["iteration"] == 3
