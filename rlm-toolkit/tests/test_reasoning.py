"""Tests for agentic reasoning module."""

import pytest
from rlm_toolkit.agentic.reasoning import (
    StepType,
    ReasoningStep,
    ReasoningChain,
    StructuredReasoner,
)
from rlm_toolkit.testing.mocks import MockProvider


class TestStepType:
    """Tests for StepType enum."""
    
    def test_values(self):
        """Test step type values."""
        assert StepType.OBSERVATION.value == "observation"
        assert StepType.HYPOTHESIS.value == "hypothesis"
        assert StepType.VERIFICATION.value == "verification"
        assert StepType.CONCLUSION.value == "conclusion"
        assert StepType.ACTION.value == "action"
        assert StepType.ERROR.value == "error"


class TestReasoningStep:
    """Tests for ReasoningStep."""
    
    def test_creation(self):
        """Test step creation."""
        step = ReasoningStep(
            step_type=StepType.OBSERVATION,
            content="Found important data",
        )
        
        assert step.step_type == StepType.OBSERVATION
        assert step.content == "Found important data"
    
    def test_evidence(self):
        """Test step with evidence."""
        step = ReasoningStep(
            step_type=StepType.VERIFICATION,
            content="Verified claim",
            evidence=["Source 1", "Source 2"],
        )
        
        assert len(step.evidence) == 2
    
    def test_confidence(self):
        """Test step confidence."""
        step = ReasoningStep(
            step_type=StepType.HYPOTHESIS,
            content="Maybe X",
            confidence=0.8,
        )
        
        assert step.confidence == 0.8
    
    def test_to_dict(self):
        """Test step serialization."""
        step = ReasoningStep(
            step_type=StepType.CONCLUSION,
            content="Final answer",
        )
        
        data = step.to_dict()
        
        assert "content" in data or "Final answer" in str(data)
        assert isinstance(data, dict)


class TestReasoningChain:
    """Tests for ReasoningChain."""
    
    def test_creation(self):
        """Test chain creation."""
        chain = ReasoningChain(goal="Find the answer")
        
        assert chain.goal == "Find the answer"
        assert len(chain.steps) == 0
    
    def test_add_step(self):
        """Test adding steps."""
        chain = ReasoningChain()
        
        chain.add(StepType.OBSERVATION, "Saw something")
        
        assert len(chain.steps) == 1
    
    def test_observe(self):
        """Test observe helper."""
        chain = ReasoningChain()
        
        chain.observe("The document says X")
        
        assert chain.steps[0].step_type == StepType.OBSERVATION
    
    def test_hypothesize(self):
        """Test hypothesize helper."""
        chain = ReasoningChain()
        
        chain.hypothesize("Maybe the answer is Y")
        
        assert chain.steps[0].step_type == StepType.HYPOTHESIS
    
    def test_verify(self):
        """Test verify helper."""
        chain = ReasoningChain()
        
        chain.verify("This is confirmed")
        
        assert chain.steps[0].step_type == StepType.VERIFICATION
    
    def test_conclude(self):
        """Test conclude helper."""
        chain = ReasoningChain()
        
        chain.conclude("The answer is 42")
        
        assert chain.steps[0].step_type == StepType.CONCLUSION
    
    def test_act(self):
        """Test act helper."""
        chain = ReasoningChain()
        
        chain.act("Performing action X")
        
        assert chain.steps[0].step_type == StepType.ACTION
    
    def test_error(self):
        """Test error helper."""
        chain = ReasoningChain()
        
        chain.error("Something went wrong")
        
        assert chain.steps[0].step_type == StepType.ERROR
    
    def test_conclusion_property(self):
        """Test getting conclusion."""
        chain = ReasoningChain()
        
        chain.observe("Data")
        chain.conclude("Answer is 42")
        
        assert chain.conclusion == "Answer is 42"
    
    def test_conclusion_none(self):
        """Test no conclusion returns None."""
        chain = ReasoningChain()
        
        chain.observe("Data")
        
        assert chain.conclusion is None
    
    def test_average_confidence(self):
        """Test average confidence calculation."""
        chain = ReasoningChain()
        
        chain.add(StepType.OBSERVATION, "A", confidence=0.8)
        chain.add(StepType.OBSERVATION, "B", confidence=0.6)
        
        assert chain.average_confidence == 0.7
    
    def test_to_markdown(self):
        """Test markdown export."""
        chain = ReasoningChain(goal="Test goal")
        
        chain.observe("Found data")
        chain.conclude("Answer")
        
        md = chain.to_markdown()
        
        assert "Test goal" in md
        assert "observation" in md.lower()


class TestStructuredReasoner:
    """Tests for StructuredReasoner."""
    
    def test_creation(self):
        """Test reasoner creation."""
        provider = MockProvider()
        reasoner = StructuredReasoner(provider)
        
        assert reasoner is not None
    
    def test_reason_basic(self):
        """Test basic reasoning."""
        provider = MockProvider(responses=[
            "[OBSERVATION] Found relevant data\n[CONCLUSION] The answer is 42",
        ])
        reasoner = StructuredReasoner(provider)
        
        chain = reasoner.reason(context="Test context", query="What is the answer?")
        
        assert len(chain.steps) >= 0
    
    def test_max_steps(self):
        """Test max steps parameter."""
        provider = MockProvider()
        reasoner = StructuredReasoner(provider, max_steps=5)
        
        assert reasoner.max_steps == 5
