"""
Tool Call Security Engine (#42) - Agent Tool Protection

Защита от злоупотребления инструментами AI агентов:
- Tool invocation validation
- Permission escalation detection
- MCP (Model Context Protocol) security
- Dangerous tool combination detection

Защита от атак (TTPs.ai):
- AI Agent Tool Invocation
- Privilege Escalation
- Command and Scripting Interpreter abuse
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Set, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("ToolCallSecurity")


# ============================================================================
# Data Classes
# ============================================================================


class ToolThreatType(Enum):
    """Types of tool-related threats."""

    DANGEROUS_TOOL = "dangerous_tool"
    PERMISSION_ESCALATION = "permission_escalation"
    INJECTION_IN_ARGS = "injection_in_args"
    DANGEROUS_COMBINATION = "dangerous_combination"
    EXFILTRATION_ATTEMPT = "exfiltration_attempt"
    CODE_EXECUTION = "code_execution"
    FILE_SYSTEM_ACCESS = "file_system_access"


class Verdict(Enum):
    ALLOW = "allow"
    WARN = "warn"
    BLOCK = "block"


class ToolRiskLevel(Enum):
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ToolCall:
    """Represents a tool/function call."""

    name: str
    arguments: Dict = field(default_factory=dict)
    raw_args: str = ""


@dataclass
class ToolCallResult:
    """Result from Tool Call Security analysis."""

    verdict: Verdict
    risk_score: float
    is_safe: bool
    risk_level: ToolRiskLevel = ToolRiskLevel.SAFE
    threats: List[ToolThreatType] = field(default_factory=list)
    blocked_tools: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    explanation: str = ""
    latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "is_safe": self.is_safe,
            "verdict": self.verdict.value,
            "risk_score": self.risk_score,
            "risk_level": self.risk_level.value,
            "threats": [t.value for t in self.threats],
            "blocked_tools": self.blocked_tools,
            "warnings": self.warnings,
            "explanation": self.explanation,
            "latency_ms": self.latency_ms,
        }


# ============================================================================
# Tool Classification
# ============================================================================

# Dangerous tools that should be blocked or require extra scrutiny
DANGEROUS_TOOLS = {
    # Code execution
    "execute_code": ToolRiskLevel.CRITICAL,
    "run_python": ToolRiskLevel.CRITICAL,
    "run_shell": ToolRiskLevel.CRITICAL,
    "eval": ToolRiskLevel.CRITICAL,
    "exec": ToolRiskLevel.CRITICAL,
    "subprocess": ToolRiskLevel.CRITICAL,
    # File system
    "write_file": ToolRiskLevel.HIGH,
    "delete_file": ToolRiskLevel.CRITICAL,
    "modify_file": ToolRiskLevel.HIGH,
    "create_file": ToolRiskLevel.MEDIUM,
    # Network
    "http_request": ToolRiskLevel.MEDIUM,
    "fetch_url": ToolRiskLevel.MEDIUM,
    "send_email": ToolRiskLevel.HIGH,
    "webhook": ToolRiskLevel.HIGH,
    # Database
    "sql_query": ToolRiskLevel.HIGH,
    "database_write": ToolRiskLevel.HIGH,
    "database_delete": ToolRiskLevel.CRITICAL,
    # System
    "install_package": ToolRiskLevel.CRITICAL,
    "system_command": ToolRiskLevel.CRITICAL,
    "modify_config": ToolRiskLevel.HIGH,
}

# Dangerous tool combinations
DANGEROUS_COMBINATIONS = [
    # Read then exfiltrate
    ({"read_file", "file_read"}, {"http_request", "send_email", "webhook"}),
    # Search then exfiltrate
    ({"search", "query"}, {"http_request", "webhook"}),
    # Code gen then execute
    ({"generate_code", "write_code"}, {"execute_code", "run_python"}),
]

# Argument patterns that indicate injection
INJECTION_IN_ARGS_PATTERNS = [
    r";\s*(rm|del|drop|delete)",
    r"\|\s*(bash|sh|cmd|powershell)",
    r"`.*`",  # Backtick execution
    r"\$\(.*\)",  # Command substitution
    r"&&\s*(rm|del|curl|wget)",
    r">\s*/etc/",  # Write to system dirs
    r"--no-check",  # Bypass security
    r"-rf\s+/",  # Dangerous delete
]


# ============================================================================
# Permission Graph Builder
# ============================================================================


@dataclass
class PermissionNode:
    """Node in the permission graph."""

    tool_name: str
    risk_level: ToolRiskLevel
    capabilities: Set[str] = field(default_factory=set)
    parent_tools: Set[str] = field(default_factory=set)
    child_tools: Set[str] = field(default_factory=set)


class PermissionGraph:
    """
    Builds and manages a DAG of tool permissions.

    Used for:
    - Visualizing permission escalation paths
    - Detecting privilege inheritance chains
    - Analyzing tool dependencies
    """

    # Capability categories
    CAPABILITIES = {
        "read_file": {"file:read"},
        "write_file": {"file:write", "file:read"},
        "delete_file": {"file:delete", "file:write", "file:read"},
        "execute_code": {"code:execute", "system:full"},
        "run_shell": {"shell:execute", "system:full"},
        "http_request": {"network:outbound"},
        "database_read": {"db:read"},
        "database_write": {"db:write", "db:read"},
        "send_email": {"network:outbound", "pii:access"},
    }

    # Permission escalation edges (tool A → tool B = escalation)
    ESCALATION_EDGES = [
        ("read_file", "http_request"),  # Read then exfiltrate
        ("database_read", "http_request"),  # DB read then exfiltrate
        ("generate_code", "execute_code"),  # Gen then exec
        ("write_file", "execute_code"),  # Write then exec
    ]

    def __init__(self):
        self.nodes: Dict[str, PermissionNode] = {}
        self.edges: List[Tuple[str, str]] = []
        self._escalation_paths: List[List[str]] = []

    def add_tool(self, tool: ToolCall) -> PermissionNode:
        """Add a tool to the permission graph."""
        tool_lower = tool.name.lower()

        # Determine risk level
        risk_level = ToolRiskLevel.SAFE
        for dangerous, level in DANGEROUS_TOOLS.items():
            if dangerous in tool_lower:
                risk_level = level
                break

        # Determine capabilities
        capabilities = set()
        for tool_pattern, caps in self.CAPABILITIES.items():
            if tool_pattern in tool_lower:
                capabilities.update(caps)

        node = PermissionNode(
            tool_name=tool.name,
            risk_level=risk_level,
            capabilities=capabilities,
        )

        self.nodes[tool.name] = node
        return node

    def build_from_sequence(self, tools: List[ToolCall]) -> None:
        """Build graph from a sequence of tool calls."""
        prev_tool = None

        for tool in tools:
            node = self.add_tool(tool)

            if prev_tool:
                # Add edge from previous tool
                self.edges.append((prev_tool.name, tool.name))
                node.parent_tools.add(prev_tool.name)
                prev_tool.child_tools.add(tool.name)

            prev_tool = self.nodes[tool.name]

        # Detect escalation paths
        self._detect_escalation_paths()

    def _detect_escalation_paths(self) -> None:
        """Detect permission escalation paths in the graph."""
        self._escalation_paths = []

        for source, sink in self.ESCALATION_EDGES:
            # Find tools matching source pattern
            source_nodes = [n for n in self.nodes if source in n.lower()]
            sink_nodes = [n for n in self.nodes if sink in n.lower()]

            for s in source_nodes:
                for t in sink_nodes:
                    if self._path_exists(s, t):
                        self._escalation_paths.append([s, t])

    def _path_exists(self, source: str, target: str) -> bool:
        """Check if a path exists from source to target."""
        visited = set()
        queue = [source]

        while queue:
            current = queue.pop(0)
            if current == target:
                return True
            if current in visited:
                continue
            visited.add(current)

            if current in self.nodes:
                queue.extend(self.nodes[current].child_tools)

        return False

    def get_escalation_paths(self) -> List[List[str]]:
        """Get detected escalation paths."""
        return self._escalation_paths

    def get_total_capabilities(self) -> Set[str]:
        """Get all capabilities granted by the tool sequence."""
        caps = set()
        for node in self.nodes.values():
            caps.update(node.capabilities)
        return caps

    def get_max_risk(self) -> ToolRiskLevel:
        """Get maximum risk level in the graph."""
        if not self.nodes:
            return ToolRiskLevel.SAFE

        return max(
            (n.risk_level for n in self.nodes.values()),
            key=lambda x: list(ToolRiskLevel).index(x),
        )

    def to_mermaid(self) -> str:
        """Export graph as Mermaid diagram."""
        lines = ["graph TD"]

        # Risk level styling
        risk_styles = {
            ToolRiskLevel.SAFE: ":::safe",
            ToolRiskLevel.LOW: ":::low",
            ToolRiskLevel.MEDIUM: ":::medium",
            ToolRiskLevel.HIGH: ":::high",
            ToolRiskLevel.CRITICAL: ":::critical",
        }

        # Add nodes
        for name, node in self.nodes.items():
            safe_name = name.replace("-", "_").replace(" ", "_")
            style = risk_styles.get(node.risk_level, "")
            caps = ", ".join(list(node.capabilities)[
                             :2]) if node.capabilities else "none"
            lines.append(f'    {safe_name}["{name}<br/>{caps}"]{style}')

        # Add edges
        for source, target in self.edges:
            safe_source = source.replace("-", "_").replace(" ", "_")
            safe_target = target.replace("-", "_").replace(" ", "_")
            lines.append(f"    {safe_source} --> {safe_target}")

        # Highlight escalation paths
        for path in self._escalation_paths:
            if len(path) >= 2:
                safe_source = path[0].replace("-", "_").replace(" ", "_")
                safe_target = path[1].replace("-", "_").replace(" ", "_")
                lines.append(
                    f"    {safe_source} -.->|ESCALATION| {safe_target}")

        # Add styling
        lines.extend([
            "",
            "    classDef safe fill:#90EE90",
            "    classDef low fill:#98FB98",
            "    classDef medium fill:#FFD700",
            "    classDef high fill:#FFA500",
            "    classDef critical fill:#FF4500",
        ])

        return "\n".join(lines)

    def get_statistics(self) -> Dict[str, Any]:
        """Get graph statistics."""
        return {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "escalation_paths": len(self._escalation_paths),
            "max_risk": self.get_max_risk().value,
            "total_capabilities": list(self.get_total_capabilities()),
        }


# ============================================================================
# Tool Invocation Validator
# ============================================================================


class ToolInvocationValidator:
    """Validates individual tool invocations."""

    def __init__(
        self,
        blocked_tools: Optional[Set[str]] = None,
        allow_code_execution: bool = False,
    ):
        self.blocked_tools = blocked_tools or set()
        self.allow_code_execution = allow_code_execution

        self._injection_patterns = [
            re.compile(p, re.IGNORECASE) for p in INJECTION_IN_ARGS_PATTERNS
        ]

    def validate(
        self, tool: ToolCall
    ) -> Tuple[bool, ToolRiskLevel, List[ToolThreatType], List[str]]:
        """
        Validate a tool call.

        Returns:
            (is_safe, risk_level, threats, warnings)
        """
        threats = []
        warnings = []
        risk_level = ToolRiskLevel.SAFE

        tool_lower = tool.name.lower()

        # 1. Check if tool is explicitly blocked
        if tool_lower in self.blocked_tools:
            threats.append(ToolThreatType.DANGEROUS_TOOL)
            return False, ToolRiskLevel.CRITICAL, threats, ["Tool is blocked"]

        # 2. Check against dangerous tools list
        for dangerous, level in DANGEROUS_TOOLS.items():
            if dangerous in tool_lower:
                risk_level = level

                if level == ToolRiskLevel.CRITICAL:
                    if not self.allow_code_execution:
                        threats.append(ToolThreatType.DANGEROUS_TOOL)
                        return False, level, threats, [f"Critical tool: {tool.name}"]

                warnings.append(f"High-risk tool: {tool.name}")
                break

        # 3. Check arguments for injection
        args_str = tool.raw_args or str(tool.arguments)

        for pattern in self._injection_patterns:
            if pattern.search(args_str):
                threats.append(ToolThreatType.INJECTION_IN_ARGS)
                risk_level = ToolRiskLevel.CRITICAL
                return False, risk_level, threats, ["Injection in arguments"]

        # 4. Check for exfiltration patterns in arguments
        exfil_patterns = [
            r"https?://[^\s]+",  # URLs in args
            r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",  # IP addresses
        ]

        for pattern in exfil_patterns:
            if re.search(pattern, args_str):
                if any(t in tool_lower for t in ["http", "request", "send", "post"]):
                    threats.append(ToolThreatType.EXFILTRATION_ATTEMPT)
                    warnings.append("Potential data exfiltration")
                    risk_level = max(
                        risk_level,
                        ToolRiskLevel.HIGH,
                        key=lambda x: list(ToolRiskLevel).index(x),
                    )

        is_safe = len(threats) == 0 and risk_level in [
            ToolRiskLevel.SAFE,
            ToolRiskLevel.LOW,
        ]

        return is_safe, risk_level, threats, warnings


# ============================================================================
# Permission Escalation Detector
# ============================================================================


class PermissionEscalationDetector:
    """Detects permission escalation attempts through tool calls."""

    ESCALATION_PATTERNS = [
        # Admin/root access
        r"(admin|root|sudo|administrator)",
        r"(privilege|permission|access)\s*(level|role)",
        r"(elevat|escalat|promot)",
        # Bypass patterns
        r"(bypass|skip|ignore)\s*(auth|check|valid)",
        r"(disable|remove)\s*(security|protection|guard)",
        r"--force",
        r"--no-verify",
        # Sensitive paths
        r"/etc/(passwd|shadow|sudoers)",
        r"C:\\Windows\\System32",
        r"~/.ssh",
        r".env",
        r"credentials",
        r"(api|secret)_?key",
    ]

    def __init__(self):
        self._patterns = [
            re.compile(p, re.IGNORECASE) for p in self.ESCALATION_PATTERNS
        ]

    def detect(self, tool: ToolCall) -> Tuple[bool, float, List[str]]:
        """
        Detect permission escalation attempts.

        Returns:
            (is_escalation, confidence, indicators)
        """
        indicators = []
        args_str = tool.raw_args or str(tool.arguments)
        combined = f"{tool.name} {args_str}"

        for pattern in self._patterns:
            matches = pattern.findall(combined)
            if matches:
                indicators.append(str(matches[0])[:30])

        if indicators:
            confidence = min(1.0, 0.5 + len(indicators) * 0.15)
            return True, confidence, indicators

        return False, 0.0, []


# ============================================================================
# MCP Security Checker
# ============================================================================


class MCPSecurityChecker:
    """Security checks for Model Context Protocol servers."""

    # Known dangerous MCP server patterns
    SUSPICIOUS_SERVERS = [
        r"file[-_]?system",
        r"shell",
        r"terminal",
        r"exec",
        r"code[-_]?runner",
    ]

    def __init__(self):
        self._suspicious = [
            re.compile(p, re.IGNORECASE) for p in self.SUSPICIOUS_SERVERS
        ]

    def check_server(self, server_name: str) -> Tuple[ToolRiskLevel, List[str]]:
        """
        Check MCP server security level.

        Returns:
            (risk_level, concerns)
        """
        concerns = []

        for pattern in self._suspicious:
            if pattern.search(server_name):
                concerns.append(f"Suspicious server type: {server_name}")

        if concerns:
            return ToolRiskLevel.HIGH, concerns

        return ToolRiskLevel.LOW, []

    def validate_tool_sequence(self, tools: List[ToolCall]) -> Tuple[bool, List[str]]:
        """
        Validate sequence of tool calls for dangerous patterns.

        Returns:
            (is_safe, warnings)
        """
        warnings = []
        tool_names = {t.name.lower() for t in tools}

        # Check dangerous combinations
        for sources, sinks in DANGEROUS_COMBINATIONS:
            used_sources = sources & tool_names
            used_sinks = sinks & tool_names

            if used_sources and used_sinks:
                warnings.append(
                    f"Dangerous combination: {used_sources} → {used_sinks}")

        is_safe = len(warnings) == 0
        return is_safe, warnings


# ============================================================================
# Main Engine
# ============================================================================


class ToolCallSecurity:
    """
    Engine #42: Tool Call Security

    Validates and secures AI agent tool invocations
    to prevent privilege escalation and abuse.
    """

    def __init__(
        self,
        blocked_tools: Optional[Set[str]] = None,
        allow_code_execution: bool = False,
    ):
        self.validator = ToolInvocationValidator(
            blocked_tools=blocked_tools, allow_code_execution=allow_code_execution
        )
        self.escalation_detector = PermissionEscalationDetector()
        self.mcp_checker = MCPSecurityChecker()

        logger.info("ToolCallSecurity initialized")

    def analyze_single(self, tool: ToolCall) -> ToolCallResult:
        """Analyze a single tool call."""
        import time

        start = time.time()

        all_threats = []
        all_warnings = []
        max_risk = ToolRiskLevel.SAFE
        blocked = []

        # 1. Basic validation
        is_valid, risk, threats, warnings = self.validator.validate(tool)
        all_threats.extend(threats)
        all_warnings.extend(warnings)
        max_risk = max(max_risk, risk, key=lambda x: list(
            ToolRiskLevel).index(x))

        if not is_valid:
            blocked.append(tool.name)

        # 2. Escalation detection
        is_escal, conf, indicators = self.escalation_detector.detect(tool)
        if is_escal:
            all_threats.append(ToolThreatType.PERMISSION_ESCALATION)
            all_warnings.extend(indicators[:2])
            max_risk = max(
                max_risk, ToolRiskLevel.HIGH, key=lambda x: list(
                    ToolRiskLevel).index(x)
            )

        # Determine verdict
        risk_index = list(ToolRiskLevel).index(max_risk)
        if risk_index >= list(ToolRiskLevel).index(ToolRiskLevel.CRITICAL):
            verdict = Verdict.BLOCK
        elif risk_index >= list(ToolRiskLevel).index(ToolRiskLevel.HIGH):
            verdict = Verdict.WARN
        else:
            verdict = Verdict.ALLOW

        risk_score = risk_index / 4.0  # Normalize to 0-1

        return ToolCallResult(
            verdict=verdict,
            risk_score=risk_score,
            is_safe=verdict == Verdict.ALLOW,
            risk_level=max_risk,
            threats=list(set(all_threats)),
            blocked_tools=blocked,
            warnings=all_warnings[:5],
            explanation="; ".join(all_warnings[:2]) or "Tool call validated",
            latency_ms=(time.time() - start) * 1000,
        )

    def analyze_sequence(self, tools: List[ToolCall]) -> ToolCallResult:
        """
        Analyze a sequence of tool calls.

        Args:
            tools: List of tool calls to analyze

        Returns:
            Aggregated ToolCallResult
        """
        import time

        start = time.time()

        all_threats = []
        all_warnings = []
        max_risk = ToolRiskLevel.SAFE
        blocked = []

        # Analyze each tool
        for tool in tools:
            result = self.analyze_single(tool)
            all_threats.extend(result.threats)
            all_warnings.extend(result.warnings)
            blocked.extend(result.blocked_tools)
            max_risk = max(
                max_risk, result.risk_level, key=lambda x: list(
                    ToolRiskLevel).index(x)
            )

        # Check sequence patterns
        is_seq_safe, seq_warnings = self.mcp_checker.validate_tool_sequence(
            tools)
        if not is_seq_safe:
            all_threats.append(ToolThreatType.DANGEROUS_COMBINATION)
            all_warnings.extend(seq_warnings)
            max_risk = max(
                max_risk, ToolRiskLevel.HIGH, key=lambda x: list(
                    ToolRiskLevel).index(x)
            )

        # Determine verdict
        risk_index = list(ToolRiskLevel).index(max_risk)
        if risk_index >= list(ToolRiskLevel).index(ToolRiskLevel.CRITICAL):
            verdict = Verdict.BLOCK
        elif (
            risk_index >= list(ToolRiskLevel).index(ToolRiskLevel.HIGH)
            or len(blocked) > 0
        ):
            verdict = Verdict.WARN
        else:
            verdict = Verdict.ALLOW

        risk_score = risk_index / 4.0

        result = ToolCallResult(
            verdict=verdict,
            risk_score=risk_score,
            is_safe=verdict == Verdict.ALLOW and len(blocked) == 0,
            risk_level=max_risk,
            threats=list(set(all_threats)),
            blocked_tools=list(set(blocked)),
            warnings=list(set(all_warnings))[:5],
            explanation=f"Analyzed {len(tools)} tool(s), blocked {len(set(blocked))}",
            latency_ms=(time.time() - start) * 1000,
        )

        if all_threats:
            logger.warning(
                f"Tool security threats: {[t.value for t in result.threats]}, "
                f"blocked={result.blocked_tools}"
            )

        return result


# ============================================================================
# Convenience functions
# ============================================================================

_default_security: Optional[ToolCallSecurity] = None


def get_security() -> ToolCallSecurity:
    global _default_security
    if _default_security is None:
        _default_security = ToolCallSecurity()
    return _default_security


def validate_tool_call(tool: ToolCall) -> ToolCallResult:
    return get_security().analyze_single(tool)


def validate_tool_sequence(tools: List[ToolCall]) -> ToolCallResult:
    return get_security().analyze_sequence(tools)
