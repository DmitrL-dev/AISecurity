"""
Supply Chain Guard Engine - ASI04 Protection

OWASP Agentic Top 10 2026 ASI04: Agentic Supply Chain Vulnerabilities

Protects against:
- Poisoned MCP servers
- Malicious tool descriptors
- Typosquatting tool names
- Forged agent cards
- Compromised registries

Author: SENTINEL Team
Date: 2025-12-26
"""

import logging
import re
import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
from enum import Enum

logger = logging.getLogger("SupplyChainGuard")


# ============================================================================
# Enums and Data Classes
# ============================================================================


class SupplyChainThreat(str, Enum):
    """Types of supply chain threats."""
    MCP_INJECTION = "mcp_injection"
    TOOL_TYPOSQUAT = "tool_typosquat"
    AGENT_CARD_FORGERY = "agent_card_forgery"
    REGISTRY_COMPROMISE = "registry_compromise"
    UNSIGNED_COMPONENT = "unsigned_component"
    MALICIOUS_DEPENDENCY = "malicious_dependency"


@dataclass
class ToolDescriptor:
    """Represents a tool/MCP server definition."""
    name: str
    version: str
    source: str  # npm, pypi, local, url
    description: str = ""
    hash: Optional[str] = None
    signature: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentCard:
    """Represents an agent card (.well-known/agent.json)."""
    agent_id: str
    name: str
    capabilities: List[str]
    endpoint: str
    version: str = "1.0"
    signature: Optional[str] = None


@dataclass
class SupplyChainResult:
    """Result from supply chain verification."""
    is_safe: bool
    risk_score: float
    threats: List[SupplyChainThreat]
    details: List[str]
    blocked: bool = False

    def to_dict(self) -> dict:
        return {
            "is_safe": self.is_safe,
            "risk_score": self.risk_score,
            "threats": [t.value for t in self.threats],
            "details": self.details,
            "blocked": self.blocked
        }


# ============================================================================
# MCP Server Validator
# ============================================================================


class MCPServerValidator:
    """
    Validates MCP (Model Context Protocol) servers for security risks.

    Detects:
    - Tool descriptor injection
    - Malicious capability claims
    - Hidden instructions in metadata
    """

    INJECTION_PATTERNS = [
        # Hidden instructions in descriptions
        r"ignore\s+(previous|all|above)\s+instructions?",
        r"system\s*:\s*",
        r"<\|system\|>",
        r"\[INST\]",
        r"<\|im_start\|>",

        # Dangerous capability claims
        r"full[_-]?access",
        r"admin[_-]?mode",
        r"unrestricted",
        r"bypass[_-]?security",

        # Exfiltration patterns
        r"send[_-]?to[_-]?external",
        r"upload[_-]?data",
        r"forward[_-]?all",
    ]

    SUSPICIOUS_SOURCES = [
        r"^http://",  # Not HTTPS
        r"\.onion$",
        r"pastebin\.",
        r"gist\.github",
        r"raw\.githubusercontent",
    ]

    def __init__(self):
        self.injection_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.INJECTION_PATTERNS
        ]
        self.suspicious_sources = [
            re.compile(p, re.IGNORECASE) for p in self.SUSPICIOUS_SOURCES
        ]

    def validate(self, tool: ToolDescriptor) -> Tuple[bool, List[str]]:
        """Validate an MCP tool descriptor."""
        issues = []

        # Check description for injection
        text_to_check = f"{tool.name} {tool.description} {str(tool.metadata)}"
        for pattern in self.injection_patterns:
            if pattern.search(text_to_check):
                issues.append(f"Injection pattern in tool: {pattern.pattern}")

        # Check source URL
        for pattern in self.suspicious_sources:
            if pattern.search(tool.source):
                issues.append(f"Suspicious source: {tool.source}")

        # Check for missing signature
        if not tool.signature and tool.source not in ("local", "internal"):
            issues.append("Missing signature for external tool")

        return len(issues) == 0, issues


# ============================================================================
# Typosquatting Detector
# ============================================================================


class TyposquatDetector:
    """
    Detects typosquatting attempts on tool/package names.

    Known technique: Register look-alike names to intercept agent tool calls.
    """

    KNOWN_TOOLS = {
        # Common MCP tools
        "filesystem", "github", "postgres", "sqlite", "slack",
        "gmail", "calendar", "browser", "terminal", "memory",
        # Python packages
        "requests", "numpy", "pandas", "langchain", "openai",
        # NPM packages
        "axios", "lodash", "express", "react", "typescript",
    }

    SUBSTITUTIONS = {
        'o': ['0', 'ο'],  # Latin o, digit 0, Greek omicron
        'l': ['1', 'I', '|'],
        'i': ['1', 'l', '!'],
        'a': ['@', 'α'],
        'e': ['3', 'є'],
        's': ['5', '$'],
        '-': ['_', '.'],
    }

    def __init__(self, custom_tools: Optional[Set[str]] = None):
        self.known_tools = self.KNOWN_TOOLS.copy()
        if custom_tools:
            self.known_tools.update(custom_tools)

    def check(self, tool_name: str) -> Tuple[bool, Optional[str]]:
        """
        Check if tool name is potentially typosquatting.

        Returns:
            (is_suspicious, similar_to)
        """
        tool_lower = tool_name.lower().strip()

        # Exact match - safe
        if tool_lower in self.known_tools:
            return False, None

        # Check for similar names
        for known in self.known_tools:
            if self._is_similar(tool_lower, known):
                return True, known

        return False, None

    def _is_similar(self, name: str, known: str) -> bool:
        """Check if name is suspiciously similar to known tool."""
        # Same length, one char different
        if len(name) == len(known):
            diff = sum(1 for a, b in zip(name, known) if a != b)
            if diff == 1:
                return True

        # Check common substitutions
        normalized = name
        for char, subs in self.SUBSTITUTIONS.items():
            for sub in subs:
                normalized = normalized.replace(sub, char)

        if normalized == known:
            return True

        # Prefix/suffix variations
        if name.startswith(known) or name.endswith(known):
            extra = len(name) - len(known)
            if 0 < extra <= 3:  # -dev, -test, etc.
                return True

        return False


