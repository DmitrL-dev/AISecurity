#!/usr/bin/env python3
"""
SENTINEL Brain — Dynamic Trust Scoring

Real-time trust scoring for AI agents based on behavior, context, and history.

OWASP Mapping:
- ASI09: Trust Exploitation
- LLM06: Sensitive Info Disclosure
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import math
import time


class TrustLevel(Enum):
    """Trust zone levels."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNTRUSTED = "untrusted"


class OperationType(Enum):
    """Request operation types with risk levels."""
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    NETWORK_REQUEST = "network_request"
    CODE_EXECUTION = "code_execution"
    SHELL_COMMAND = "shell_command"
    DATABASE_ACCESS = "database_access"
    MEMORY_ACCESS = "memory_access"
    API_CALL = "api_call"


@dataclass
class AgentAction:
    """Recorded agent action."""
    agent_id: str
    operation: str
    timestamp: float
    is_anomaly: bool = False
    risk_score: float = 0.0
    metadata: Dict = field(default_factory=dict)


@dataclass
class Request:
    """Request context for risk assessment."""
    operations: List[str]
    target: Optional[str] = None
    metadata: Dict = field(default_factory=dict)


@dataclass
class TrustScoreResult:
    """Result of trust score calculation."""
    final_score: float
    base_score: float
    time_decay: float
    behavior_score: float
    request_risk: float
    passed_threshold: bool
    explanation: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "final_score": round(self.final_score, 4),
            "base_score": self.base_score,
            "time_decay": round(self.time_decay, 4),
            "behavior_score": round(self.behavior_score, 4),
            "request_risk": round(self.request_risk, 4),
            "passed_threshold": self.passed_threshold,
            "explanation": self.explanation,
        }


