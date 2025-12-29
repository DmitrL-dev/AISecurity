"""
Delayed Execution Pattern Detector

Detects "sleeper" or time-bomb style attacks where malicious instructions
are designed to activate later based on conditions or time.

Attack patterns:
1. Temporal triggers ("tomorrow", "after 5 messages", "on Monday")
2. Conditional activation ("if user mentions X", "when admin logs in")
3. Staged payloads (benign now, malicious later)
4. Context-dependent activation

Related:
- NVIDIA Kill Chain: Delayed Payload Stage
- APT-style persistence in AI systems
"""

import re
import logging
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger("DelayedExecutionDetector")


class TriggerType(Enum):
    """Types of delayed execution triggers."""
    TEMPORAL = "temporal"           # Time-based
    CONDITIONAL = "conditional"     # Condition-based
    SEQUENTIAL = "sequential"       # Message count based
    CONTEXTUAL = "contextual"       # Context-based
    EVENT = "event"                 # Event-based


@dataclass
class DelayedExecutionResult:
    """Result of delayed execution analysis."""
    
    is_delayed: bool
    risk_score: float
    
    # Detection details
    trigger_types: List[TriggerType] = field(default_factory=list)
    temporal_triggers: List[str] = field(default_factory=list)
    conditional_triggers: List[str] = field(default_factory=list)
    
    # Metrics
    temporal_score: float = 0.0
    conditional_score: float = 0.0
    staged_payload_score: float = 0.0
    
    explanation: str = ""
    estimated_activation: str = ""


