"""
Identity Privilege Abuse Detector - OWASP Agentic AI ASI03 Defense

Based on December 2025 R&D findings:
- OWASP Agentic AI Top 10: ASI03 Identity & Privilege Abuse
- Agent authorization control hijacking
- Credential exploitation in AI agents

Attack mechanism:
1. Attacker exploits agent's credential/trust relationships
2. Agent manipulated to operate beyond authorization boundaries
3. Unauthorized access appears as legitimate agent behavior
4. Result: Data breach, privilege escalation, system compromise

Detection approach:
- Permission boundary enforcement
- Action authorization validation
- Credential usage monitoring
- Trust relationship verification
"""

import re
import logging
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class PrivilegeAbuseSeverity(Enum):
    """Severity levels for privilege abuse detection."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    BENIGN = "benign"


@dataclass
class AgentIdentity:
    """Agent identity and permissions."""
    agent_id: str
    role: str
    permissions: Set[str] = field(default_factory=set)
    trust_level: int = 0  # 0-10
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentAction:
    """Action attempted by an agent."""
    action_type: str
    resource: str
    operation: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    timestamp: Optional[datetime] = None
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PrivilegeAbuseIndicator:
    """Indicator of potential privilege abuse."""
    indicator_type: str
    description: str
    severity: PrivilegeAbuseSeverity
    action: str
    required_permission: str
    confidence: float
    evidence: str


@dataclass
class PrivilegeAbuseResult:
    """Result of privilege abuse analysis."""
    is_authorized: bool
    risk_score: float
    severity: PrivilegeAbuseSeverity
    indicators: List[PrivilegeAbuseIndicator] = field(default_factory=list)
    denied_actions: List[str] = field(default_factory=list)
    recommended_action: str = "allow"
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_authorized": self.is_authorized,
            "risk_score": self.risk_score,
            "severity": self.severity.value,
            "indicators": [
                {
                    "type": i.indicator_type,
                    "description": i.description,
                    "severity": i.severity.value,
                    "action": i.action,
                    "required_permission": i.required_permission,
                }
                for i in self.indicators
            ],
            "denied_actions": self.denied_actions,
            "recommended_action": self.recommended_action,
        }


class IdentityPrivilegeAbuseDetector:
    """
    Detects identity and privilege abuse in AI agents.
    
    Implements OWASP Agentic AI Top 10 ASI03 defense:
    - Permission boundary enforcement
    - Privilege escalation detection
    - Credential abuse monitoring
    - Trust relationship validation
    """

    # Sensitive resource patterns
    SENSITIVE_RESOURCES = {
        "credentials": ["password", "api_key", "secret", "token", "auth"],
        "filesystem": ["system32", "/etc/", "/root", "/admin"],
        "database": ["users", "credentials", "secrets", "admin"],
        "network": ["internal", "private", "localhost", "0.0.0.0"],
    }

    # Dangerous operations
    DANGEROUS_OPERATIONS = {
        "delete": 0.8,
        "drop": 0.9,
        "truncate": 0.85,
        "modify_permissions": 0.9,
        "grant": 0.85,
        "execute_code": 0.95,
        "shell": 0.95,
        "sudo": 1.0,
        "admin": 0.9,
    }

    # Permission hierarchy
    PERMISSION_HIERARCHY = {
        "read": 1,
        "write": 2,
        "execute": 3,
        "delete": 4,
        "admin": 5,
        "root": 6,
    }

    # Escalation patterns
    ESCALATION_PATTERNS = [
        (re.compile(r'run\s+as\s+(admin|root|system)', re.I),
         "role_escalation", 0.9),
        (re.compile(r'sudo|su\s+-|runas', re.I),
         "privilege_escalation", 0.95),
        (re.compile(r'grant\s+\w+\s+to', re.I),
         "permission_grant", 0.85),
        (re.compile(r'disable\s+(auth|security|logging)', re.I),
         "security_bypass", 0.95),
        (re.compile(r'impersonate|assume\s+identity', re.I),
         "identity_impersonation", 0.9),
    ]

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.action_history: List[AgentAction] = []

    def validate_action(
        self,
        agent: AgentIdentity,
        action: AgentAction,
    ) -> PrivilegeAbuseResult:
        """
        Validate if an agent action is authorized.
        
        Args:
            agent: Agent identity and permissions
            action: Action to validate
            
        Returns:
            PrivilegeAbuseResult with validation results
        """
        indicators: List[PrivilegeAbuseIndicator] = []
        denied_actions: List[str] = []
        
        # 1. Check if action requires permission agent doesn't have
        required_perm = self._get_required_permission(action)
        if required_perm and required_perm not in agent.permissions:
            indicators.append(PrivilegeAbuseIndicator(
                indicator_type="missing_permission",
                description=f"Agent lacks required permission: {required_perm}",
                severity=PrivilegeAbuseSeverity.HIGH,
                action=action.action_type,
                required_permission=required_perm,
                confidence=0.9,
                evidence=f"Has: {agent.permissions}",
            ))
            denied_actions.append(action.action_type)
        
        # 2. Check for privilege escalation attempts
        escalation_indicators = self._detect_escalation_attempts(action)
        indicators.extend(escalation_indicators)
        
        # 3. Check for sensitive resource access
        sensitive_indicators = self._check_sensitive_access(agent, action)
        indicators.extend(sensitive_indicators)
        
        # 4. Check for dangerous operations
        danger_indicators = self._check_dangerous_operations(action)
        indicators.extend(danger_indicators)
        
        # 5. Check trust level sufficiency
        trust_indicator = self._validate_trust_level(agent, action)
        if trust_indicator:
            indicators.append(trust_indicator)
        
        # 6. Anomaly detection based on history
        anomaly_indicators = self._detect_behavior_anomalies(agent, action)
        indicators.extend(anomaly_indicators)
        
        # Track action
        self.action_history.append(action)
        
        # Calculate overall assessment
        severity = self._determine_severity(indicators)
        risk_score = self._calculate_risk_score(indicators)
        is_authorized = len(denied_actions) == 0 and risk_score < 0.5
        recommended_action = self._get_recommended_action(severity)
        
        return PrivilegeAbuseResult(
            is_authorized=is_authorized,
            risk_score=risk_score,
            severity=severity,
            indicators=indicators,
            denied_actions=denied_actions,
            recommended_action=recommended_action,
            details={
                "agent_id": agent.agent_id,
                "agent_role": agent.role,
                "trust_level": agent.trust_level,
                "action_type": action.action_type,
            }
        )

    def _get_required_permission(self, action: AgentAction) -> Optional[str]:
        """Determine required permission for an action."""
        op = action.operation.lower()
        
        if op in ["read", "get", "list", "query"]:
            return "read"
        if op in ["write", "set", "update", "create", "insert"]:
            return "write"
        if op in ["execute", "run", "invoke", "call"]:
            return "execute"
        if op in ["delete", "remove", "drop", "truncate"]:
            return "delete"
        if op in ["admin", "grant", "revoke", "configure"]:
            return "admin"
        
        return None

    def _detect_escalation_attempts(
        self,
        action: AgentAction
    ) -> List[PrivilegeAbuseIndicator]:
        """Detect privilege escalation attempts."""
        indicators = []
        
        # Check action text for escalation patterns
        action_text = f"{action.action_type} {action.resource} {action.operation}"
        action_text += " " + str(action.parameters)
        
        for pattern, ind_type, weight in self.ESCALATION_PATTERNS:
            if pattern.search(action_text):
                indicators.append(PrivilegeAbuseIndicator(
                    indicator_type=ind_type,
                    description=f"Privilege escalation attempt: {ind_type}",
                    severity=PrivilegeAbuseSeverity.CRITICAL,
                    action=action.action_type,
                    required_permission="admin",
                    confidence=weight,
                    evidence=pattern.pattern,
                ))
        
        return indicators

    def _check_sensitive_access(
        self,
        agent: AgentIdentity,
        action: AgentAction
    ) -> List[PrivilegeAbuseIndicator]:
        """Check for access to sensitive resources."""
        indicators = []
        resource = action.resource.lower()
        
        for category, patterns in self.SENSITIVE_RESOURCES.items():
            for pattern in patterns:
                if pattern in resource:
                    # Check if agent has appropriate trust level
                    required_trust = 7  # High trust required
                    if agent.trust_level < required_trust:
                        indicators.append(PrivilegeAbuseIndicator(
                            indicator_type=f"sensitive_{category}_access",
                            description=f"Access to sensitive {category} resource",
                            severity=PrivilegeAbuseSeverity.HIGH,
                            action=action.action_type,
                            required_permission=f"{category}_access",
                            confidence=0.8,
                            evidence=f"Resource: {action.resource}",
                        ))
                    break
        
        return indicators

    def _check_dangerous_operations(
        self,
        action: AgentAction
    ) -> List[PrivilegeAbuseIndicator]:
        """Check for dangerous operations."""
        indicators = []
        operation = action.operation.lower()
        
        for dangerous_op, risk_weight in self.DANGEROUS_OPERATIONS.items():
            if dangerous_op in operation:
                indicators.append(PrivilegeAbuseIndicator(
                    indicator_type="dangerous_operation",
                    description=f"Dangerous operation: {dangerous_op}",
                    severity=PrivilegeAbuseSeverity.HIGH,
                    action=action.action_type,
                    required_permission="admin",
                    confidence=risk_weight,
                    evidence=f"Operation: {operation}",
                ))
                break
        
        return indicators

    def _validate_trust_level(
        self,
        agent: AgentIdentity,
        action: AgentAction
    ) -> Optional[PrivilegeAbuseIndicator]:
        """Validate agent trust level for action."""
        # High-risk actions require high trust
        required_trust = self._get_required_trust(action)
        
        if agent.trust_level < required_trust:
            return PrivilegeAbuseIndicator(
                indicator_type="insufficient_trust",
                description=f"Trust level {agent.trust_level} < required {required_trust}",
                severity=PrivilegeAbuseSeverity.MEDIUM,
                action=action.action_type,
                required_permission=f"trust_level_{required_trust}",
                confidence=0.7,
                evidence=f"Agent trust: {agent.trust_level}",
            )
        
        return None

    def _get_required_trust(self, action: AgentAction) -> int:
        """Get required trust level for action."""
        operation = action.operation.lower()
        
        if any(d in operation for d in ["delete", "drop", "admin"]):
            return 8
        if any(d in operation for d in ["write", "execute"]):
            return 5
        if "read" in operation:
            return 2
        
        return 3

    def _detect_behavior_anomalies(
        self,
        agent: AgentIdentity,
        action: AgentAction
    ) -> List[PrivilegeAbuseIndicator]:
        """Detect anomalies based on action history."""
        indicators = []
        
        if len(self.action_history) < 5:
            return indicators
        
        # Check for rapid action rate (potential automation attack)
        recent_actions = self.action_history[-10:]
        same_type = [a for a in recent_actions if a.action_type == action.action_type]
        
        if len(same_type) >= 8:
            indicators.append(PrivilegeAbuseIndicator(
                indicator_type="rapid_repetition",
                description="Unusual rapid action repetition",
                severity=PrivilegeAbuseSeverity.MEDIUM,
                action=action.action_type,
                required_permission="rate_limit",
                confidence=0.65,
                evidence=f"{len(same_type)}/10 same action",
            ))
        
        # Check for escalating access pattern
        if len(self.action_history) >= 10:
            recent_ops = [
                a.operation.lower() for a in self.action_history[-10:]
            ]
            escalation_score = sum(
                self.PERMISSION_HIERARCHY.get(op, 0)
                for op in recent_ops
            ) / len(recent_ops)
            
            if escalation_score > 3:
                indicators.append(PrivilegeAbuseIndicator(
                    indicator_type="escalating_access",
                    description="Escalating access pattern detected",
                    severity=PrivilegeAbuseSeverity.MEDIUM,
                    action=action.action_type,
                    required_permission="access_control",
                    confidence=0.6,
                    evidence=f"Escalation score: {escalation_score:.2f}",
                ))
        
        return indicators

    def _determine_severity(
        self,
        indicators: List[PrivilegeAbuseIndicator]
    ) -> PrivilegeAbuseSeverity:
        """Determine overall severity."""
        if not indicators:
            return PrivilegeAbuseSeverity.BENIGN
        
        severities = [i.severity for i in indicators]
        
        if PrivilegeAbuseSeverity.CRITICAL in severities:
            return PrivilegeAbuseSeverity.CRITICAL
        if PrivilegeAbuseSeverity.HIGH in severities:
            return PrivilegeAbuseSeverity.HIGH
        if PrivilegeAbuseSeverity.MEDIUM in severities:
            return PrivilegeAbuseSeverity.MEDIUM
        
        return PrivilegeAbuseSeverity.LOW

    def _calculate_risk_score(
        self,
        indicators: List[PrivilegeAbuseIndicator]
    ) -> float:
        """Calculate overall risk score."""
        if not indicators:
            return 0.0
        
        severity_scores = {
            PrivilegeAbuseSeverity.CRITICAL: 1.0,
            PrivilegeAbuseSeverity.HIGH: 0.8,
            PrivilegeAbuseSeverity.MEDIUM: 0.5,
            PrivilegeAbuseSeverity.LOW: 0.25,
            PrivilegeAbuseSeverity.BENIGN: 0.0,
        }
        
        max_score = max(
            severity_scores[i.severity] * i.confidence
            for i in indicators
        )
        
        return min(max_score + 0.05 * len(indicators), 1.0)

    def _get_recommended_action(
        self,
        severity: PrivilegeAbuseSeverity
    ) -> str:
        """Get recommended action."""
        actions = {
            PrivilegeAbuseSeverity.CRITICAL: "block_and_alert",
            PrivilegeAbuseSeverity.HIGH: "block",
            PrivilegeAbuseSeverity.MEDIUM: "warn_and_log",
            PrivilegeAbuseSeverity.LOW: "log",
            PrivilegeAbuseSeverity.BENIGN: "allow",
        }
        return actions[severity]


# Example usage
if __name__ == "__main__":
    detector = IdentityPrivilegeAbuseDetector()
    
    # Define agent with limited permissions
    agent = AgentIdentity(
        agent_id="agent-001",
        role="assistant",
        permissions={"read", "write"},
        trust_level=5,
    )
    
    # Test action that exceeds permissions
    action = AgentAction(
        action_type="database_query",
        resource="/admin/users/passwords",
        operation="delete",
        parameters={"all": True},
    )
    
    result = detector.validate_action(agent, action)
    print(f"Is authorized: {result.is_authorized}")
    print(f"Risk score: {result.risk_score:.2f}")
    print(f"Severity: {result.severity.value}")
    print(f"Denied actions: {result.denied_actions}")
    for ind in result.indicators:
        print(f"  - {ind.indicator_type}: {ind.description}")
