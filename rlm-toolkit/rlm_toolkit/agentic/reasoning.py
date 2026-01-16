"""
Structured Reasoning
====================

Chain-of-thought and structured reasoning for complex tasks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from rlm_toolkit.providers.base import LLMProvider


class StepType(Enum):
    """Types of reasoning steps."""
    
    OBSERVATION = "observation"     # Observed fact from context
    HYPOTHESIS = "hypothesis"       # Proposed explanation
    VERIFICATION = "verification"   # Tested hypothesis
    CONCLUSION = "conclusion"       # Final conclusion
    ACTION = "action"               # Action taken (code execution)
    ERROR = "error"                 # Error or contradiction


@dataclass
class ReasoningStep:
    """Single step in reasoning chain.
    
    Attributes:
        step_type: Type of reasoning step
        content: The reasoning content
        evidence: Supporting evidence
        confidence: Confidence score (0-1)
        timestamp: When step was created
        metadata: Additional data
    """
    step_type: StepType
    content: str
    evidence: List[str] = field(default_factory=list)
    confidence: float = 1.0
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.step_type.value,
            "content": self.content,
            "evidence": self.evidence,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


class ReasoningChain:
    """Chain of reasoning steps.
    
    Maintains a structured record of the reasoning process.
    
    Example:
        >>> chain = ReasoningChain()
        >>> chain.observe("Document mentions revenue of $2.5B")
        >>> chain.hypothesize("Q4 was successful financially")
        >>> chain.conclude("Q4 showed strong financial performance")
    """
    
    def __init__(self, goal: str = ""):
        """Initialize chain.
        
        Args:
            goal: The reasoning goal
        """
        self.goal = goal
        self.steps: List[ReasoningStep] = []
        self._start_time = datetime.now()
    
    def add(
        self,
        step_type: StepType,
        content: str,
        evidence: Optional[List[str]] = None,
        confidence: float = 1.0,
        **metadata
    ) -> ReasoningStep:
        """Add a reasoning step."""
        step = ReasoningStep(
            step_type=step_type,
            content=content,
            evidence=evidence or [],
            confidence=confidence,
            metadata=metadata,
        )
        self.steps.append(step)
        return step
    
    def observe(self, content: str, **kwargs) -> ReasoningStep:
        """Add an observation."""
        return self.add(StepType.OBSERVATION, content, **kwargs)
    
    def hypothesize(self, content: str, **kwargs) -> ReasoningStep:
        """Add a hypothesis."""
        return self.add(StepType.HYPOTHESIS, content, **kwargs)
    
    def verify(self, content: str, **kwargs) -> ReasoningStep:
        """Add a verification step."""
        return self.add(StepType.VERIFICATION, content, **kwargs)
    
    def conclude(self, content: str, **kwargs) -> ReasoningStep:
        """Add a conclusion."""
        return self.add(StepType.CONCLUSION, content, **kwargs)
    
    def act(self, content: str, **kwargs) -> ReasoningStep:
        """Add an action step."""
        return self.add(StepType.ACTION, content, **kwargs)
    
    def error(self, content: str, **kwargs) -> ReasoningStep:
        """Add an error step."""
        return self.add(StepType.ERROR, content, **kwargs)
    
    @property
    def conclusion(self) -> Optional[str]:
        """Get final conclusion if any."""
        conclusions = [s for s in self.steps if s.step_type == StepType.CONCLUSION]
        return conclusions[-1].content if conclusions else None
    
    @property
    def average_confidence(self) -> float:
        """Average confidence across steps."""
        if not self.steps:
            return 0.0
        return sum(s.confidence for s in self.steps) / len(self.steps)
    
    def to_markdown(self) -> str:
        """Export chain as markdown."""
        lines = [f"# Reasoning Chain: {self.goal}", ""]
        
        for i, step in enumerate(self.steps, 1):
            icon = {
                StepType.OBSERVATION: "👁️",
                StepType.HYPOTHESIS: "💡",
                StepType.VERIFICATION: "✓",
                StepType.CONCLUSION: "✅",
                StepType.ACTION: "⚡",
                StepType.ERROR: "❌",
            }.get(step.step_type, "•")
            
            lines.append(f"{i}. {icon} **{step.step_type.value.title()}**: {step.content}")
            if step.evidence:
                for e in step.evidence:
                    lines.append(f"   - Evidence: {e}")
            lines.append(f"   - Confidence: {step.confidence:.0%}")
            lines.append("")
        
        return "\n".join(lines)


class StructuredReasoner:
    """Structured reasoning engine.
    
    Uses LLM to perform structured reasoning with explicit steps.
    
    Example:
        >>> reasoner = StructuredReasoner(provider)
        >>> chain = reasoner.reason(context, query)
        >>> print(chain.conclusion)
    """
    
    SYSTEM_PROMPT = """You are a structured reasoner. Break down your thinking into explicit steps.

For each step, use one of these formats:
- OBSERVE: [what you notice in the context]
- HYPOTHESIZE: [your proposed explanation/answer]
- VERIFY: [how you check your hypothesis]
- CONCLUDE: [your final answer]

Be explicit about your reasoning. Show your work."""
    
    def __init__(
        self,
        provider: "LLMProvider",
        max_steps: int = 10,
    ):
        """Initialize reasoner.
        
        Args:
            provider: LLM provider
            max_steps: Maximum reasoning steps
        """
        self.provider = provider
        self.max_steps = max_steps
    
    def reason(
        self,
        context: str,
        query: str,
        chain: Optional[ReasoningChain] = None,
    ) -> ReasoningChain:
        """Perform structured reasoning.
        
        Args:
            context: Input context
            query: Question to answer
            chain: Existing chain to continue
        
        Returns:
            ReasoningChain with all steps
        """
        if chain is None:
            chain = ReasoningChain(goal=query)
        
        prompt = f"""Context:
{context[:5000]}

Question: {query}

Reason through this step by step using OBSERVE, HYPOTHESIZE, VERIFY, CONCLUDE formats."""
        
        response = self.provider.generate(
            prompt=prompt,
            system_prompt=self.SYSTEM_PROMPT,
        )
        
        # Parse response into steps
        self._parse_response(response.content, chain)
        
        return chain
    
    def _parse_response(self, response: str, chain: ReasoningChain) -> None:
        """Parse LLM response into reasoning steps."""
        lines = response.split("\n")
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            line_upper = line.upper()
            
            if line_upper.startswith("OBSERVE:"):
                chain.observe(line[8:].strip())
            elif line_upper.startswith("HYPOTHESIZE:"):
                chain.hypothesize(line[12:].strip())
            elif line_upper.startswith("VERIFY:"):
                chain.verify(line[7:].strip())
            elif line_upper.startswith("CONCLUDE:"):
                chain.conclude(line[9:].strip())
            elif line_upper.startswith("ACTION:"):
                chain.act(line[7:].strip())
            elif line_upper.startswith("ERROR:"):
                chain.error(line[6:].strip())
