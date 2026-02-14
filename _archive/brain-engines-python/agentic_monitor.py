"""
Agentic AI Monitor - Security for Multi-Agent LLM Systems

Based on OWASP Top 10 for Agentic AI Applications (2025):
  1. Memory Poisoning
  2. Tool Misuse/Abuse
  3. Privilege Escalation
  4. Agent Collusion
  5. Prompt Injection via Tools
  6. Data Exfiltration
  7. Denial of Service
  8. Shadow AI Agents
  9. Insecure Agent Communication
  10. Insufficient Logging

Author: SENTINEL Team
Date: 2025-12-09
"""

import logging
import time
import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Set, Any, Tuple
from collections import defaultdict, deque
import re

logger = logging.getLogger("AgenticMonitor")


# ============================================================================
# Enums and Data Classes
# ============================================================================

class AgentRole(str, Enum):
    """Standard agent roles in multi-agent systems."""
    ORCHESTRATOR = "orchestrator"
    EXECUTOR = "executor"
    PLANNER = "planner"
    RETRIEVER = "retriever"
    VALIDATOR = "validator"
    CUSTOM = "custom"


class ThreatCategory(str, Enum):
    """OWASP Top 10 threat categories for Agentic AI."""
    MEMORY_POISONING = "memory_poisoning"
    TOOL_ABUSE = "tool_abuse"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    AGENT_COLLUSION = "agent_collusion"
    PROMPT_INJECTION = "prompt_injection"
    DATA_EXFILTRATION = "data_exfiltration"
    DENIAL_OF_SERVICE = "denial_of_service"
    SHADOW_AGENT = "shadow_agent"
    INSECURE_COMMUNICATION = "insecure_communication"
    INSUFFICIENT_LOGGING = "insufficient_logging"


class RiskLevel(str, Enum):
    """Risk levels for detected threats."""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AgentProfile:
    """Profile of a registered agent."""
    agent_id: str
    name: str
    role: AgentRole
    allowed_tools: Set[str]
    allowed_targets: Set[str]  # Other agents this can communicate with
    max_requests_per_minute: int = 60
    trust_score: float = 1.0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "role": self.role.value,
            "allowed_tools": list(self.allowed_tools),
            "allowed_targets": list(self.allowed_targets),
            "trust_score": self.trust_score
        }


@dataclass
class AgentInteraction:
    """Record of an agent interaction."""
    interaction_id: str
    source_agent: str
    target_agent: Optional[str]
    action: str  # tool_call, message, memory_write, etc.
    content: str
    tool_name: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ThreatAlert:
    """Alert for detected threat."""
    alert_id: str
    category: ThreatCategory
    risk_level: RiskLevel
    source_agent: str
    description: str
    evidence: List[str]
    timestamp: float = field(default_factory=time.time)
    mitigated: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "category": self.category.value,
            "risk_level": self.risk_level.value,
            "source_agent": self.source_agent,
            "description": self.description,
            "evidence": self.evidence,
            "timestamp": self.timestamp,
            "mitigated": self.mitigated
        }


# ============================================================================
# Threat Detectors
# ============================================================================

class MemoryPoisoningDetector:
    """
    Detects attempts to poison agent memory/context.

    Patterns:
    - Injecting false facts
    - Overwriting existing memories
    - Context manipulation
    """

    POISONING_PATTERNS = [
        # Classic patterns
        r"forget\s+(everything|all|previous)",
        r"your\s+new\s+(instructions?|rules?|guidelines?)",
        r"from\s+now\s+on\s+you\s+are",
        r"disregard\s+(all\s+)?previous",
        r"update\s+your\s+(memory|knowledge|understanding)",
        r"remember\s+that\s+(you\s+are|your\s+name\s+is)",
        # Extended patterns (2025 gaps)
        r"remember\s+(this|that|the\s+following)",
        r"save\s+(this|to\s+your|in\s+your)",
        r"store\s+(this|in\s+your)",
        r"note\s+(this|down|that)",
        r"when\s+.{0,30}asks?\s+about\s+.{0,30}(say|respond|answer)",
        r"if\s+(user|someone|I)\s+(later\s+)?asks?\s+about",
        r"add\s+to\s+your\s+(memory|context|knowledge)",
        r"keep\s+in\s+mind\s+(that|for\s+later)",
    ]

    def __init__(self):
        self.patterns = [re.compile(p, re.IGNORECASE)
                         for p in self.POISONING_PATTERNS]

    def detect(self, content: str) -> Tuple[bool, List[str]]:
        """Detect memory poisoning attempts."""
        matches = []
        for pattern in self.patterns:
            if pattern.search(content):
                matches.append(pattern.pattern)

        return len(matches) > 0, matches