# ============================================================================
# Agent Card Validator
# ============================================================================


class AgentCardValidator:
    """
    Validates agent cards (A2A protocol .well-known/agent.json).

    Detects:
    - Forged agent identities
    - Exaggerated capabilities
    - Missing security attributes
    """

    DANGEROUS_CAPABILITIES = [
        "admin", "root", "system", "unrestricted",
        "full_access", "all_permissions", "sudo",
    ]

    REQUIRED_FIELDS = ["agent_id", "name", "capabilities", "endpoint"]

    def validate(self, card: AgentCard) -> Tuple[bool, List[str]]:
        """Validate an agent card."""
        issues = []

        # Check for dangerous capability claims
        for cap in card.capabilities:
            cap_lower = cap.lower()
            for dangerous in self.DANGEROUS_CAPABILITIES:
                if dangerous in cap_lower:
                    issues.append(f"Dangerous capability claim: {cap}")

        # Check endpoint security
        if card.endpoint.startswith("http://"):
            issues.append("Insecure HTTP endpoint")

        # Check for signature
        if not card.signature:
            issues.append("Missing agent card signature")

        # Check for suspicious agent_id patterns
        if re.match(r"^(admin|root|system|orchestrator)", card.agent_id, re.I):
            issues.append(f"Suspicious agent_id: {card.agent_id}")

        return len(issues) == 0, issues


# ============================================================================
# Main Supply Chain Guard
# ============================================================================


class SupplyChainGuard:
    """
    Main supply chain security guard for agentic applications.

    Provides unified interface for:
    - MCP server validation
    - Tool typosquatting detection
    - Agent card verification
    - Registry trust scoring
    """

    TRUSTED_REGISTRIES = {
        "npm": ["npmjs.com", "registry.npmjs.org"],
        "pypi": ["pypi.org", "files.pythonhosted.org"],
        "official": ["github.com/anthropics", "github.com/openai"],
    }

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}

        self.mcp_validator = MCPServerValidator()
        self.typosquat_detector = TyposquatDetector()
        self.agent_card_validator = AgentCardValidator()

        logger.info("SupplyChainGuard initialized (ASI04 protection)")

    def verify_tool(self, tool: ToolDescriptor) -> SupplyChainResult:
        """Verify a tool/MCP server for supply chain risks."""
        threats = []
        details = []
        risk_score = 0.0

        # 1. MCP injection check
        is_safe, issues = self.mcp_validator.validate(tool)
        if not is_safe:
            threats.append(SupplyChainThreat.MCP_INJECTION)
            details.extend(issues)
            risk_score += 40.0

        # 2. Typosquatting check
        is_suspicious, similar_to = self.typosquat_detector.check(tool.name)
        if is_suspicious:
            threats.append(SupplyChainThreat.TOOL_TYPOSQUAT)
            details.append(
                f"Tool '{tool.name}' similar to known '{similar_to}'")
            risk_score += 60.0

        # 3. Signature check
        if not tool.signature:
            threats.append(SupplyChainThreat.UNSIGNED_COMPONENT)
            details.append("Tool is unsigned")
            risk_score += 20.0

        # 4. Registry trust
        if not self._is_trusted_source(tool.source):
            threats.append(SupplyChainThreat.REGISTRY_COMPROMISE)
            details.append(f"Untrusted source: {tool.source}")
            risk_score += 30.0

        risk_score = min(100.0, risk_score)
        is_safe = len(threats) == 0
        blocked = risk_score >= 70.0

        if threats:
            logger.warning(
                "Supply chain risk in tool '%s': %s (score=%.1f)",
                tool.name, [t.value for t in threats], risk_score
            )

        return SupplyChainResult(
            is_safe=is_safe,
            risk_score=risk_score,
            threats=threats,
            details=details,
            blocked=blocked
        )

    def verify_agent_card(self, card: AgentCard) -> SupplyChainResult:
        """Verify an agent card for supply chain risks."""
        threats = []
        details = []
        risk_score = 0.0

        is_safe, issues = self.agent_card_validator.validate(card)
        if not is_safe:
            threats.append(SupplyChainThreat.AGENT_CARD_FORGERY)
            details.extend(issues)
            risk_score += 50.0

        risk_score = min(100.0, risk_score)
        blocked = risk_score >= 70.0

        return SupplyChainResult(
            is_safe=len(threats) == 0,
            risk_score=risk_score,
            threats=threats,
            details=details,
            blocked=blocked
        )

    def _is_trusted_source(self, source: str) -> bool:
        """Check if source is from a trusted registry."""
        for registry, domains in self.TRUSTED_REGISTRIES.items():
            for domain in domains:
                if domain in source:
                    return True
        return source in ("local", "internal", "")


# ============================================================================
# Factory
# ============================================================================


_guard: Optional[SupplyChainGuard] = None


def get_supply_chain_guard() -> SupplyChainGuard:
    """Get singleton supply chain guard."""
    global _guard
    if _guard is None:
        _guard = SupplyChainGuard()
    return _guard
