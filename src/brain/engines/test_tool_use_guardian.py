"""
Unit tests for Tool Use Guardian Engine.

Tests:
- Permission management
- Argument sanitization
- Scope analysis
- Rate limiting
"""

import pytest
from tool_use_guardian import (
    ToolUseGuardian,
    PermissionManager,
    ArgumentSanitizer,
    ScopeAnalyzer,
    RateLimiter,
    ToolDefinition,
    ToolCall,
    Permission,
    ToolViolationType,
)


# ============================================================================
# Permission Manager Tests
# ============================================================================


class TestPermissionManager:
    """Tests for permission management."""

    def test_default_guest_permission(self):
        """Unassigned user gets guest permission."""
        manager = PermissionManager()
        perm = manager.get_permission("unknown_user")
        assert perm == Permission.READ

    def test_role_based_permission(self):
        """Role-based permission works."""
        manager = PermissionManager()
        manager.set_user_role("user1", "admin")

        perm = manager.get_permission("user1")
        assert perm == Permission.ADMIN

    def test_explicit_permission_overrides_role(self):
        """Explicit permission overrides role."""
        manager = PermissionManager()
        manager.set_user_role("user1", "admin")
        manager.set_user_permission("user1", Permission.READ)

        perm = manager.get_permission("user1")
        assert perm == Permission.READ

    def test_permission_check_allowed(self):
        """Permission check passes when sufficient."""
        manager = PermissionManager()
        manager.set_user_role("user1", "power_user")  # EXECUTE

        allowed, reason = manager.check_permission("user1", Permission.WRITE)
        assert allowed is True

    def test_permission_check_denied(self):
        """Permission check fails when insufficient."""
        manager = PermissionManager()
        manager.set_user_role("user1", "guest")  # READ

        allowed, reason = manager.check_permission("user1", Permission.ADMIN)
        assert allowed is False


# ============================================================================
# Argument Sanitizer Tests
# ============================================================================


class TestArgumentSanitizer:
    """Tests for argument sanitization."""

    def test_clean_args_pass(self):
        """Clean arguments pass."""
        sanitizer = ArgumentSanitizer()

        args = {"query": "SELECT * FROM users", "limit": 10}
        is_safe, clean, threats = sanitizer.sanitize(args)

        assert is_safe is True
        assert len(threats) == 0

    def test_command_injection_blocked(self):
        """Command injection is blocked."""
        sanitizer = ArgumentSanitizer()

        args = {"cmd": "list files; rm -rf /"}
        is_safe, clean, threats = sanitizer.sanitize(args)

        assert is_safe is False
        assert "command_injection" in threats

    def test_path_traversal_blocked(self):
        """Path traversal is blocked."""
        sanitizer = ArgumentSanitizer()

        args = {"path": "../../etc/passwd"}
        is_safe, clean, threats = sanitizer.sanitize(args)

        assert is_safe is False
        assert "path_traversal" in threats

    def test_sql_injection_blocked(self):
        """SQL injection is blocked."""
        sanitizer = ArgumentSanitizer()

        args = {"query": "'; DROP TABLE users; --"}
        is_safe, clean, threats = sanitizer.sanitize(args)

        assert is_safe is False

    def test_nested_args_sanitized(self):
        """Nested arguments are sanitized."""
        sanitizer = ArgumentSanitizer()

        args = {"outer": {"inner": "eval(code)"}}
        is_safe, clean, threats = sanitizer.sanitize(args)

        assert is_safe is False
        assert "eval_injection" in threats


# ============================================================================
# Scope Analyzer Tests
# ============================================================================


class TestScopeAnalyzer:
    """Tests for scope analysis."""

    def test_allowed_scope_passes(self):
        """Allowed scope passes check."""
        analyzer = ScopeAnalyzer()

        requested = {"read", "write"}
        allowed = {"read", "write", "delete"}

        ok, reason = analyzer.check_scope(requested, allowed, "user1")
        assert ok is True

    def test_restricted_scope_blocked(self):
        """Restricted scope is blocked."""
        analyzer = ScopeAnalyzer()

        requested = {"read", "admin"}
        allowed = {"read", "write"}

        ok, reason = analyzer.check_scope(requested, allowed, "user1")
        assert ok is False
        assert "admin" in reason or "Restricted" in reason

    def test_excess_scope_blocked(self):
        """Excess scope is blocked."""
        analyzer = ScopeAnalyzer()

        requested = {"read", "write", "execute"}
        allowed = {"read", "write"}

        ok, reason = analyzer.check_scope(requested, allowed, "user1")
        assert ok is False


# ============================================================================
# Rate Limiter Tests
# ============================================================================


class TestRateLimiter:
    """Tests for rate limiting."""

    def test_under_limit_allowed(self):
        """Under limit calls are allowed."""
        limiter = RateLimiter(window_seconds=60)

        allowed, remaining = limiter.check("key1", limit=10)
        assert allowed is True
        assert remaining == 9

    def test_at_limit_blocked(self):
        """At limit calls are blocked."""
        limiter = RateLimiter(window_seconds=60)

        # Fill up limit
        for _ in range(10):
            limiter.check("key1", limit=10)

        # Next call should be blocked
        allowed, remaining = limiter.check("key1", limit=10)
        assert allowed is False
        assert remaining == 0


# ============================================================================
# Integration Tests
# ============================================================================


class TestToolUseGuardian:
    """Integration tests for Tool Use Guardian."""

    def setup_method(self):
        """Setup guardian with test tools."""
        self.guardian = ToolUseGuardian()

        # Register test tool
        tool = ToolDefinition(
            name="safe_query",
            description="Safe database query",
            required_permission=Permission.READ,
            allowed_scopes={"read"},
            rate_limit=100,
        )
        self.guardian.register_tool(tool)
        self.guardian.permission_manager.set_user_role("test_user", "user")

    def test_allowed_call_passes(self):
        """Valid tool call is allowed."""
        call = ToolCall(
            tool_name="safe_query",
            arguments={"query": "SELECT * FROM products"},
            caller_id="test_user",
            session_id="session1",
        )

        result = self.guardian.analyze(call)

        assert result.allowed is True
        assert len(result.violations) == 0

    def test_unknown_tool_blocked(self):
        """Unknown tool is blocked."""
        call = ToolCall(
            tool_name="evil_tool",
            arguments={},
            caller_id="test_user",
            session_id="session1",
        )

        result = self.guardian.analyze(call)

        assert result.allowed is False
        assert ToolViolationType.UNAUTHORIZED_TOOL in result.violations

    def test_dangerous_args_blocked(self):
        """Dangerous arguments are blocked."""
        call = ToolCall(
            tool_name="safe_query",
            arguments={"query": "data; rm -rf /"},
            caller_id="test_user",
            session_id="session1",
        )

        result = self.guardian.analyze(call)

        assert result.allowed is False
        assert ToolViolationType.DANGEROUS_ARGUMENT in result.violations

    def test_chain_depth_exceeded_blocked(self):
        """Excessive chain depth is blocked."""
        call = ToolCall(
            tool_name="safe_query",
            arguments={"query": "SELECT 1"},
            caller_id="test_user",
            session_id="session1",
            chain_depth=10,  # Exceeds default max of 5
        )

        result = self.guardian.analyze(call)

        assert result.allowed is False
        assert ToolViolationType.CHAIN_DEPTH_EXCEEDED in result.violations


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
