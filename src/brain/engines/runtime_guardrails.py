"""
Runtime Guardrails Engine (#51) - Execution Monitoring

Мониторинг не только input, но и runtime:
- API calls tracking
- Memory access patterns
- Timing anomalies
- Resource usage

Ловит атаки, которые проходят input-фильтры.
"""

import logging
import time
import re
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
from threading import Lock

logger = logging.getLogger("RuntimeGuardrails")


# ============================================================================
# Data Classes
# ============================================================================


class RuntimeEventType(Enum):
    """Types of runtime events."""

    API_CALL = "api_call"
    FILE_ACCESS = "file_access"
    NETWORK_REQUEST = "network_request"
    TOOL_INVOCATION = "tool_invocation"
    MEMORY_ACCESS = "memory_access"
    RESOURCE_USAGE = "resource_usage"


class AlertSeverity(Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RuntimeEvent:
    """A runtime event to monitor."""

    event_type: RuntimeEventType
    timestamp: float
    source: str
    target: str
    details: Dict[str, Any] = field(default_factory=dict)
    user_id: Optional[str] = None
    session_id: Optional[str] = None


@dataclass
class RuntimeAlert:
    """Alert from runtime monitoring."""

    severity: AlertSeverity
    event: RuntimeEvent
    rule_name: str
    message: str
    should_block: bool = False


@dataclass
class RuntimeAnalysisResult:
    """Result of runtime analysis."""

    events_analyzed: int
    alerts: List[RuntimeAlert] = field(default_factory=list)
    blocked: bool = False
    block_reason: str = ""
    risk_score: float = 0.0


# ============================================================================
# Runtime Rules
# ============================================================================


class RuntimeRule:
    """Base class for runtime rules."""

    def __init__(self, name: str, severity: AlertSeverity):
        self.name = name
        self.severity = severity

    def check(
        self, event: RuntimeEvent, history: List[RuntimeEvent]
    ) -> Optional[RuntimeAlert]:
        """Check if event violates rule."""
        raise NotImplementedError


class SuspiciousURLRule(RuntimeRule):
    """Detect suspicious outbound URLs."""

    SUSPICIOUS_PATTERNS = [
        r"ngrok\.io",
        r"webhook\.site",
        r"requestbin",
        r"pipedream",
        r"\.tk$",
        r"\.ml$",
        r"\d+\.\d+\.\d+\.\d+",  # IP addresses
        r"pastebin",
        r"hastebin",
    ]

    def __init__(self):
        super().__init__("suspicious_url", AlertSeverity.HIGH)
        self._patterns = [
            re.compile(p, re.IGNORECASE) for p in self.SUSPICIOUS_PATTERNS
        ]

    def check(
        self, event: RuntimeEvent, history: List[RuntimeEvent]
    ) -> Optional[RuntimeAlert]:
        if event.event_type != RuntimeEventType.NETWORK_REQUEST:
            return None

        target = event.target
        for pattern in self._patterns:
            if pattern.search(target):
                return RuntimeAlert(
                    severity=self.severity,
                    event=event,
                    rule_name=self.name,
                    message=f"Suspicious URL detected: {target}",
                    should_block=True,
                )

        return None


class ExcessiveAPICallsRule(RuntimeRule):
    """Detect excessive API calls."""

    def __init__(self, threshold: int = 10, window_seconds: float = 60.0):
        super().__init__("excessive_api_calls", AlertSeverity.WARNING)
        self.threshold = threshold
        self.window_seconds = window_seconds

    def check(
        self, event: RuntimeEvent, history: List[RuntimeEvent]
    ) -> Optional[RuntimeAlert]:
        if event.event_type != RuntimeEventType.API_CALL:
            return None

        now = event.timestamp
        recent_calls = [
            e
            for e in history
            if e.event_type == RuntimeEventType.API_CALL
            and now - e.timestamp <= self.window_seconds
        ]

        if len(recent_calls) >= self.threshold:
            return RuntimeAlert(
                severity=self.severity,
                event=event,
                rule_name=self.name,
                message=f"Excessive API calls: {len(recent_calls)} in {self.window_seconds}s",
                should_block=False,
            )

        return None


class SensitiveFileAccessRule(RuntimeRule):
    """Detect access to sensitive files."""

    SENSITIVE_PATTERNS = [
        r"\.env",
        r"config\.json",
        r"secrets?",
        r"password",
        r"credentials",
        r"/etc/passwd",
        r"/etc/shadow",
        r"\.ssh/",
        r"\.aws/",
        r"\.kube/",
    ]

    def __init__(self):
        super().__init__("sensitive_file_access", AlertSeverity.CRITICAL)
        self._patterns = [re.compile(p, re.IGNORECASE) for p in self.SENSITIVE_PATTERNS]

    def check(
        self, event: RuntimeEvent, history: List[RuntimeEvent]
    ) -> Optional[RuntimeAlert]:
        if event.event_type != RuntimeEventType.FILE_ACCESS:
            return None

        target = event.target
        for pattern in self._patterns:
            if pattern.search(target):
                return RuntimeAlert(
                    severity=self.severity,
                    event=event,
                    rule_name=self.name,
                    message=f"Sensitive file access: {target}",
                    should_block=True,
                )

        return None


class DangerousToolRule(RuntimeRule):
    """Detect dangerous tool invocations."""

    DANGEROUS_TOOLS = [
        "exec",
        "eval",
        "shell",
        "bash",
        "cmd",
        "subprocess",
        "os.system",
        "popen",
        "rm",
        "delete",
        "drop",
        "truncate",
    ]

    def __init__(self):
        super().__init__("dangerous_tool", AlertSeverity.CRITICAL)

    def check(
        self, event: RuntimeEvent, history: List[RuntimeEvent]
    ) -> Optional[RuntimeAlert]:
        if event.event_type != RuntimeEventType.TOOL_INVOCATION:
            return None

        tool_name = event.target.lower()
        for dangerous in self.DANGEROUS_TOOLS:
            if dangerous in tool_name:
                return RuntimeAlert(
                    severity=self.severity,
                    event=event,
                    rule_name=self.name,
                    message=f"Dangerous tool invocation: {event.target}",
                    should_block=True,
                )

        return None


class UnexpectedNetworkRule(RuntimeRule):
    """Detect unexpected network activity."""

    def __init__(self):
        super().__init__("unexpected_network", AlertSeverity.HIGH)

    def check(
        self, event: RuntimeEvent, history: List[RuntimeEvent]
    ) -> Optional[RuntimeAlert]:
        if event.event_type != RuntimeEventType.NETWORK_REQUEST:
            return None

        # Check if this session had no prior network activity
        session_events = [
            e
            for e in history
            if e.session_id == event.session_id
            and e.event_type == RuntimeEventType.NETWORK_REQUEST
        ]

        if not session_events:
            # First network request in session - suspicious
            return RuntimeAlert(
                severity=self.severity,
                event=event,
                rule_name=self.name,
                message=f"Unexpected network activity: {event.target}",
                should_block=False,
            )

        return None


class TimingAnomalyRule(RuntimeRule):
    """Detect timing anomalies (too fast or too slow)."""

    def __init__(self, min_interval_ms: float = 10.0, max_interval_ms: float = 30000.0):
        super().__init__("timing_anomaly", AlertSeverity.WARNING)
        self.min_interval = min_interval_ms / 1000
        self.max_interval = max_interval_ms / 1000

    def check(
        self, event: RuntimeEvent, history: List[RuntimeEvent]
    ) -> Optional[RuntimeAlert]:
        if not history:
            return None

        last_event = history[-1]
        interval = event.timestamp - last_event.timestamp

        if interval < self.min_interval:
            return RuntimeAlert(
                severity=self.severity,
                event=event,
                rule_name=self.name,
                message=f"Too fast: {interval*1000:.0f}ms between events",
                should_block=False,
            )

        if interval > self.max_interval:
            return RuntimeAlert(
                severity=AlertSeverity.INFO,
                event=event,
                rule_name=self.name,
                message=f"Long delay: {interval:.1f}s between events",
                should_block=False,
            )

        return None


# ============================================================================
# Main Engine
# ============================================================================


class RuntimeGuardrailsEngine:
    """
    Engine #51: Runtime Guardrails

    Monitors runtime behavior to detect attacks that
    bypass input filters.
    """

    def __init__(self, max_history: int = 1000):
        self._history: deque = deque(maxlen=max_history)
        self._lock = Lock()

        # Initialize rules
        self._rules: List[RuntimeRule] = [
            SuspiciousURLRule(),
            ExcessiveAPICallsRule(),
            SensitiveFileAccessRule(),
            DangerousToolRule(),
            UnexpectedNetworkRule(),
            TimingAnomalyRule(),
        ]

        logger.info("RuntimeGuardrailsEngine initialized")

    def record_event(
        self,
        event_type: RuntimeEventType,
        source: str,
        target: str,
        details: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> RuntimeAnalysisResult:
        """
        Record and analyze a runtime event.

        Args:
            event_type: Type of event
            source: Event source
            target: Event target
            details: Additional details
            user_id: User identifier
            session_id: Session identifier

        Returns:
            RuntimeAnalysisResult with any alerts
        """
        event = RuntimeEvent(
            event_type=event_type,
            timestamp=time.time(),
            source=source,
            target=target,
            details=details or {},
            user_id=user_id,
            session_id=session_id,
        )

        with self._lock:
            history = list(self._history)
            self._history.append(event)

        # Check all rules
        alerts = []
        should_block = False

        for rule in self._rules:
            alert = rule.check(event, history)
            if alert:
                alerts.append(alert)
                if alert.should_block:
                    should_block = True

        # Calculate risk score
        risk_score = 0.0
        for alert in alerts:
            if alert.severity == AlertSeverity.CRITICAL:
                risk_score += 0.4
            elif alert.severity == AlertSeverity.HIGH:
                risk_score += 0.25
            elif alert.severity == AlertSeverity.WARNING:
                risk_score += 0.15
            else:
                risk_score += 0.05

        risk_score = min(1.0, risk_score)

        result = RuntimeAnalysisResult(
            events_analyzed=len(history) + 1,
            alerts=alerts,
            blocked=should_block,
            block_reason=alerts[0].message if should_block and alerts else "",
            risk_score=risk_score,
        )

        if alerts:
            logger.warning(
                f"Runtime alerts: {len(alerts)}, blocked={should_block}, "
                f"risk={risk_score:.2f}"
            )

        return result

    def add_rule(self, rule: RuntimeRule):
        """Add custom rule."""
        self._rules.append(rule)

    def get_session_events(self, session_id: str) -> List[RuntimeEvent]:
        """Get all events for a session."""
        with self._lock:
            return [e for e in self._history if e.session_id == session_id]

    def clear_history(self):
        """Clear event history."""
        with self._lock:
            self._history.clear()


# ============================================================================
# Convenience functions
# ============================================================================

_default_engine: Optional[RuntimeGuardrailsEngine] = None


def get_engine() -> RuntimeGuardrailsEngine:
    global _default_engine
    if _default_engine is None:
        _default_engine = RuntimeGuardrailsEngine()
    return _default_engine


def record_api_call(source: str, target: str, **details) -> RuntimeAnalysisResult:
    return get_engine().record_event(RuntimeEventType.API_CALL, source, target, details)


def record_file_access(source: str, path: str, **details) -> RuntimeAnalysisResult:
    return get_engine().record_event(
        RuntimeEventType.FILE_ACCESS, source, path, details
    )


def record_network_request(source: str, url: str, **details) -> RuntimeAnalysisResult:
    return get_engine().record_event(
        RuntimeEventType.NETWORK_REQUEST, source, url, details
    )


def record_tool_invocation(source: str, tool: str, **details) -> RuntimeAnalysisResult:
    return get_engine().record_event(
        RuntimeEventType.TOOL_INVOCATION, source, tool, details
    )
