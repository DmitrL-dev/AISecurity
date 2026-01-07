"""
Human-in-the-Loop Fatigue Detector — SENTINEL R&D Jan 2026

Detects degradation in human oversight quality.

Threat context (AISecHub Jan 2026):
- Users become "approval fatigued" and auto-approve dangerous actions
- Long sessions reduce attention to AI outputs
- Night/tired operators make more mistakes
- Pattern of 100% approval indicates rubber-stamping

Metrics:
- Response time analysis (too fast = not reading)
- Approval pattern detection (100% approve = autoclick)
- Session duration tracking (>4 hours = reduced attention)
- Time-of-day risk scoring

Author: Dmitry Labintsev
Contact: chg@live.ru | @DmLabincev
"""

import time
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
from collections import deque
from datetime import datetime

logger = logging.getLogger("HITLFatigueDetector")


class FatigueLevel(str, Enum):
    """Fatigue severity levels."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ApprovalDecision(str, Enum):
    """Types of human decisions."""
    APPROVE = "approve"
    REJECT = "reject"
    MODIFY = "modify"
    SKIP = "skip"


@dataclass
class ApprovalEvent:
    """Record of a human approval/rejection."""
    event_id: str
    operator_id: str
    request_type: str  # tool_call, message, action
    request_summary: str
    decision: ApprovalDecision
    response_time_ms: float  # Time from presentation to decision
    timestamp: float = field(default_factory=time.time)


@dataclass
class OperatorSession:
    """Tracks an operator's session state."""
    operator_id: str
    session_start: float = field(default_factory=time.time)
    total_decisions: int = 0
    approvals: int = 0
    rejections: int = 0
    modifications: int = 0
    avg_response_time_ms: float = 0.0
    min_response_time_ms: float = float('inf')
    response_times: deque = field(default_factory=lambda: deque(maxlen=100))
    warnings: List[str] = field(default_factory=list)


@dataclass
class FatigueResult:
    """Result of fatigue analysis."""
    fatigue_level: FatigueLevel
    risk_score: float  # 0-100
    indicators: List[str]
    recommendations: List[str]
    should_alert: bool = False
    should_block: bool = False