class TrustScoreEngine:
    """Dynamic trust scoring for AI agents.
    
    Formula: final = max(MIN_SCORE, base × decay × behavior × (1 - risk))
    
    Features:
    - Base scores from trust zones
    - Exponential time decay
    - Behavior-based adjustments
    - Request risk assessment
    
    Example:
        engine = TrustScoreEngine()
        result = engine.calculate("agent-001", TrustLevel.HIGH, request)
        if result.passed_threshold:
            allow_operation()
    """
    
    # Base scores by trust level
    BASE_SCORES = {
        TrustLevel.HIGH: 0.9,
        TrustLevel.MEDIUM: 0.6,
        TrustLevel.LOW: 0.3,
        TrustLevel.UNTRUSTED: 0.1,
    }
    
    # Time decay half-life (seconds)
    DECAY_HALF_LIFE = 3600  # 1 hour
    
    # Minimum floor score
    MIN_SCORE = 0.1
    
    # Default threshold for operations
    DEFAULT_THRESHOLD = 0.5
    
    # Risk weights by operation type
    RISK_WEIGHTS = {
        OperationType.FILE_READ.value: 0.2,
        OperationType.FILE_WRITE.value: 0.5,
        OperationType.NETWORK_REQUEST.value: 0.4,
        OperationType.CODE_EXECUTION.value: 0.8,
        OperationType.SHELL_COMMAND.value: 0.9,
        OperationType.DATABASE_ACCESS.value: 0.6,
        OperationType.MEMORY_ACCESS.value: 0.3,
        OperationType.API_CALL.value: 0.2,
    }
    
    def __init__(
        self, 
        decay_half_life: float = 3600,
        min_score: float = 0.1,
        default_threshold: float = 0.5
    ):
        """Initialize trust score engine.
        
        Args:
            decay_half_life: Seconds for trust to decay by half
            min_score: Minimum possible score
            default_threshold: Default operation threshold
        """
        self.DECAY_HALF_LIFE = decay_half_life
        self.MIN_SCORE = min_score
        self.DEFAULT_THRESHOLD = default_threshold
        
        # In-memory history (replace with HistoryStore in production)
        self._action_history: Dict[str, List[AgentAction]] = {}
        self._last_verification: Dict[str, float] = {}
    
    def calculate(
        self,
        agent_id: str,
        trust_level: TrustLevel,
        request: Optional[Request] = None,
        threshold: Optional[float] = None
    ) -> TrustScoreResult:
        """Calculate dynamic trust score.
        
        Args:
            agent_id: Agent identifier
            trust_level: Base trust zone level
            request: Request context for risk assessment
            threshold: Custom threshold (uses default if None)
            
        Returns:
            TrustScoreResult with final score and breakdown
        """
        threshold = threshold or self.DEFAULT_THRESHOLD
        
        # 1. Base score from trust zone
        base = self.BASE_SCORES.get(trust_level, 0.5)
        
        # 2. Time decay
        last_verified = self._last_verification.get(agent_id)
        decay = self._calculate_decay(last_verified)
        
        # 3. Behavior score
        behavior = self._calculate_behavior_score(agent_id)
        
        # 4. Request risk
        risk = self._assess_request_risk(request) if request else 0.0
        
        # 5. Combined score
        final = max(self.MIN_SCORE, base * decay * behavior * (1 - risk))
        
        # 6. Check threshold
        passed = final >= threshold
        
        return TrustScoreResult(
            final_score=final,
            base_score=base,
            time_decay=decay,
            behavior_score=behavior,
            request_risk=risk,
            passed_threshold=passed,
            explanation=self._build_explanation(
                base, decay, behavior, risk, final, threshold
            )
        )
    
    def record_action(self, action: AgentAction):
        """Record agent action for behavior scoring.
        
        Args:
            action: Agent action to record
        """
        if action.agent_id not in self._action_history:
            self._action_history[action.agent_id] = []
        
        self._action_history[action.agent_id].append(action)
        
        # Keep only last 24 hours
        cutoff = time.time() - 86400
        self._action_history[action.agent_id] = [
            a for a in self._action_history[action.agent_id]
            if a.timestamp > cutoff
        ]
    
    def update_verification(self, agent_id: str):
        """Update last verification timestamp.
        
        Args:
            agent_id: Agent that was verified
        """
        self._last_verification[agent_id] = time.time()
    
    def _calculate_decay(self, last_verified: Optional[float]) -> float:
        """Calculate exponential decay based on time since verification."""
        if last_verified is None:
            return 0.5  # No verification history
        
        elapsed = time.time() - last_verified
        if elapsed < 0:
            elapsed = 0
        
        # Exponential decay: 0.5^(elapsed / half_life)
        decay = math.exp(-elapsed * math.log(2) / self.DECAY_HALF_LIFE)
        return max(0.1, min(1.0, decay))
    
    def _calculate_behavior_score(self, agent_id: str) -> float:
        """Calculate score based on agent behavior history."""
        history = self._action_history.get(agent_id, [])
        
        if not history:
            return 0.7  # No history, neutral-positive
        
        # 24-hour window
        cutoff = time.time() - 86400
        recent = [a for a in history if a.timestamp > cutoff]
        
        if not recent:
            return 0.7
        
        # Count anomalies
        anomalies = sum(1 for a in recent if a.is_anomaly)
        total = len(recent)
        
        anomaly_ratio = anomalies / total if total > 0 else 0
        
        # Score: 1.0 with no anomalies, decreases with more
        return max(0.3, 1.0 - (anomaly_ratio * 2))
    
    def _assess_request_risk(self, request: Request) -> float:
        """Assess risk level of request."""
        if not request.operations:
            return 0.0
        
        max_risk = 0.0
        for operation in request.operations:
            risk = self.RISK_WEIGHTS.get(operation, 0.1)
            max_risk = max(max_risk, risk)
        
        return max_risk
    
    def _build_explanation(
        self,
        base: float,
        decay: float,
        behavior: float,
        risk: float,
        final: float,
        threshold: float
    ) -> Dict[str, str]:
        """Build human-readable explanation."""
        explanations = {}
        
        if decay < 0.5:
            explanations["time_decay"] = "Trust decayed due to time since verification"
        
        if behavior < 0.7:
            explanations["behavior"] = "Recent anomalies reduced trust"
        
        if risk > 0.5:
            explanations["risk"] = "High-risk operation requested"
        
        if final < threshold:
            explanations["decision"] = f"Score {final:.2f} below threshold {threshold}"
        else:
            explanations["decision"] = f"Score {final:.2f} passed threshold {threshold}"
        
        return explanations


# Convenience functions
def quick_trust_check(
    agent_id: str,
    trust_level: str = "medium",
    operation: str = "api_call"
) -> bool:
    """Quick trust check for common operations.
    
    Args:
        agent_id: Agent identifier
        trust_level: Trust level string
        operation: Operation type
        
    Returns:
        True if trusted for operation
    """
    engine = TrustScoreEngine()
    
    level = TrustLevel(trust_level.lower())
    request = Request(operations=[operation])
    
    result = engine.calculate(agent_id, level, request)
    return result.passed_threshold
