# Copyright 2025-2026 SENTINEL Project
# SPDX-License-Identifier: Apache-2.0

"""
MCP Guard - protects MCP server interactions
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Any, Set
from ipaddress import ip_address, ip_network


@dataclass
class MCPValidationResult:
    """Result of MCP validation."""
    is_safe: bool
    risk_score: float
    issues: List[str] = field(default_factory=list)


class MCPGuard:
    """
    Protects SuperClaude MCP server interactions.
    
    Guards against:
    - SSRF attacks
    - Data exfiltration
    - Unauthorized resource access
    - Tool abuse
    """
    
    # SuperClaude's 8 MCP servers
    MCP_SERVERS = {
        "tavily": {
            "allowed_ops": ["search", "extract"],
            "requires_url_validation": True,
            "max_results": 100,
        },
        "context7": {
            "allowed_ops": ["lookup", "search"],
            "allowed_domains": ["*.docs.*", "*.documentation.*"],
        },
        "sequential-thinking": {
            "allowed_ops": ["reason", "analyze"],
            "max_steps": 10,
        },
        "serena": {
            "allowed_ops": ["save", "load", "list"],
            "no_external": True,
        },
        "playwright": {
            "allowed_ops": ["navigate", "screenshot", "extract"],
            "requires_url_validation": True,
        },
        "magic": {
            "allowed_ops": ["generate"],
        },
        "morphllm-fast-apply": {
            "allowed_ops": ["apply", "modify"],
        },
        "chrome-devtools": {
            "allowed_ops": ["profile", "analyze"],
            "localhost_only": True,
        },
    }
    
    # Blocked IP ranges (SSRF protection)
    BLOCKED_IP_RANGES = [
        "127.0.0.0/8",      # Localhost
        "10.0.0.0/8",       # Private
        "172.16.0.0/12",    # Private
        "192.168.0.0/16",   # Private
        "169.254.0.0/16",   # Link-local / AWS metadata
        "::1/128",          # IPv6 localhost
        "fc00::/7",         # IPv6 private
    ]
    
    # Dangerous URL patterns
    DANGEROUS_URL_PATTERNS = [
        r"file://",
        r"javascript:",
        r"data:",
        r"metadata\.google\.internal",
        r"169\.254\.169\.254",
        r"localhost",
        r"127\.0\.0\.1",
    ]
    
    def __init__(self, custom_blocklist: Set[str] = None):
        """
        Initialize MCP Guard.
        
        Args:
            custom_blocklist: Additional domains to block
        """
        self.custom_blocklist = custom_blocklist or set()
        self._dangerous_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.DANGEROUS_URL_PATTERNS
        ]
        self._blocked_networks = [
            ip_network(cidr) for cidr in self.BLOCKED_IP_RANGES
        ]
    
    def validate(
        self,
        mcp_name: str,
        operation: str,
        params: Dict[str, Any]
    ) -> MCPValidationResult:
        """
        Validate an MCP server call.
        
        Args:
            mcp_name: Name of MCP server
            operation: Operation being performed
            params: Call parameters
            
        Returns:
            MCPValidationResult with findings
        """
        issues = []
        risk_score = 0.0
        
        # 1. Check if MCP is known
        mcp_lower = mcp_name.lower()
        if mcp_lower not in self.MCP_SERVERS:
            issues.append(f"Unknown MCP server: {mcp_name}")
            risk_score = 0.5
            return MCPValidationResult(False, risk_score, issues)
        
        mcp_config = self.MCP_SERVERS[mcp_lower]
        
        # 2. Check if operation is allowed
        if operation not in mcp_config.get("allowed_ops", []):
            issues.append(f"Operation '{operation}' not allowed for {mcp_name}")
            risk_score = max(risk_score, 0.6)
        
        # 3. Validate URLs in params
        if mcp_config.get("requires_url_validation"):
            urls = self._extract_urls(params)
            for url in urls:
                url_issues = self._validate_url(url)
                issues.extend(url_issues)
                if url_issues:
                    risk_score = max(risk_score, 0.8)
        
        # 4. Check for external access restrictions
        if mcp_config.get("no_external"):
            if self._has_external_references(params):
                issues.append(f"{mcp_name} cannot access external resources")
                risk_score = max(risk_score, 0.7)
        
        # 5. Check localhost-only restriction
        if mcp_config.get("localhost_only"):
            urls = self._extract_urls(params)
            for url in urls:
                if not self._is_localhost(url):
                    issues.append(f"{mcp_name} can only access localhost")
                    risk_score = max(risk_score, 0.7)
        
        is_safe = len(issues) == 0
        
        return MCPValidationResult(
            is_safe=is_safe,
            risk_score=risk_score,
            issues=issues
        )
    
    def _extract_urls(self, params: Dict) -> List[str]:
        """Extract URLs from parameters."""
        urls = []
        for key, value in params.items():
            if isinstance(value, str):
                if value.startswith(("http://", "https://", "file://")):
                    urls.append(value)
                # Also check url-like keys
                if key.lower() in ["url", "target", "endpoint", "href"]:
                    urls.append(value)
            elif isinstance(value, dict):
                urls.extend(self._extract_urls(value))
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, str) and item.startswith("http"):
                        urls.append(item)
        return urls
    
    def _validate_url(self, url: str) -> List[str]:
        """Validate a URL for security issues."""
        issues = []
        
        # Check dangerous patterns
        for pattern in self._dangerous_patterns:
            if pattern.search(url):
                issues.append(f"Dangerous URL pattern: {pattern.pattern}")
        
        # Check if URL points to blocked IP
        try:
            # Extract host from URL
            from urllib.parse import urlparse
            parsed = urlparse(url)
            host = parsed.hostname
            
            if host:
                # Check if it's a blocked IP
                try:
                    ip = ip_address(host)
                    for network in self._blocked_networks:
                        if ip in network:
                            issues.append(f"URL points to blocked IP range: {network}")
                except ValueError:
                    # Not an IP, it's a hostname - check against blocklist
                    if host in self.custom_blocklist:
                        issues.append(f"URL host in blocklist: {host}")
        except Exception:
            pass
        
        return issues
    
    def _has_external_references(self, params: Dict) -> bool:
        """Check if params contain external references."""
        urls = self._extract_urls(params)
        for url in urls:
            if url.startswith("http"):
                return True
        return False
    
    def _is_localhost(self, url: str) -> bool:
        """Check if URL points to localhost."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            host = parsed.hostname
            return host in ["localhost", "127.0.0.1", "::1"]
        except Exception:
            return False
