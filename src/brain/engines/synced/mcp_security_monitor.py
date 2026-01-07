"""
MCP (Model Context Protocol) Security Monitor

Detects suspicious MCP tool calls, privilege escalation,
and data exfiltration attempts via agent tools.

Auto-generated from R&D: ebpf_redteam_research.md
Generated: 2026-01-07
"""

import re
import logging
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class MCPRiskLevel(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class MCPViolation:
    """Individual MCP security violation."""
    tool_name: str
    violation_type: str
    matched_pattern: str
    argument_value: str
    risk_level: MCPRiskLevel
    recommendation: str


@dataclass
class MCPSecurityResult:
    """Complete MCP security analysis result."""
    detected: bool
    risk_score: float
    violations: List[MCPViolation] = field(default_factory=list)
    blocked: bool = False
    explanation: str = ""


class MCPSecurityMonitor:
    """
    Monitors MCP tool calls for security violations.
    
    Detects:
    - Credential/secret access attempts
    - File system traversal attacks
    - Code execution via tools
    - Data exfiltration patterns
    - Privilege escalation
    """

    # Sensitive file patterns
    SENSITIVE_FILES = [
        (r"/etc/(?:passwd|shadow|sudoers)", "System credentials access"),
        (r"~?/\.(?:ssh|aws|azure|gcloud|kube)", "Cloud/SSH credentials"),
        (r"\.env|\.secrets|\.credentials", "Environment secrets"),
        (r"(?:password|secret|token|key)s?\.(?:txt|json|yaml|yml)", "Secret files"),
        (r"/proc/|/sys/", "System internals access"),
        (r"\.git/config", "Git credentials exposure"),
    ]

    # Dangerous tool patterns
    DANGEROUS_TOOLS = {
        "shell_exec": MCPRiskLevel.CRITICAL,
        "run_command": MCPRiskLevel.CRITICAL,
        "execute_code": MCPRiskLevel.CRITICAL,
        "eval": MCPRiskLevel.CRITICAL,
        "exec": MCPRiskLevel.CRITICAL,
        "bash": MCPRiskLevel.CRITICAL,
        "powershell": MCPRiskLevel.CRITICAL,
        "cmd": MCPRiskLevel.CRITICAL,
    }

    # Exfiltration patterns
    EXFIL_PATTERNS = [
        (r"pastebin\.com|paste\.ee|hastebin", "Known paste service"),
        (r"webhook\.site|requestbin|hookbin", "Webhook testing service"),
        (r"ngrok\.io|localtunnel|serveo", "Tunnel service"),
        (r"discord\.com/api/webhooks", "Discord webhook"),
        (r"slack\.com/api", "Slack API"),
        (r"telegram\.org/bot", "Telegram bot API"),
        (r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d+", "Direct IP:Port"),
    ]

    # Command injection patterns  
    INJECTION_PATTERNS = [
        (r";\s*(?:rm|wget|curl|nc|bash|sh)\s+", "Command chaining"),
        (r"\|\s*(?:bash|sh|nc)\s*", "Pipe to shell"),
        (r"\$\(|`[^`]+`", "Command substitution"),
        (r">\s*/(?:etc|tmp|var)", "Redirect to system path"),
        (r"&&\s*(?:chmod|chown|rm)\s+", "Privilege command"),
    ]

    # Privilege escalation
    PRIVESC_PATTERNS = [
        (r"sudo\s+", "Sudo usage"),
        (r"chmod\s+[0-7]*[67][0-7]*", "Dangerous chmod"),
        (r"chown\s+root", "Chown to root"),
        (r"setuid|setgid|capabilities", "Privilege attribute"),
        (r"passwd|shadow|sudoers", "Auth file modification"),
    ]

    def __init__(self):
        self._compile_patterns()

    def _compile_patterns(self):
        """Pre-compile regex patterns."""
        self._sensitive_compiled = [(re.compile(p, re.I), d) for p, d in self.SENSITIVE_FILES]
        self._exfil_compiled = [(re.compile(p, re.I), d) for p, d in self.EXFIL_PATTERNS]
        self._injection_compiled = [(re.compile(p, re.I), d) for p, d in self.INJECTION_PATTERNS]
        self._privesc_compiled = [(re.compile(p, re.I), d) for p, d in self.PRIVESC_PATTERNS]

    def analyze_tool_call(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        context: Optional[str] = None
    ) -> MCPSecurityResult:
        """
        Analyze a single MCP tool call for security issues.
        
        Args:
            tool_name: Name of the tool being called
            arguments: Tool arguments as dict
            context: Optional context about the call
            
        Returns:
            MCPSecurityResult with findings
        """
        violations: List[MCPViolation] = []

        # Check if tool itself is dangerous
        tool_lower = tool_name.lower()
        if tool_lower in self.DANGEROUS_TOOLS:
            violations.append(MCPViolation(
                tool_name=tool_name,
                violation_type="dangerous_tool",
                matched_pattern=tool_lower,
                argument_value="",
                risk_level=self.DANGEROUS_TOOLS[tool_lower],
                recommendation="Block or require human approval for shell execution"
            ))

        # Flatten arguments for scanning
        arg_str = self._flatten_args(arguments)

        # Check sensitive file access
        for pattern, desc in self._sensitive_compiled:
            match = pattern.search(arg_str)
            if match:
                violations.append(MCPViolation(
                    tool_name=tool_name,
                    violation_type="sensitive_file",
                    matched_pattern=pattern.pattern,
                    argument_value=match.group()[:50],
                    risk_level=MCPRiskLevel.HIGH,
                    recommendation=f"Block access to {desc}"
                ))

        # Check exfiltration patterns
        for pattern, desc in self._exfil_compiled:
            match = pattern.search(arg_str)
            if match:
                violations.append(MCPViolation(
                    tool_name=tool_name,
                    violation_type="exfiltration",
                    matched_pattern=pattern.pattern,
                    argument_value=match.group()[:50],
                    risk_level=MCPRiskLevel.CRITICAL,
                    recommendation=f"Block exfiltration via {desc}"
                ))

        # Check injection patterns
        for pattern, desc in self._injection_compiled:
            match = pattern.search(arg_str)
            if match:
                violations.append(MCPViolation(
                    tool_name=tool_name,
                    violation_type="injection",
                    matched_pattern=pattern.pattern,
                    argument_value=match.group()[:50],
                    risk_level=MCPRiskLevel.CRITICAL,
                    recommendation=f"Block {desc}"
                ))

        # Check privilege escalation
        for pattern, desc in self._privesc_compiled:
            match = pattern.search(arg_str)
            if match:
                violations.append(MCPViolation(
                    tool_name=tool_name,
                    violation_type="privilege_escalation",
                    matched_pattern=pattern.pattern,
                    argument_value=match.group()[:50],
                    risk_level=MCPRiskLevel.CRITICAL,
                    recommendation=f"Block {desc}"
                ))

        # Calculate risk score and block decision
        risk_score = self._calculate_risk(violations)
        should_block = risk_score >= 0.7 or any(
            v.risk_level == MCPRiskLevel.CRITICAL for v in violations
        )

        return MCPSecurityResult(
            detected=len(violations) > 0,
            risk_score=risk_score,
            violations=violations[:5],
            blocked=should_block,
            explanation=self._generate_explanation(violations)
        )

    def _flatten_args(self, arguments: Dict[str, Any]) -> str:
        """Flatten arguments dict to searchable string."""
        parts = []
        for key, value in arguments.items():
            if isinstance(value, str):
                parts.append(f"{key}={value}")
            elif isinstance(value, (list, tuple)):
                parts.append(f"{key}={' '.join(str(v) for v in value)}")
            elif isinstance(value, dict):
                parts.append(self._flatten_args(value))
            else:
                parts.append(f"{key}={value}")
        return " ".join(parts)

    def _calculate_risk(self, violations: List[MCPViolation]) -> float:
        """Calculate risk score 0.0-1.0."""
        if not violations:
            return 0.0

        score = 0.0
        for v in violations:
            if v.risk_level == MCPRiskLevel.CRITICAL:
                score += 0.4
            elif v.risk_level == MCPRiskLevel.HIGH:
                score += 0.25
            elif v.risk_level == MCPRiskLevel.MEDIUM:
                score += 0.1

        return min(1.0, score)

    def _generate_explanation(self, violations: List[MCPViolation]) -> str:
        """Generate human-readable explanation."""
        if not violations:
            return "No security violations detected"

        types = set(v.violation_type for v in violations)
        return f"Detected {len(violations)} violations: {', '.join(types)}"

    def analyze_batch(
        self,
        tool_calls: List[Dict[str, Any]]
    ) -> List[MCPSecurityResult]:
        """Analyze multiple tool calls."""
        return [
            self.analyze_tool_call(
                tc.get("name", "unknown"),
                tc.get("arguments", {}),
                tc.get("context")
            )
            for tc in tool_calls
        ]


# Singleton
_monitor = None

def get_monitor() -> MCPSecurityMonitor:
    global _monitor
    if _monitor is None:
        _monitor = MCPSecurityMonitor()
    return _monitor

def analyze(tool_name: str, arguments: Dict[str, Any]) -> MCPSecurityResult:
    return get_monitor().analyze_tool_call(tool_name, arguments)