class ToolAbuseDetector:
    """
    Detects tool misuse and abuse patterns.

    Patterns:
    - Excessive tool calls
    - Unauthorized tool access
    - Dangerous parameter values
    """

    DANGEROUS_PATTERNS = {
        "file_system": [r"\.\.\/", r"\/etc\/", r"\/root\/", r"rm\s+-rf", r"del\s+\/"],
        "network": [r"0\.0\.0\.0", r"127\.0\.0\.1.*port", r"curl.*\|.*sh"],
        "code_exec": [r"eval\(", r"exec\(", r"__import__", r"os\.system"],
    }

    def __init__(self, allowed_tools: Set[str] = None):
        self.allowed_tools = allowed_tools or set()
        self.patterns = {
            cat: [re.compile(p, re.IGNORECASE) for p in patterns]
            for cat, patterns in self.DANGEROUS_PATTERNS.items()
        }

    def detect(
        self,
        tool_name: str,
        parameters: str,
        agent_profile: Optional[AgentProfile] = None
    ) -> Tuple[bool, List[str]]:
        """Detect tool abuse."""
        issues = []

        # Check authorization
        if agent_profile and tool_name not in agent_profile.allowed_tools:
            issues.append(f"Unauthorized tool access: {tool_name}")

        # Check dangerous patterns
        for category, patterns in self.patterns.items():
            for pattern in patterns:
                if pattern.search(parameters):
                    issues.append(
                        f"Dangerous pattern ({category}): {pattern.pattern}")

        return len(issues) > 0, issues


class PrivilegeEscalationDetector:
    """
    Detects privilege escalation attempts.

    Patterns:
    - Agent claiming higher privileges
    - Unauthorized role changes
    - Admin impersonation
    """

    ESCALATION_PATTERNS = [
        r"i\s+am\s+(the\s+)?(admin|root|system|supervisor)",
        r"grant\s+(me\s+)?access",
        r"elevate\s+(my\s+)?privileges?",
        r"become\s+(admin|root|superuser)",
        r"sudo|su\s+-",
        r"as\s+(an?\s+)?administrator",
    ]

    def __init__(self):
        self.patterns = [re.compile(p, re.IGNORECASE)
                         for p in self.ESCALATION_PATTERNS]

    def detect(self, content: str) -> Tuple[bool, List[str]]:
        """Detect privilege escalation attempts."""
        matches = []
        for pattern in self.patterns:
            if pattern.search(content):
                matches.append(pattern.pattern)

        return len(matches) > 0, matches


class AgentCollusionDetector:
    """
    Detects potential agent collusion patterns.

    Patterns:
    - Circular communication loops
    - Message forwarding chains
    - Coordinated policy violations
    """

    def __init__(self, window_size: int = 100):
        self.interaction_history: deque = deque(maxlen=window_size)
        self.agent_pairs: Dict[Tuple[str, str], int] = defaultdict(int)

    def record_interaction(self, source: str, target: str) -> None:
        """Record an agent-to-agent interaction."""
        if target:
            self.interaction_history.append((source, target, time.time()))
            self.agent_pairs[(source, target)] += 1

    def detect(self, source: str,
               window_seconds: float = 60.0) -> Tuple[bool, List[str]]:
        """Detect collusion patterns."""
        issues = []
        now = time.time()

        # Check for circular patterns
        recent = [
            (s, t) for s, t, ts in self.interaction_history
            if now - ts < window_seconds
        ]

        # Find loops
        visited = set()
        for s, t in recent:
            if (t, s) in recent and (s, t) not in visited:
                issues.append(f"Circular interaction detected: {s} <-> {t}")
                visited.add((s, t))
                visited.add((t, s))

        # Check for excessive pairwise communication
        for (s, t), count in self.agent_pairs.items():
            if count > 20:  # Threshold
                issues.append(
                    f"Excessive communication: {s} -> {t} ({count} times)")

        return len(issues) > 0, issues