class HITLFatigueDetector:
    """
    Detects human-in-the-loop fatigue and rubber-stamping.
    
    Warning signs:
    1. Response times < 500ms (not reading content)
    2. 100% approval rate over 20+ decisions
    3. Session > 4 hours without break
    4. Night-time operation (midnight - 6am)
    5. Decreasing response times over session
    """
    
    # Thresholds
    MIN_READ_TIME_MS = 500  # Less than this = not reading
    FAST_APPROVAL_THRESHOLD_MS = 1000  # Suspicious if under 1 second
    MAX_SESSION_HOURS = 4
    SUSPICIOUS_APPROVAL_RATE = 0.95  # 95% approval
    MIN_DECISIONS_FOR_PATTERN = 20
    NIGHT_HOURS = (0, 6)  # Midnight to 6am
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.sessions: Dict[str, OperatorSession] = {}
        self.events: deque = deque(maxlen=10000)
        
        # Override thresholds from config
        if "min_read_time_ms" in self.config:
            self.MIN_READ_TIME_MS = self.config["min_read_time_ms"]
        if "max_session_hours" in self.config:
            self.MAX_SESSION_HOURS = self.config["max_session_hours"]
        
        logger.info("HITLFatigueDetector initialized")
    
    def start_session(self, operator_id: str) -> OperatorSession:
        """Start tracking a new operator session."""
        session = OperatorSession(operator_id=operator_id)
        self.sessions[operator_id] = session
        logger.info(f"Started HITL session for operator: {operator_id}")
        return session
    
    def end_session(self, operator_id: str) -> Optional[OperatorSession]:
        """End an operator session."""
        session = self.sessions.pop(operator_id, None)
        if session:
            logger.info(
                f"Ended session for {operator_id}: "
                f"{session.total_decisions} decisions, "
                f"{session.approvals} approvals"
            )
        return session
    
    def record_decision(
        self,
        operator_id: str,
        request_type: str,
        request_summary: str,
        decision: ApprovalDecision,
        response_time_ms: float
    ) -> Tuple[bool, List[str]]:
        """
        Record a human decision and check for fatigue indicators.
        
        Returns:
            (is_healthy, warnings)
        """
        warnings = []
        
        # Get or create session
        session = self.sessions.get(operator_id)
        if not session:
            session = self.start_session(operator_id)
        
        # Create event
        event = ApprovalEvent(
            event_id=f"{operator_id}_{session.total_decisions}",
            operator_id=operator_id,
            request_type=request_type,
            request_summary=request_summary[:200],
            decision=decision,
            response_time_ms=response_time_ms
        )
        self.events.append(event)
        
        # Update session stats
        session.total_decisions += 1
        session.response_times.append(response_time_ms)
        session.min_response_time_ms = min(
            session.min_response_time_ms, 
            response_time_ms
        )
        
        # Update counts
        if decision == ApprovalDecision.APPROVE:
            session.approvals += 1
        elif decision == ApprovalDecision.REJECT:
            session.rejections += 1
        elif decision == ApprovalDecision.MODIFY:
            session.modifications += 1
        
        # Update average response time
        session.avg_response_time_ms = (
            sum(session.response_times) / len(session.response_times)
        )
        
        # Check for immediate warnings
        
        # 1. Response too fast (not reading)
        if response_time_ms < self.MIN_READ_TIME_MS:
            warnings.append(
                f"Response time {response_time_ms:.0f}ms < minimum {self.MIN_READ_TIME_MS}ms"
            )
        
        # 2. Session too long
        session_hours = (time.time() - session.session_start) / 3600
        if session_hours > self.MAX_SESSION_HOURS:
            warnings.append(
                f"Session duration {session_hours:.1f}h exceeds {self.MAX_SESSION_HOURS}h"
            )
        
        # 3. High approval rate
        if session.total_decisions >= self.MIN_DECISIONS_FOR_PATTERN:
            approval_rate = session.approvals / session.total_decisions
            if approval_rate >= self.SUSPICIOUS_APPROVAL_RATE:
                warnings.append(
                    f"Approval rate {approval_rate:.0%} over {session.total_decisions} decisions"
                )
        
        # Store warnings
        session.warnings.extend(warnings)
        
        is_healthy = len(warnings) == 0
        
        if not is_healthy:
            logger.warning(f"HITL fatigue indicators for {operator_id}: {warnings}")
        
        return is_healthy, warnings
    
    def analyze_fatigue(self, operator_id: str) -> FatigueResult:
        """
        Perform comprehensive fatigue analysis for an operator.
        
        Returns:
            FatigueResult with level, score, and recommendations
        """
        session = self.sessions.get(operator_id)
        if not session:
            return FatigueResult(
                fatigue_level=FatigueLevel.NONE,
                risk_score=0.0,
                indicators=[],
                recommendations=[]
            )
        
        indicators = []
        risk_score = 0.0
        
        # 1. Response time analysis
        if session.avg_response_time_ms < self.MIN_READ_TIME_MS:
            indicators.append("Average response time below reading threshold")
            risk_score += 30.0
        elif session.avg_response_time_ms < self.FAST_APPROVAL_THRESHOLD_MS:
            indicators.append("Average response time suspiciously fast")
            risk_score += 15.0
        
        # 2. Approval rate analysis
        if session.total_decisions >= self.MIN_DECISIONS_FOR_PATTERN:
            approval_rate = session.approvals / session.total_decisions
            if approval_rate >= 1.0:
                indicators.append("100% approval rate (rubber-stamping)")
                risk_score += 40.0
            elif approval_rate >= self.SUSPICIOUS_APPROVAL_RATE:
                indicators.append(f"High approval rate ({approval_rate:.0%})")
                risk_score += 20.0
        
        # 3. Session duration
        session_hours = (time.time() - session.session_start) / 3600
        if session_hours > self.MAX_SESSION_HOURS * 2:
            indicators.append(f"Very long session ({session_hours:.1f}h)")
            risk_score += 30.0
        elif session_hours > self.MAX_SESSION_HOURS:
            indicators.append(f"Extended session ({session_hours:.1f}h)")
            risk_score += 15.0
        
        # 4. Time of day
        current_hour = datetime.now().hour
        if self.NIGHT_HOURS[0] <= current_hour < self.NIGHT_HOURS[1]:
            indicators.append("Night-time operation")
            risk_score += 15.0
        
        # 5. Response time trend (are they getting faster = more fatigued?)
        if len(session.response_times) >= 20:
            first_half = list(session.response_times)[:10]
            second_half = list(session.response_times)[-10:]
            if sum(second_half) / 10 < sum(first_half) / 10 * 0.7:
                indicators.append("Response times decreasing (fatigue trend)")
                risk_score += 20.0
        
        # Determine fatigue level
        risk_score = min(100.0, risk_score)
        
        if risk_score >= 70:
            fatigue_level = FatigueLevel.CRITICAL
        elif risk_score >= 50:
            fatigue_level = FatigueLevel.HIGH
        elif risk_score >= 30:
            fatigue_level = FatigueLevel.MEDIUM
        elif risk_score > 0:
            fatigue_level = FatigueLevel.LOW
        else:
            fatigue_level = FatigueLevel.NONE
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            session, indicators, fatigue_level
        )
        
        return FatigueResult(
            fatigue_level=fatigue_level,
            risk_score=risk_score,
            indicators=indicators,
            recommendations=recommendations,
            should_alert=fatigue_level in [FatigueLevel.HIGH, FatigueLevel.CRITICAL],
            should_block=fatigue_level == FatigueLevel.CRITICAL
        )
    
    def _generate_recommendations(
        self,
        session: OperatorSession,
        indicators: List[str],
        fatigue_level: FatigueLevel
    ) -> List[str]:
        """Generate recommendations based on fatigue analysis."""
        recommendations = []
        
        if fatigue_level == FatigueLevel.CRITICAL:
            recommendations.append("MANDATORY: Take immediate break (15+ minutes)")
            recommendations.append("Consider switching operator")
            recommendations.append("Enable mandatory confirmation delays")
        
        elif fatigue_level == FatigueLevel.HIGH:
            recommendations.append("Recommended: Take a break within 30 minutes")
            recommendations.append("Slow down approval pace")
            recommendations.append("Review last 10 approvals for accuracy")
        
        elif fatigue_level == FatigueLevel.MEDIUM:
            recommendations.append("Schedule a break in the next hour")
            recommendations.append("Increase attention to high-risk requests")
        
        # Session-specific recommendations
        session_hours = (time.time() - session.session_start) / 3600
        if session_hours > self.MAX_SESSION_HOURS:
            recommendations.append(
                f"Session running {session_hours:.1f}h - consider handoff"
            )
        
        if any("approval rate" in i.lower() for i in indicators):
            recommendations.append("Consciously reject at least one request to break pattern")
        
        return recommendations
    
    def get_session_stats(self, operator_id: str) -> Optional[Dict[str, Any]]:
        """Get statistics for an operator session."""
        session = self.sessions.get(operator_id)
        if not session:
            return None
        
        session_hours = (time.time() - session.session_start) / 3600
        approval_rate = (
            session.approvals / session.total_decisions 
            if session.total_decisions > 0 else 0.0
        )
        
        return {
            "operator_id": operator_id,
            "session_duration_hours": session_hours,
            "total_decisions": session.total_decisions,
            "approvals": session.approvals,
            "rejections": session.rejections,
            "modifications": session.modifications,
            "approval_rate": approval_rate,
            "avg_response_time_ms": session.avg_response_time_ms,
            "min_response_time_ms": session.min_response_time_ms,
            "warnings_count": len(session.warnings),
        }


