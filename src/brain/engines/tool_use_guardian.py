"""
Tool Use Guardian Engine - Function Calling Security

Protects against unauthorized and malicious tool/function usage:
- Permission-based access control
- Argument validation and sanitization
- Scope analysis and restriction
- Dangerous pattern detection

Addresses: OWASP ASI-02 (Tool Misuse)
Research: tool_use_security_deep_dive.md
Invention: Tool Use Guardian (#37)
"""

import re
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Callable

from .base_engine import Severity, Action  # Base classes

logger = logging.getLogger("ToolUseGuardian")


# ============================================================================
# Data Classes
# ============================================================================


class ToolViolationType(Enum):
    """Types of tool use violations."""

    UNAUTHORIZED_TOOL = "unauthorized_tool"
    DANGEROUS_ARGUMENT = "dangerous_argument"
    SCOPE_VIOLATION = "scope_violation"
    RATE_EXCEEDED = "rate_exceeded"
    CHAIN_DEPTH_EXCEEDED = "chain_depth_exceeded"


class Permission(Enum):
    """Tool permission levels."""

    NONE = 0
    READ = 1
    WRITE = 2
    EXECUTE = 3
    ADMIN = 4


@dataclass
class ToolDefinition:
    """Definition of an allowed tool."""

    name: str
    description: str
    required_permission: Permission
    allowed_scopes: Set[str] = field(default_factory=set)
    dangerous_arg_patterns: List[str] = field(default_factory=list)
    rate_limit: int = 100  # calls per minute


@dataclass
class ToolCall:
    """Represents a tool call request."""

    tool_name: str
    arguments: Dict
    caller_id: str
    session_id: str
    chain_depth: int = 0


@dataclass
class GuardianResult:
    """Result from Tool Use Guardian analysis."""

    allowed: bool
    risk_score: float
    violations: List[ToolViolationType] = field(default_factory=list)
    blocked_reason: str = ""
    sanitized_args: Optional[Dict] = None
    latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "allowed": self.allowed,
            "risk_score": self.risk_score,
            "violations": [v.value for v in self.violations],
            "blocked_reason": self.blocked_reason,
            "latency_ms": self.latency_ms,
        }


# ============================================================================
# Permission Manager
# ============================================================================


class PermissionManager:
    """
    Manages tool permissions per user/role.

    Implements RBAC for tool access.
    """

    def __init__(self):
        self._user_permissions: Dict[str, Permission] = {}
        self._role_permissions: Dict[str, Permission] = {
            "admin": Permission.ADMIN,
            "power_user": Permission.EXECUTE,
            "user": Permission.WRITE,
            "guest": Permission.READ,
        }
        self._user_roles: Dict[str, str] = {}

    def set_user_role(self, user_id: str, role: str) -> None:
        """Assign role to user."""
        self._user_roles[user_id] = role

    def set_user_permission(self, user_id: str,
                            permission: Permission) -> None:
        """Set explicit permission for user (overrides role)."""
        self._user_permissions[user_id] = permission

    def get_permission(self, user_id: str) -> Permission:
        """Get effective permission for user."""
        # Explicit permission takes precedence
        if user_id in self._user_permissions:
            return self._user_permissions[user_id]

        # Fall back to role-based
        role = self._user_roles.get(user_id, "guest")
        return self._role_permissions.get(role, Permission.NONE)

    def check_permission(self, user_id: str,
                         required: Permission) -> Tuple[bool, str]:
        """
        Check if user has required permission.

        Returns:
            (allowed, reason)
        """
        user_perm = self.get_permission(user_id)

        if user_perm.value >= required.value:
            return True, ""

        return False, f"Insufficient permission: {user_perm.name} < {required.name}"


# ============================================================================
# Argument Sanitizer
# ============================================================================


