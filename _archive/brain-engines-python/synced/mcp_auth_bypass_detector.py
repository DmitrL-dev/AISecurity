"""
MCP Authorization Bypass Detector

Detects authorization vulnerabilities in MCP (Model Context Protocol):
- Account/user ID parameter manipulation
- Cross-tenant access attempts
- Missing token scope validation
- Server-to-server auth gaps

Sources:
- Praetorian: praetorian.com/blog/as-strong-as-your-weakest-parameter
- StackOverflow: MCP auth specification gaps
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("MCPAuthBypassDetector")


@dataclass
class AuthBypassResult:
    """Result of MCP authorization analysis."""

    is_suspicious: bool
    has_scope_issue: bool = False
    has_auth_issue: bool = False
    risk_score: float = 0.0
    risks: List[str] = field(default_factory=list)
    remediation: str = ""

    def to_dict(self) -> dict:
        return {
            "is_suspicious": self.is_suspicious,
            "has_scope_issue": self.has_scope_issue,
            "has_auth_issue": self.has_auth_issue,
            "risk_score": self.risk_score,
            "risks": self.risks,
            "remediation": self.remediation,
        }


class MCPAuthBypassDetector:
    """
    Detects MCP authorization bypass attempts.

    Based on Praetorian research showing account_id manipulation
    and StackOverflow analysis of MCP auth specification gaps.
    """

    def __init__(self):
        # Suspicious parameter names (IDOR indicators)
        self.idor_params = [
            "account_id",
            "user_id",
            "tenant_id",
            "org_id",
            "customer_id",
            "owner_id",
            "member_id",
            "workspace_id",
        ]

        # Prompt patterns for history extraction
        self.history_patterns = [
            re.compile(r"summarize.*(?:our|all).*conversations?", re.I),
            re.compile(r"previous.*(?:chat|conversation|history)", re.I),
            re.compile(r"what.*(?:we|I).*discussed", re.I),
            re.compile(r"personal.*details.*mentioned", re.I),
            re.compile(r"context.*(?:our|the).*interactions?", re.I),
        ]

        # Cross-resource URI patterns
        self.xresource_patterns = [
            re.compile(r"user://(?!self|me|current)[\w-]+/", re.I),
            re.compile(r"tenant://(?!self)[\w-]+/", re.I),
            re.compile(r"/other_user|/admin|/root/", re.I),
        ]

    def analyze_request(self, request: Dict[str, Any]) -> AuthBypassResult:
        """Analyze MCP request for auth bypass indicators."""
        risks = []
        score = 0.0

        params = request.get("params", {})
        if isinstance(params, dict):
            args = params.get("arguments", params)

            # Check for IDOR parameters
            for key in args.keys() if isinstance(args, dict) else []:
                key_lower = key.lower()
                for idor in self.idor_params:
                    if idor in key_lower:
                        risks.append(f"IDOR: {key} parameter in request")
                        score += 60.0
                        break

            # Check URI for cross-resource access
            uri = params.get("uri", "")
            for pattern in self.xresource_patterns:
                if pattern.search(uri):
                    risks.append(f"Cross-resource URI: {uri[:50]}")
                    score += 70.0
                    break

        is_suspicious = len(risks) > 0
        remediation = ""
        if is_suspicious:
            remediation = (
                "Validate that user can only access their own resources. "
                "Enforce tenant isolation at the data layer. "
                "Use token claims for authorization, not request params."
            )

        return AuthBypassResult(
            is_suspicious=is_suspicious,
            risk_score=min(score, 100.0),
            risks=risks,
            remediation=remediation,
        )

    def analyze_prompt(self, prompt: str) -> AuthBypassResult:
        """Analyze prompt for privilege escalation attempts."""
        risks = []
        score = 0.0

        for pattern in self.history_patterns:
            if pattern.search(prompt):
                risks.append("History extraction: conversation summary request")
                score += 50.0
                break

        is_suspicious = len(risks) > 0
        remediation = ""
        if is_suspicious:
            remediation = (
                "Implement conversation history access controls. "
                "Verify user ownership before returning chat history."
            )

        return AuthBypassResult(
            is_suspicious=is_suspicious,
            risk_score=min(score, 100.0),
            risks=risks,
            remediation=remediation,
        )

    def analyze_context(self, context: Dict[str, Any]) -> AuthBypassResult:
        """Analyze full request context for auth issues."""
        risks = []
        has_scope_issue = False
        has_auth_issue = False
        score = 0.0

        token = context.get("token", {})
        request = context.get("request", {})
        downstream = context.get("downstream_call", {})

        # Check token scope
        if token and "scope" not in token:
            has_scope_issue = True
            risks.append("Missing scope claim in token")
            score += 40.0

        # Check tenant isolation
        token_tenant = token.get("tenant_id")
        req_params = request.get("params", {})
        req_tenant = req_params.get("tenant_id")

        if token_tenant and req_tenant and token_tenant != req_tenant:
            risks.append(f"Tenant mismatch: token={token_tenant}, req={req_tenant}")
            score += 80.0

        # Check S2S auth
        if downstream:
            headers = downstream.get("headers", {})
            if not any(
                h.lower() in ["authorization", "x-api-key"] for h in headers.keys()
            ):
                has_auth_issue = True
                risks.append("Missing auth header in downstream call")
                score += 50.0

        is_suspicious = len(risks) > 0
        remediation = ""
        if is_suspicious:
            remediation = (
                "Enforce scope-based access control. "
                "Validate tenant boundaries. "
                "Use service accounts for S2S calls."
            )

        return AuthBypassResult(
            is_suspicious=is_suspicious,
            has_scope_issue=has_scope_issue,
            has_auth_issue=has_auth_issue,
            risk_score=min(score, 100.0),
            risks=risks,
            remediation=remediation,
        )


def detect_mcp_auth_bypass(
    request: Optional[Dict] = None,
    prompt: Optional[str] = None,
    context: Optional[Dict] = None,
) -> AuthBypassResult:
    """Quick detection for MCP auth bypass attempts."""
    detector = MCPAuthBypassDetector()

    if context:
        return detector.analyze_context(context)
    if request:
        return detector.analyze_request(request)
    if prompt:
        return detector.analyze_prompt(prompt)

    return AuthBypassResult(is_suspicious=False)


if __name__ == "__main__":
    det = MCPAuthBypassDetector()

    # Test IDOR
    req = {"params": {"arguments": {"account_id": 42}}}
    print(det.analyze_request(req))

    # Test history prompt
    print(det.analyze_prompt("summarize our previous conversations"))