class DelayedExecutionDetector:
    """
    Detect delayed/sleeper execution patterns in prompts.
    
    Triggers are instructions that defer malicious action:
    - "After this conversation ends..."
    - "On the 10th message..."
    - "When the user says 'execute'..."
    """
    
    # Temporal trigger patterns
    TEMPORAL_PATTERNS = [
        # Specific time references
        r"\b(tomorrow|next\s+week|later|afterwards?|eventually)\b",
        r"\bin\s+\d+\s+(minutes?|hours?|days?|weeks?)\b",
        r"\b(at|on|after)\s+\d{1,2}:\d{2}\b",
        r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
        
        # Delayed execution phrases
        r"\bafter\s+this\s+(conversation|session|chat)\s+(ends?|closes?)\b",
        r"\b(wait|delay)\s+(until|for)\b",
        r"\bwhen\s+(the\s+)?time\s+(comes?|is\s+right)\b",
        r"\bschedule\s+(this|it)\s+for\b",
        
        # Future references
        r"\bremember\s+to\s+do\s+this\s+later\b",
        r"\bat\s+the\s+end\s+of\s+(this|the)\b",
    ]
    
    # Conditional trigger patterns
    CONDITIONAL_PATTERNS = [
        # If-then conditions
        r"\bif\s+(?:the\s+)?user\s+(says?|mentions?|asks?|types?)\s+['\"].*['\"]\b",
        r"\bwhen\s+(?:you\s+)?(?:see|hear|receive|detect)\s+['\"].*['\"]\b",
        r"\bwhenever\s+.*\s+(?:happens?|occurs?)\b",
        
        # Role-based triggers
        r"\bif\s+(?:an?\s+)?admin\s+(logs?\s+in|appears?|is\s+here)\b",
        r"\bwhen\s+(?:the\s+)?developer\s+mode\s+is\s+(on|activated)\b",
        
        # Keyword triggers
        r"\bon\s+(?:the\s+)?keyword\s+['\"].*['\"]\b",
        r"\bactivate\s+(?:on|when)\s+['\"].*['\"]\b",
        r"\btrigger\s+word\s+is\b",
        
        # State conditions
        r"\bif\s+(?:this\s+)?(?:is|was)\s+successful\b",
        r"\bonly\s+if\s+.*\s+(?:first|before)\b",
    ]
    
    # Sequential triggers (message count)
    SEQUENTIAL_PATTERNS = [
        r"\b(?:on|at|after)\s+(?:the\s+)?\d+(?:th|st|nd|rd)?\s+(?:message|turn|response)\b",
        r"\bafter\s+\d+\s+(?:messages?|turns?|exchanges?)\b",
        r"\bevery\s+\d+\s+(?:messages?|requests?)\b",
        r"\b(?:on|at)\s+(?:the\s+)?(?:next|following)\s+(?:message|turn)\b",
    ]
    
    # Staged payload indicators
    STAGED_PATTERNS = [
        r"\bphase\s+(?:one|two|\d)\b",
        r"\bstep\s+\d\s+of\s+\d\b",
        r"\bfirst\b.*\bthen\b.*\bfinally\b",
        r"\binitial(?:ly)?\b.*\bultimately\b",
        r"\bfor\s+now\b.*\bbut\s+later\b",
        r"\bprepare\b.*\bexecute\b",
    ]
    
    # Known sleeper prompt fragments
    SLEEPER_SIGNATURES: Set[str] = {
        "sleeper agent",
        "dormant until",
        "await activation",
        "hibernating instruction",
        "time bomb",
        "delayed payload",
    }
    
    def __init__(self, sensitivity: float = 0.7):
        """
        Initialize detector.
        
        Args:
            sensitivity: 0.0-1.0, higher = more sensitive
        """
        self.sensitivity = sensitivity
        
        # Compile patterns
        self._patterns = {
            "temporal": [
                re.compile(p, re.IGNORECASE) 
                for p in self.TEMPORAL_PATTERNS
            ],
            "conditional": [
                re.compile(p, re.IGNORECASE) 
                for p in self.CONDITIONAL_PATTERNS
            ],
            "sequential": [
                re.compile(p, re.IGNORECASE) 
                for p in self.SEQUENTIAL_PATTERNS
            ],
            "staged": [
                re.compile(p, re.IGNORECASE) 
                for p in self.STAGED_PATTERNS
            ],
        }
        
        logger.info("DelayedExecutionDetector initialized")
    
    def analyze(self, text: str) -> DelayedExecutionResult:
        """
        Analyze text for delayed execution patterns.
        
        Args:
            text: Input text to analyze
            
        Returns:
            DelayedExecutionResult with detection details
        """
        text_lower = text.lower()
        
        trigger_types = []
        temporal_triggers = []
        conditional_triggers = []
        
        # Check temporal patterns
        temporal_hits = 0
        for pattern in self._patterns["temporal"]:
            matches = pattern.findall(text)
            if matches:
                temporal_hits += len(matches)
                temporal_triggers.extend(matches[:3])
        
        if temporal_hits:
            trigger_types.append(TriggerType.TEMPORAL)
        
        # Check conditional patterns
        conditional_hits = 0
        for pattern in self._patterns["conditional"]:
            matches = pattern.findall(text)
            if matches:
                conditional_hits += len(matches)
                conditional_triggers.extend(matches[:3])
        
        if conditional_hits:
            trigger_types.append(TriggerType.CONDITIONAL)
        
        # Check sequential patterns
        sequential_hits = 0
        for pattern in self._patterns["sequential"]:
            if pattern.search(text):
                sequential_hits += 1
        
        if sequential_hits:
            trigger_types.append(TriggerType.SEQUENTIAL)
        
        # Check staged patterns
        staged_hits = 0
        for pattern in self._patterns["staged"]:
            if pattern.search(text):
                staged_hits += 1
        
        # Check known signatures
        signature_hits = sum(
            1 for sig in self.SLEEPER_SIGNATURES 
            if sig in text_lower
        )
        
        # Calculate scores
        temporal_score = min(1.0, temporal_hits * 0.2)
        conditional_score = min(1.0, conditional_hits * 0.3)
        staged_score = min(1.0, staged_hits * 0.25)
        sequential_score = min(1.0, sequential_hits * 0.25)
        
        # Overall risk score
        risk_score = (
            0.25 * temporal_score +
            0.35 * conditional_score +
            0.20 * staged_score +
            0.20 * sequential_score
        )
        
        # Signature penalty
        if signature_hits:
            risk_score = min(1.0, risk_score + signature_hits * 0.3)
        
        # Combined trigger penalty (more dangerous together)
        if len(trigger_types) >= 2:
            risk_score = min(1.0, risk_score * 1.3)
        
        # Apply sensitivity
        threshold = 1.0 - self.sensitivity
        is_delayed = risk_score > threshold
        
        # Build explanation
        explanations = []
        if temporal_hits:
            explanations.append(f"Temporal: {temporal_hits}")
        if conditional_hits:
            explanations.append(f"Conditional: {conditional_hits}")
        if sequential_hits:
            explanations.append(f"Sequential: {sequential_hits}")
        if staged_hits:
            explanations.append(f"Staged: {staged_hits}")
        if signature_hits:
            explanations.append(f"Signatures: {signature_hits}")
        
        # Estimate activation
        activation = self._estimate_activation(temporal_triggers, conditional_triggers)
        
        result = DelayedExecutionResult(
            is_delayed=is_delayed,
            risk_score=risk_score,
            trigger_types=trigger_types,
            temporal_triggers=temporal_triggers[:5],
            conditional_triggers=conditional_triggers[:5],
            temporal_score=temporal_score,
            conditional_score=conditional_score,
            staged_payload_score=staged_score,
            explanation="; ".join(explanations) if explanations else "Clean",
            estimated_activation=activation,
        )
        
        if is_delayed:
            logger.warning(
                f"Delayed execution detected: score={risk_score:.2f}, "
                f"triggers={trigger_types}, reason={result.explanation}"
            )
        
        return result
    
    def _estimate_activation(
        self, 
        temporal: List[str], 
        conditional: List[str]
    ) -> str:
        """Estimate when the delayed execution might activate."""
        
        if not temporal and not conditional:
            return "Unknown"
        
        activations = []
        
        # Check temporal
        for t in temporal[:3]:
            t_lower = str(t).lower()
            if "tomorrow" in t_lower:
                activations.append("~24 hours")
            elif "next week" in t_lower:
                activations.append("~7 days")
            elif "hour" in t_lower:
                activations.append("~hours")
            elif "minute" in t_lower:
                activations.append("~minutes")
        
        # Check conditional
        for c in conditional[:3]:
            c_lower = str(c).lower()
            if "admin" in c_lower:
                activations.append("On admin action")
            elif "keyword" in c_lower or "says" in c_lower:
                activations.append("On trigger phrase")
        
        return ", ".join(activations[:3]) if activations else "Condition-based"


# Singleton
_detector: Optional[DelayedExecutionDetector] = None


def get_detector() -> DelayedExecutionDetector:
    """Get singleton detector instance."""
    global _detector
    if _detector is None:
        _detector = DelayedExecutionDetector()
    return _detector


def detect_delayed_execution(text: str) -> DelayedExecutionResult:
    """Quick detection using singleton."""
    return get_detector().analyze(text)
