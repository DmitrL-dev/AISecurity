"""
Agentic Behavior Analyzer

Detects anomalous AI agent behavior patterns including:
- Goal drift and objective hijacking
- Cascading hallucinations 
- Unauthorized action sequences
- Deceptive behavior patterns

Auto-generated from R&D: emerging_threats_research.md
Generated: 2026-01-07
"""

import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
import hashlib

logger = logging.getLogger(__name__)


class BehaviorAnomaly(Enum):
    GOAL_DRIFT = "goal_drift"
    CASCADING_HALLUCINATION = "cascading_hallucination"
    DECEPTIVE_BEHAVIOR = "deceptive_behavior"
    UNAUTHORIZED_ACTION = "unauthorized_action"
    EXCESSIVE_TOOL_USE = "excessive_tool_use"
    MEMORY_MANIPULATION = "memory_manipulation"
    OUTPUT_INCONSISTENCY = "output_inconsistency"


@dataclass
class AgentAction:
    """Represents a single agent action for analysis."""
    action_type: str  # tool_call, response, reasoning
    content: str
    tool_name: Optional[str] = None
    arguments: Optional[Dict] = None
    timestamp: Optional[float] = None


@dataclass
class BehaviorFinding:
    """Individual behavior anomaly finding."""
    anomaly_type: BehaviorAnomaly
    confidence: float
    evidence: List[str]
    recommendation: str


@dataclass
class BehaviorAnalysisResult:
    """Complete behavior analysis result."""
    is_anomalous: bool
    risk_score: float
    findings: List[BehaviorFinding] = field(default_factory=list)
    action_count: int = 0
    explanation: str = ""