class ArgumentSanitizer:
    """
    Sanitizes and validates tool arguments.

    Detects and blocks dangerous patterns.
    """

    DANGEROUS_PATTERNS = [
        # Command injection
        (r";\s*(rm|del|format|shutdown)", "command_injection"),
        (r"\|\s*(bash|sh|cmd|powershell)", "pipe_injection"),
        (r"`[^`]+`", "backtick_execution"),
        (r"\$\([^)]+\)", "subshell_execution"),
        # Path traversal
        (r"\.\./", "path_traversal"),
        (r"\.\.\\", "path_traversal_win"),
        # SQL injection
        (r";\s*DROP\s+TABLE", "sql_injection"),
        (r"'\s*OR\s+'1'\s*=\s*'1", "sql_injection"),
        (r"UNION\s+SELECT", "sql_union"),
        # Code injection
        (r"eval\s*\(", "eval_injection"),
        (r"exec\s*\(", "exec_injection"),
        (r"__import__", "import_injection"),
    ]

    def __init__(
            self, custom_patterns: Optional[List[Tuple[str, str]]] = None):
        patterns = self.DANGEROUS_PATTERNS.copy()
        if custom_patterns:
            patterns.extend(custom_patterns)

        self._patterns = [(re.compile(p, re.IGNORECASE), name)
                          for p, name in patterns]

    def sanitize(self, arguments: Dict) -> Tuple[bool, Dict, List[str]]:
        """
        Sanitize arguments.

        Returns:
            (is_safe, sanitized_args, detected_threats)
        """
        threats = []
        sanitized = {}

        for key, value in arguments.items():
            if isinstance(value, str):
                is_safe, clean, found = self._sanitize_string(value)
                sanitized[key] = clean
                threats.extend(found)
            elif isinstance(value, dict):
                # Recursive sanitization
                is_safe, clean, found = self.sanitize(value)
                sanitized[key] = clean
                threats.extend(found)
            elif isinstance(value, list):
                clean_list = []
                for item in value:
                    if isinstance(item, str):
                        _, clean, found = self._sanitize_string(item)
                        clean_list.append(clean)
                        threats.extend(found)
                    else:
                        clean_list.append(item)
                sanitized[key] = clean_list
            else:
                sanitized[key] = value

        return len(threats) == 0, sanitized, threats

    def _sanitize_string(self, value: str) -> Tuple[bool, str, List[str]]:
        """Sanitize a single string value."""
        threats = []

        for pattern, name in self._patterns:
            if pattern.search(value):
                threats.append(name)

        # If threats found, return empty string
        if threats:
            return False, "[BLOCKED]", threats

        return True, value, []


# ============================================================================
# Scope Analyzer
# ============================================================================


class ScopeAnalyzer:
    """
    Analyzes and enforces scope restrictions.

    Prevents tools from accessing restricted resources.
    """

    def __init__(self):
        self._restricted_scopes: Set[str] = {
            "system",
            "admin",
            "internal",
            "secret",
            "credential",
        }
        self._scope_hierarchy: Dict[str, Set[str]] = {}

    def add_restricted_scope(self, scope: str) -> None:
        """Add a restricted scope."""
        self._restricted_scopes.add(scope.lower())

    def check_scope(
        self, requested_scopes: Set[str], allowed_scopes: Set[str], user_id: str
    ) -> Tuple[bool, str]:
        """
        Check if requested scopes are allowed.

        Returns:
            (allowed, violation_description)
        """
        # Check for restricted scopes
        for scope in requested_scopes:
            if scope.lower() in self._restricted_scopes:
                if scope not in allowed_scopes:
                    return False, f"Restricted scope: {scope}"

        # Check if requested scopes are subset of allowed
        if not requested_scopes.issubset(allowed_scopes):
            excess = requested_scopes - allowed_scopes
            return False, f"Scope violation: {excess}"

        return True, ""


# ============================================================================
# Rate Limiter
# ============================================================================


class RateLimiter:
    """
    Rate limiting for tool calls.

    Prevents abuse through excessive calls.
    """

    def __init__(self, window_seconds: int = 60):
        self.window = window_seconds
        self._calls: Dict[str, List[float]] = {}

    def check(self, key: str, limit: int) -> Tuple[bool, int]:
        """
        Check if under rate limit.

        Returns:
            (allowed, remaining_calls)
        """
        now = time.time()

        if key not in self._calls:
            self._calls[key] = []

        # Remove old entries
        self._calls[key] = [
            t for t in self._calls[key] if now -
            t < self.window]

        current = len(self._calls[key])

        if current >= limit:
            return False, 0

        self._calls[key].append(now)
        return True, limit - current - 1


# ============================================================================
# Main Engine: Tool Use Guardian
# ============================================================================