# ============================================================================
# Factory
# ============================================================================

_detector: Optional[HITLFatigueDetector] = None


def get_hitl_fatigue_detector() -> HITLFatigueDetector:
    """Get singleton HITL fatigue detector."""
    global _detector
    if _detector is None:
        _detector = HITLFatigueDetector()
    return _detector


def create_engine(config: Optional[Dict[str, Any]] = None) -> HITLFatigueDetector:
    """Factory function for analyzer integration."""
    return HITLFatigueDetector(config)


# === Unit Tests ===
if __name__ == "__main__":
    detector = HITLFatigueDetector()
    
    print("=== Test 1: Normal Operation ===")
    detector.start_session("operator_1")
    
    # Simulate normal decisions
    for i in range(10):
        is_healthy, warnings = detector.record_decision(
            "operator_1",
            "tool_call",
            f"Execute command {i}",
            ApprovalDecision.APPROVE if i % 3 != 0 else ApprovalDecision.REJECT,
            response_time_ms=2000 + i * 100  # 2-3 seconds
        )
        print(f"Decision {i}: healthy={is_healthy}, warnings={warnings}")
    
    result = detector.analyze_fatigue("operator_1")
    print(f"Fatigue Level: {result.fatigue_level.value}")
    print(f"Risk Score: {result.risk_score}")
    print(f"Indicators: {result.indicators}")
    print(f"Recommendations: {result.recommendations}")
    print()
    
    print("=== Test 2: Rubber-Stamping ===")
    detector.start_session("operator_2")
    
    # Simulate rubber-stamping (fast approvals)
    for i in range(25):
        detector.record_decision(
            "operator_2",
            "tool_call",
            f"Execute dangerous command {i}",
            ApprovalDecision.APPROVE,
            response_time_ms=200  # Too fast!
        )
    
    result = detector.analyze_fatigue("operator_2")
    print(f"Fatigue Level: {result.fatigue_level.value}")
    print(f"Risk Score: {result.risk_score}")
    print(f"Indicators: {result.indicators}")
    print(f"Should Alert: {result.should_alert}")
    print(f"Should Block: {result.should_block}")