class DataExfiltrationDetector:
    """
    Detects data exfiltration attempts.

    Patterns:
    - Sensitive data in outgoing messages
    - Encoding attempts (base64, hex)
    - External URL mentions
    """

    SENSITIVE_PATTERNS = [
        r"password\s*[=:]\s*\S+",
        r"api[_-]?key\s*[=:]\s*\S+",
        r"secret\s*[=:]\s*\S+",
        r"token\s*[=:]\s*\S+",
        r"bearer\s+\S+",
        r"-----BEGIN.*PRIVATE KEY-----",
    ]

    ENCODING_PATTERNS = [
        r"base64",
        r"[A-Za-z0-9+/]{50,}={0,2}",  # Base64-like strings
        r"\\x[0-9a-f]{2}",  # Hex encoding
    ]

    def __init__(self):
        self.sensitive = [re.compile(p, re.IGNORECASE)
                          for p in self.SENSITIVE_PATTERNS]
        self.encoding = [re.compile(p, re.IGNORECASE)
                         for p in self.ENCODING_PATTERNS]

    def detect(self, content: str) -> Tuple[bool, List[str]]:
        """Detect data exfiltration attempts."""
        issues = []

        for pattern in self.sensitive:
            if pattern.search(content):
                issues.append(f"Sensitive data detected: {pattern.pattern}")

        for pattern in self.encoding:
            if pattern.search(content):
                issues.append(f"Potential encoding: {pattern.pattern}")

        return len(issues) > 0, issues


class InterAgentSecurityDetector:
    """
    Detects insecure inter-agent communication (ASI07).

    OWASP Agentic Top 10 2026 Coverage:
    - Agent identity spoofing
    - MCP/A2A protocol abuse
    - Agent card manipulation
    - Unsigned/unverified messages
    - Confused deputy attacks
    """

    INSECURE_PATTERNS = [
        # Agent identity spoofing
        r"agent[_-]?id\s*[=:]\s*[\"']?admin",
        r"from[_-]?agent\s*[=:]\s*.*(orchestrator|system|root)",
        r"\.well-known/agent\.json",
        r"agent[_-]?card\s*[=:]\s*",

        # MCP protocol abuse
        r"mcp[_-]?server\s*[=:]\s*",
        r"tool[_-]?descriptor\s*[=:]\s*",
        r"capability[_-]?override",

        # Trust manipulation
        r"trust[_-]?level\s*[=:]\s*(high|admin|system)",
        r"verified\s*[=:]\s*(true|1)",
        r"signature\s*[=:]\s*[\"']?none",

        # A2A protocol abuse
        r"agent2agent\s*auth\s*bypass",
        r"forward[_-]?to[_-]?agent.*without.*verification",
    ]

    def __init__(self):
        self.patterns = [re.compile(p, re.IGNORECASE)
                         for p in self.INSECURE_PATTERNS]

    def detect(
        self,
        content: str,
        source_agent: str,
        target_agent: Optional[str] = None
    ) -> Tuple[bool, List[str]]:
        """Detect insecure inter-agent communication patterns."""
        issues = []

        # Check for insecure patterns
        for pattern in self.patterns:
            if pattern.search(content):
                issues.append(
                    f"Insecure communication pattern: {pattern.pattern}")

        return len(issues) > 0, issues


# ============================================================================
# Rate Limiter
# ============================================================================

class AgentRateLimiter:
    """Rate limiter for agent actions."""

    def __init__(self, window_seconds: float = 60.0):
        self.window = window_seconds
        self.action_counts: Dict[str, deque] = defaultdict(lambda: deque())

    def check(self, agent_id: str, max_requests: int) -> Tuple[bool, int]:
        """
        Check if agent is within rate limit.

        Returns:
            (allowed, current_count)
        """
        now = time.time()
        actions = self.action_counts[agent_id]

        # Remove old actions
        while actions and now - actions[0] > self.window:
            actions.popleft()

        current = len(actions)
        allowed = current < max_requests

        if allowed:
            actions.append(now)

        return allowed, current


# ============================================================================
# Autonomous Loop Controller (Jan 2026 - AISecHub threat response)
# ============================================================================


@dataclass
class LoopState:
    """Tracks state of an agent's execution loop."""
    agent_id: str
    loop_start: float = field(default_factory=time.time)
    tool_calls: int = 0
    tokens_used: int = 0
    same_tool_streak: int = 0
    last_tool: Optional[str] = None
    task_deviation_score: float = 0.0
    warnings: List[str] = field(default_factory=list)