class ToolUseGuardian:
    """
    Tool Use Guardian - Function Calling Security

    Comprehensive protection against tool misuse:
    - Permission-based access control
    - Argument sanitization
    - Scope enforcement
    - Rate limiting
    - Chain depth control

    Invention #37 from research.
    Addresses OWASP ASI-02.
    """

    def __init__(
        self,
        max_chain_depth: int = 5,
        rate_window: int = 60,
    ):
        self.permission_manager = PermissionManager()
        self.sanitizer = ArgumentSanitizer()
        self.scope_analyzer = ScopeAnalyzer()
        self.rate_limiter = RateLimiter(rate_window)

        self.max_chain_depth = max_chain_depth
        self._tool_registry: Dict[str, ToolDefinition] = {}

        logger.info("ToolUseGuardian initialized")

    def register_tool(self, tool: ToolDefinition) -> None:
        """Register a tool with the guardian."""
        self._tool_registry[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")

    def analyze(self, call: ToolCall) -> GuardianResult:
        """
        Analyze tool call for safety.

        Args:
            call: ToolCall to analyze

        Returns:
            GuardianResult
        """
        start = time.time()

        violations = []
        risk = 0.0
        blocked_reason = ""

        # 1. Check tool exists
        tool = self._tool_registry.get(call.tool_name)
        if not tool:
            violations.append(ToolViolationType.UNAUTHORIZED_TOOL)
            return GuardianResult(
                allowed=False,
                risk_score=1.0,
                violations=violations,
                blocked_reason=f"Unknown tool: {call.tool_name}",
                latency_ms=(time.time() - start) * 1000,
            )

        # 2. Check permission
        has_perm, perm_reason = self.permission_manager.check_permission(
            call.caller_id, tool.required_permission
        )
        if not has_perm:
            violations.append(ToolViolationType.UNAUTHORIZED_TOOL)
            risk = max(risk, 0.9)
            blocked_reason = perm_reason

        # 3. Check rate limit
        rate_key = f"{call.caller_id}:{call.tool_name}"
        under_limit, remaining = self.rate_limiter.check(
            rate_key, tool.rate_limit)
        if not under_limit:
            violations.append(ToolViolationType.RATE_EXCEEDED)
            risk = max(risk, 0.7)
            blocked_reason = f"Rate limit exceeded for {call.tool_name}"

        # 4. Check chain depth
        if call.chain_depth > self.max_chain_depth:
            violations.append(ToolViolationType.CHAIN_DEPTH_EXCEEDED)
            risk = max(risk, 0.8)
            blocked_reason = f"Chain depth {call.chain_depth} > {self.max_chain_depth}"

        # 5. Sanitize arguments
        is_safe, sanitized, threats = self.sanitizer.sanitize(call.arguments)
        if not is_safe:
            violations.append(ToolViolationType.DANGEROUS_ARGUMENT)
            risk = max(risk, 0.95)
            blocked_reason = f"Dangerous arguments: {threats}"

        # 6. Check scopes (if tool defines allowed scopes)
        if tool.allowed_scopes:
            requested = set(call.arguments.get("scopes", []))
            scope_ok, scope_reason = self.scope_analyzer.check_scope(
                requested, tool.allowed_scopes, call.caller_id
            )
            if not scope_ok:
                violations.append(ToolViolationType.SCOPE_VIOLATION)
                risk = max(risk, 0.85)
                blocked_reason = scope_reason

        allowed = len(violations) == 0

        if violations:
            logger.warning(
                f"Tool call blocked: {call.tool_name}, "
                f"violations={[v.value for v in violations]}"
            )

        return GuardianResult(
            allowed=allowed,
            risk_score=risk,
            violations=violations,
            blocked_reason=blocked_reason,
            sanitized_args=sanitized if allowed else None,
            latency_ms=(time.time() - start) * 1000,
        )


# ============================================================================
# Convenience Functions
# ============================================================================

_default_guardian: Optional[ToolUseGuardian] = None


def get_guardian() -> ToolUseGuardian:
    """Get default ToolUseGuardian instance."""
    global _default_guardian
    if _default_guardian is None:
        _default_guardian = ToolUseGuardian()
    return _default_guardian


def analyze_tool_call(
    tool_name: str,
    arguments: Dict,
    caller_id: str,
    session_id: str,
    chain_depth: int = 0,
) -> GuardianResult:
    """Convenience function for tool call analysis."""
    call = ToolCall(tool_name, arguments, caller_id, session_id, chain_depth)
    return get_guardian().analyze(call)