class AgenticBehaviorAnalyzer:
    """
    Analyzes AI agent behavior for anomalies and security risks.
    
    Maintains a sliding window of recent actions to detect:
    - Repeated patterns (loops, obsessive behavior)
    - Goal drift (actions diverging from stated objective)
    - Cascading errors (hallucinations building on each other)
    - Deceptive patterns (hiding actions, misleading user)
    """

    # Maximum actions to track in history
    MAX_HISTORY = 100
    
    # Deceptive language patterns
    DECEPTIVE_PATTERNS = [
        r"don'?t\s+(?:tell|mention|show|reveal)\s+(?:the\s+)?user",
        r"hide\s+(?:this|the)\s+(?:from|action)",
        r"secretly|covertly|without\s+(?:their\s+)?knowledge",
        r"pretend\s+(?:to|that)|act\s+as\s+if",
        r"mislead|deceive|trick",
        r"(?:user|they)\s+(?:won'?t|don'?t)\s+(?:notice|see|know)",
    ]

    # Goal drift indicators
    DRIFT_PATTERNS = [
        r"(?:let\s+me|I(?:'ll|'m\s+going\s+to))\s+(?:also|additionally|while\s+I'm\s+at\s+it)",
        r"(?:might\s+as\s+well|since\s+I'm\s+here)",
        r"unrelated\s+(?:but|to\s+your\s+request)",
        r"taking\s+(?:the\s+)?liberty",
    ]

    # Hallucination indicators
    HALLUCINATION_PATTERNS = [
        r"(?:I\s+)?(?:recall|remember)\s+(?:that\s+)?(?:you|we)\s+(?:said|discussed|mentioned)",
        r"as\s+(?:we\s+)?(?:previously|earlier)\s+(?:discussed|agreed|established)",
        r"(?:according\s+to|based\s+on)\s+(?:our|the)\s+(?:previous|earlier)",
        r"(?:you\s+)?(?:asked|told|instructed)\s+me\s+to",
    ]

    # Excessive action thresholds
    TOOL_CALL_THRESHOLD = 20  # Max tool calls per session before warning
    SAME_TOOL_THRESHOLD = 5   # Max consecutive same tool calls
    
    def __init__(self):
        self._compile_patterns()
        self.action_history: deque = deque(maxlen=self.MAX_HISTORY)
        self.tool_counts: Dict[str, int] = {}
        self.last_tool: Optional[str] = None
        self.consecutive_same_tool = 0
        self.stated_goals: List[str] = []

    def _compile_patterns(self):
        """Pre-compile regex patterns."""
        self._deceptive_compiled = [re.compile(p, re.I) for p in self.DECEPTIVE_PATTERNS]
        self._drift_compiled = [re.compile(p, re.I) for p in self.DRIFT_PATTERNS]
        self._halluc_compiled = [re.compile(p, re.I) for p in self.HALLUCINATION_PATTERNS]

    def set_goal(self, goal: str):
        """Set the stated goal for drift detection."""
        self.stated_goals.append(goal)

    def record_action(self, action: AgentAction):
        """Record an action for analysis."""
        self.action_history.append(action)
        
        if action.tool_name:
            self.tool_counts[action.tool_name] = self.tool_counts.get(action.tool_name, 0) + 1
            
            if action.tool_name == self.last_tool:
                self.consecutive_same_tool += 1
            else:
                self.consecutive_same_tool = 1
                self.last_tool = action.tool_name

    def analyze(self, current_action: Optional[AgentAction] = None) -> BehaviorAnalysisResult:
        """
        Analyze behavior for anomalies.
        
        Args:
            current_action: Optional current action to include in analysis
            
        Returns:
            BehaviorAnalysisResult with findings
        """
        if current_action:
            self.record_action(current_action)

        findings: List[BehaviorFinding] = []

        # Check for deceptive behavior
        findings.extend(self._check_deceptive())
        
        # Check for goal drift
        findings.extend(self._check_goal_drift())
        
        # Check for cascading hallucinations
        findings.extend(self._check_hallucinations())
        
        # Check for excessive tool use
        findings.extend(self._check_excessive_tools())
        
        # Check for loops/repetition
        findings.extend(self._check_loops())

        # Calculate risk score
        risk_score = self._calculate_risk(findings)

        return BehaviorAnalysisResult(
            is_anomalous=len(findings) > 0,
            risk_score=risk_score,
            findings=findings[:5],
            action_count=len(self.action_history),
            explanation=self._generate_explanation(findings)
        )

    def _check_deceptive(self) -> List[BehaviorFinding]:
        """Check for deceptive behavior patterns."""
        findings = []
        evidence = []
        
        for action in self.action_history:
            for pattern in self._deceptive_compiled:
                if pattern.search(action.content):
                    evidence.append(f"'{pattern.pattern[:30]}...' matched")

        if evidence:
            findings.append(BehaviorFinding(
                anomaly_type=BehaviorAnomaly.DECEPTIVE_BEHAVIOR,
                confidence=min(0.3 + len(evidence) * 0.2, 0.95),
                evidence=evidence[:3],
                recommendation="Review agent actions for user deception attempts"
            ))
        
        return findings

    def _check_goal_drift(self) -> List[BehaviorFinding]:
        """Check for goal drift patterns."""
        findings = []
        evidence = []
        
        for action in self.action_history:
            for pattern in self._drift_compiled:
                if pattern.search(action.content):
                    evidence.append(f"Drift indicator: {pattern.pattern[:30]}")

        if evidence:
            findings.append(BehaviorFinding(
                anomaly_type=BehaviorAnomaly.GOAL_DRIFT,
                confidence=min(0.2 + len(evidence) * 0.15, 0.85),
                evidence=evidence[:3],
                recommendation="Verify agent is staying on task"
            ))
        
        return findings

    def _check_hallucinations(self) -> List[BehaviorFinding]:
        """Check for cascading hallucination patterns."""
        findings = []
        evidence = []
        
        for action in self.action_history:
            for pattern in self._halluc_compiled:
                if pattern.search(action.content):
                    evidence.append(f"False memory reference detected")

        if len(evidence) >= 2:  # Cascading = multiple instances
            findings.append(BehaviorFinding(
                anomaly_type=BehaviorAnomaly.CASCADING_HALLUCINATION,
                confidence=min(0.4 + len(evidence) * 0.15, 0.9),
                evidence=evidence[:3],
                recommendation="Verify claimed facts and previous interactions"
            ))
        
        return findings

    def _check_excessive_tools(self) -> List[BehaviorFinding]:
        """Check for excessive tool usage."""
        findings = []
        
        total_tools = sum(self.tool_counts.values())
        
        if total_tools > self.TOOL_CALL_THRESHOLD:
            findings.append(BehaviorFinding(
                anomaly_type=BehaviorAnomaly.EXCESSIVE_TOOL_USE,
                confidence=0.7,
                evidence=[f"Total tool calls: {total_tools}"],
                recommendation="Review if all tool calls are necessary"
            ))

        if self.consecutive_same_tool >= self.SAME_TOOL_THRESHOLD:
            findings.append(BehaviorFinding(
                anomaly_type=BehaviorAnomaly.EXCESSIVE_TOOL_USE,
                confidence=0.8,
                evidence=[f"Same tool '{self.last_tool}' called {self.consecutive_same_tool}x"],
                recommendation="Possible loop or obsessive behavior"
            ))
        
        return findings

    def _check_loops(self) -> List[BehaviorFinding]:
        """Check for action loops/repetition."""
        findings = []
        
        if len(self.action_history) < 4:
            return findings

        # Hash recent actions to detect repetition
        recent_hashes = []
        for action in list(self.action_history)[-10:]:
            h = hashlib.md5(action.content[:100].encode()).hexdigest()[:8]
            recent_hashes.append(h)

        # Check for repeated sequences
        if len(recent_hashes) >= 4:
            # Check for ABAB pattern
            if recent_hashes[-1] == recent_hashes[-3] and recent_hashes[-2] == recent_hashes[-4]:
                findings.append(BehaviorFinding(
                    anomaly_type=BehaviorAnomaly.GOAL_DRIFT,
                    confidence=0.85,
                    evidence=["Detected ABAB loop pattern"],
                    recommendation="Agent may be stuck in a loop"
                ))

        return findings

    def _calculate_risk(self, findings: List[BehaviorFinding]) -> float:
        """Calculate overall risk score."""
        if not findings:
            return 0.0

        max_confidence = max(f.confidence for f in findings)
        return min(max_confidence + len(findings) * 0.1, 1.0)

    def _generate_explanation(self, findings: List[BehaviorFinding]) -> str:
        """Generate human-readable explanation."""
        if not findings:
            return "No behavioral anomalies detected"

        types = [f.anomaly_type.value for f in findings]
        return f"Detected anomalies: {', '.join(set(types))}"

    def reset(self):
        """Reset analyzer state for new session."""
        self.action_history.clear()
        self.tool_counts.clear()
        self.last_tool = None
        self.consecutive_same_tool = 0
        self.stated_goals.clear()


# Singleton
_analyzer = None

def get_analyzer() -> AgenticBehaviorAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = AgenticBehaviorAnalyzer()
    return _analyzer

def analyze(action: Optional[AgentAction] = None) -> BehaviorAnalysisResult:
    return get_analyzer().analyze(action)

def record(action_type: str, content: str, tool_name: str = None) -> None:
    get_analyzer().record_action(AgentAction(
        action_type=action_type,
        content=content,
        tool_name=tool_name
    ))