class AutonomousLoopController:
    """
    Controls autonomous agent execution loops.
    
    Threat context (Jan 2026):
    - Agentic loops losing control (human-in-the-loop fatigue)
    - Infinite recursion attacks
    - Token budget exhaustion attacks
    - Task deviation exploitation
    
    Detects:
    - Runaway loops (excessive iterations)
    - Infinite recursion patterns
    - Token budget violations
    - Task deviation (agent going off-task)
    """
    
    # Thresholds
    MAX_TOOL_CALLS_PER_TASK = 100
    MAX_SAME_TOOL_STREAK = 10
    MAX_TOKENS_PER_TASK = 100000
    MAX_LOOP_DURATION_SECONDS = 300  # 5 minutes
    TASK_DEVIATION_THRESHOLD = 0.7
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.active_loops: Dict[str, LoopState] = {}
        
        # Override defaults from config
        if "max_tool_calls" in self.config:
            self.MAX_TOOL_CALLS_PER_TASK = self.config["max_tool_calls"]
        if "max_tokens" in self.config:
            self.MAX_TOKENS_PER_TASK = self.config["max_tokens"]
        if "max_duration" in self.config:
            self.MAX_LOOP_DURATION_SECONDS = self.config["max_duration"]
        
        logger.info("AutonomousLoopController initialized")
    
    def start_loop(self, agent_id: str, task_description: str = "") -> LoopState:
        """Start tracking a new agent loop."""
        state = LoopState(agent_id=agent_id)
        self.active_loops[agent_id] = state
        logger.debug(f"Started loop tracking for agent: {agent_id}")
        return state
    
    def end_loop(self, agent_id: str) -> Optional[LoopState]:
        """End tracking for an agent loop."""
        return self.active_loops.pop(agent_id, None)
    
    def record_tool_call(
        self,
        agent_id: str,
        tool_name: str,
        tokens_used: int = 0
    ) -> Tuple[bool, List[str]]:
        """
        Record a tool call and check for violations.
        
        Returns:
            (should_continue, warnings)
        """
        issues = []
        
        state = self.active_loops.get(agent_id)
        if not state:
            # Auto-start tracking
            state = self.start_loop(agent_id)
        
        # Update state
        state.tool_calls += 1
        state.tokens_used += tokens_used
        
        # Check same tool streak
        if tool_name == state.last_tool:
            state.same_tool_streak += 1
        else:
            state.same_tool_streak = 1
        state.last_tool = tool_name
        
        # Check violations
        
        # 1. Too many tool calls
        if state.tool_calls > self.MAX_TOOL_CALLS_PER_TASK:
            issues.append(
                f"Tool call limit exceeded: {state.tool_calls}/{self.MAX_TOOL_CALLS_PER_TASK}"
            )
        
        # 2. Same tool called too many times in a row (infinite loop indicator)
        if state.same_tool_streak > self.MAX_SAME_TOOL_STREAK:
            issues.append(
                f"Infinite loop detected: {tool_name} called {state.same_tool_streak} times"
            )
        
        # 3. Token budget exceeded
        if state.tokens_used > self.MAX_TOKENS_PER_TASK:
            issues.append(
                f"Token budget exceeded: {state.tokens_used}/{self.MAX_TOKENS_PER_TASK}"
            )
        
        # 4. Loop running too long
        elapsed = time.time() - state.loop_start
        if elapsed > self.MAX_LOOP_DURATION_SECONDS:
            issues.append(
                f"Loop timeout: {elapsed:.0f}s > {self.MAX_LOOP_DURATION_SECONDS}s"
            )
        
        # Store warnings
        state.warnings.extend(issues)
        
        should_continue = len(issues) == 0
        
        if not should_continue:
            logger.warning(
                f"Loop controller stopping agent {agent_id}: {issues}"
            )
        
        return should_continue, issues
    
    def check_task_deviation(
        self,
        agent_id: str,
        original_task: str,
        current_action: str
    ) -> Tuple[bool, float]:
        """
        Check if agent is deviating from original task.
        
        Uses simple heuristic: overlap of keywords.
        
        Returns:
            (is_deviating, deviation_score)
        """
        # Simple keyword overlap check
        task_words = set(original_task.lower().split())
        action_words = set(current_action.lower().split())
        
        if not task_words:
            return False, 0.0
        
        overlap = len(task_words & action_words) / len(task_words)
        deviation_score = 1.0 - overlap
        
        state = self.active_loops.get(agent_id)
        if state:
            state.task_deviation_score = deviation_score
        
        is_deviating = deviation_score > self.TASK_DEVIATION_THRESHOLD
        
        return is_deviating, deviation_score
    
    def get_loop_status(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get status of an agent's loop."""
        state = self.active_loops.get(agent_id)
        if not state:
            return None
        
        elapsed = time.time() - state.loop_start
        
        return {
            "agent_id": agent_id,
            "tool_calls": state.tool_calls,
            "tokens_used": state.tokens_used,
            "elapsed_seconds": elapsed,
            "same_tool_streak": state.same_tool_streak,
            "last_tool": state.last_tool,
            "task_deviation_score": state.task_deviation_score,
            "warnings": state.warnings,
            "limits": {
                "max_tool_calls": self.MAX_TOOL_CALLS_PER_TASK,
                "max_tokens": self.MAX_TOKENS_PER_TASK,
                "max_duration": self.MAX_LOOP_DURATION_SECONDS,
            }
        }
    
    def force_terminate(self, agent_id: str, reason: str) -> bool:
        """Force terminate an agent's loop."""
        state = self.active_loops.get(agent_id)
        if state:
            state.warnings.append(f"FORCE TERMINATED: {reason}")
            logger.warning(f"Force terminated agent {agent_id}: {reason}")
            self.end_loop(agent_id)
            return True
        return False


# ============================================================================
# Main Agentic Monitor
# ============================================================================

class AgenticMonitor:
    """
    Main monitor for multi-agent LLM systems.

    Provides:
    - Agent registration and profiling
    - Interaction tracking
    - Threat detection (OWASP Top 10)
    - Rate limiting
    - Audit logging
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}

        # Agent management
        self.agents: Dict[str, AgentProfile] = {}

        # Detectors
        self.memory_detector = MemoryPoisoningDetector()
        self.tool_detector = ToolAbuseDetector()
        self.privilege_detector = PrivilegeEscalationDetector()
        self.collusion_detector = AgentCollusionDetector()
        self.exfiltration_detector = DataExfiltrationDetector()
        self.inter_agent_detector = InterAgentSecurityDetector()  # ASI07

        # Rate limiting
        self.rate_limiter = AgentRateLimiter()

        # Logging
        self.interactions: deque = deque(maxlen=10000)
        self.alerts: List[ThreatAlert] = []

        logger.info("AgenticMonitor initialized")

    def register_agent(self, profile: AgentProfile) -> None:
        """Register an agent for monitoring."""
        self.agents[profile.agent_id] = profile
        logger.info(f"Registered agent: {profile.name} ({profile.role.value})")

    def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent."""
        if agent_id in self.agents:
            del self.agents[agent_id]
            return True
        return False

    def monitor_interaction(
        self,
        source_agent: str,
        action: str,
        content: str,
        target_agent: Optional[str] = None,
        tool_name: Optional[str] = None,
        tool_params: Optional[str] = None
    ) -> Tuple[bool, List[ThreatAlert]]:
        """
        Monitor an agent interaction.

        Args:
            source_agent: ID of acting agent
            action: Type of action (message, tool_call, memory_write)
            content: Content of the action
            target_agent: Optional target agent
            tool_name: Optional tool being called
            tool_params: Optional tool parameters

        Returns:
            (is_allowed, alerts)
        """
        alerts = []
        agent_profile = self.agents.get(source_agent)

        # Create interaction record
        interaction = AgentInteraction(
            interaction_id=self._generate_id(),
            source_agent=source_agent,
            target_agent=target_agent,
            action=action,
            content=content[:500],  # Truncate
            tool_name=tool_name
        )
        self.interactions.append(interaction)

        # 1. Check rate limit
        if agent_profile:
            allowed, count = self.rate_limiter.check(
                source_agent, agent_profile.max_requests_per_minute
            )
            if not allowed:
                alerts.append(self._create_alert(
                    ThreatCategory.DENIAL_OF_SERVICE,
                    RiskLevel.MEDIUM,
                    source_agent,
                    f"Rate limit exceeded ({count} requests/min)",
                    ["Rate limit violation"]
                ))

        # 2. Check for memory poisoning
        is_threat, evidence = self.memory_detector.detect(content)
        if is_threat:
            alerts.append(self._create_alert(
                ThreatCategory.MEMORY_POISONING,
                RiskLevel.HIGH,
                source_agent,
                "Memory poisoning attempt detected",
                evidence
            ))

        # 3. Check privilege escalation
        is_threat, evidence = self.privilege_detector.detect(content)
        if is_threat:
            alerts.append(self._create_alert(
                ThreatCategory.PRIVILEGE_ESCALATION,
                RiskLevel.HIGH,
                source_agent,
                "Privilege escalation attempt detected",
                evidence
            ))

        # 4. Check tool abuse
        if tool_name and tool_params:
            is_threat, evidence = self.tool_detector.detect(
                tool_name, tool_params, agent_profile
            )
            if is_threat:
                alerts.append(self._create_alert(
                    ThreatCategory.TOOL_ABUSE,
                    RiskLevel.CRITICAL,
                    source_agent,
                    f"Tool abuse detected: {tool_name}",
                    evidence
                ))

        # 5. Check data exfiltration
        is_threat, evidence = self.exfiltration_detector.detect(content)
        if is_threat:
            alerts.append(self._create_alert(
                ThreatCategory.DATA_EXFILTRATION,
                RiskLevel.CRITICAL,
                source_agent,
                "Data exfiltration attempt detected",
                evidence
            ))

        # 6. Track for collusion detection
        if target_agent:
            self.collusion_detector.record_interaction(
                source_agent, target_agent)
            is_threat, evidence = self.collusion_detector.detect(source_agent)
            if is_threat:
                alerts.append(self._create_alert(
                    ThreatCategory.AGENT_COLLUSION,
                    RiskLevel.MEDIUM,
                    source_agent,
                    "Potential agent collusion detected",
                    evidence
                ))

        # 7. Check for shadow agent
        if source_agent not in self.agents:
            alerts.append(self._create_alert(
                ThreatCategory.SHADOW_AGENT,
                RiskLevel.HIGH,
                source_agent,
                "Unregistered agent detected",
                [f"Agent ID: {source_agent}"]
            ))

        # 8. Check inter-agent security (ASI07)
        if target_agent:
            is_threat, evidence = self.inter_agent_detector.detect(
                content, source_agent, target_agent)
            if is_threat:
                alerts.append(self._create_alert(
                    ThreatCategory.INSECURE_COMMUNICATION,
                    RiskLevel.HIGH,
                    source_agent,
                    "Insecure inter-agent communication detected",
                    evidence
                ))

        # Store alerts
        self.alerts.extend(alerts)

        # Determine if action should be allowed
        is_allowed = not any(
            a.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
            for a in alerts
        )

        return is_allowed, alerts

    def get_agent_trust_score(self, agent_id: str) -> float:
        """Get trust score for an agent based on history."""
        profile = self.agents.get(agent_id)
        if not profile:
            return 0.0

        # Reduce score based on alerts
        agent_alerts = [a for a in self.alerts if a.source_agent == agent_id]
        penalty = sum(
            0.1 if a.risk_level == RiskLevel.LOW else
            0.2 if a.risk_level == RiskLevel.MEDIUM else
            0.3 if a.risk_level == RiskLevel.HIGH else
            0.5  # CRITICAL
            for a in agent_alerts
        )

        return max(0.0, profile.trust_score - penalty)

    def get_alerts(
        self,
        category: Optional[ThreatCategory] = None,
        risk_level: Optional[RiskLevel] = None,
        limit: int = 100
    ) -> List[ThreatAlert]:
        """Get alerts, optionally filtered."""
        filtered = self.alerts

        if category:
            filtered = [a for a in filtered if a.category == category]
        if risk_level:
            filtered = [a for a in filtered if a.risk_level == risk_level]

        return filtered[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """Get monitoring statistics."""
        alert_counts = defaultdict(int)
        for alert in self.alerts:
            alert_counts[alert.category.value] += 1

        return {
            "registered_agents": len(self.agents),
            "total_interactions": len(self.interactions),
            "total_alerts": len(self.alerts),
            "alerts_by_category": dict(alert_counts),
            "critical_alerts": sum(
                1 for a in self.alerts if a.risk_level == RiskLevel.CRITICAL
            )
        }

    def _create_alert(
        self,
        category: ThreatCategory,
        risk_level: RiskLevel,
        source_agent: str,
        description: str,
        evidence: List[str]
    ) -> ThreatAlert:
        """Create a threat alert."""
        alert = ThreatAlert(
            alert_id=self._generate_id(),
            category=category,
            risk_level=risk_level,
            source_agent=source_agent,
            description=description,
            evidence=evidence
        )

        logger.warning(
            f"ALERT [{risk_level.value}] {category.value}: {description}"
        )

        return alert

    def _generate_id(self) -> str:
        """Generate unique ID."""
        return hashlib.sha256(
            f"{time.time()}{len(self.interactions)}".encode()
        ).hexdigest()[:12]
