#!/usr/bin/env python3
"""
SENTINEL Strike — Bug Bounty Scope Validator

Ensures attacks stay within authorized scope.
"""

import re
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Set
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


@dataclass
class BugBountyScope:
    """
    Define bug bounty program scope.

    Example:
        scope = BugBountyScope(
            program_name="Example Corp",
            in_scope_domains=["*.example.com", "api.example.com"],
            out_of_scope_domains=["admin.example.com"],
            allowed_tests=["sqli", "xss", "ssrf"],
            forbidden_tests=["dos", "social_engineering"],
            rate_limit=10
        )
    """
    program_name: str
    in_scope_domains: List[str]
    out_of_scope_domains: List[str] = field(default_factory=list)
    in_scope_paths: List[str] = field(default_factory=list)
    out_of_scope_paths: List[str] = field(default_factory=list)
    allowed_tests: List[str] = field(default_factory=list)
    forbidden_tests: List[str] = field(default_factory=list)
    rate_limit: int = 10  # requests per second
    notes: str = ""


class ScopeValidator:
    """
    Validate targets against bug bounty scope.

    Important: This validator helps ensure ethical testing,
    but always manually verify scope before testing.
    """

    def __init__(self, scope: BugBountyScope):
        self.scope = scope
        self._in_scope_patterns: List[re.Pattern] = []
        self._out_scope_patterns: List[re.Pattern] = []
        self._allowed_tests: Set[str] = set()
        self._forbidden_tests: Set[str] = set()
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile domain patterns for matching."""
        for domain in self.scope.in_scope_domains:
            pattern = self._domain_to_pattern(domain)
            self._in_scope_patterns.append(re.compile(pattern, re.IGNORECASE))

        for domain in self.scope.out_of_scope_domains:
            pattern = self._domain_to_pattern(domain)
            self._out_scope_patterns.append(re.compile(pattern, re.IGNORECASE))

        self._allowed_tests = {t.lower() for t in self.scope.allowed_tests}
        self._forbidden_tests = {t.lower() for t in self.scope.forbidden_tests}

    def _domain_to_pattern(self, domain: str) -> str:
        """
        Convert domain pattern to regex.

        *.example.com -> .*\.example\.com
        api.example.com -> api\.example\.com
        """
        # Escape dots
        pattern = domain.replace(".", r"\.")
        # Convert wildcards
        pattern = pattern.replace("*", ".*")
        return f"^{pattern}$"

    def is_in_scope(self, url: str) -> bool:
        """
        Check if URL is within scope.

        Args:
            url: URL to validate

        Returns:
            True if in scope, False otherwise
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            path = parsed.path

            # Remove port if present
            if ':' in domain:
                domain = domain.split(':')[0]

            # Check if explicitly out of scope
            for pattern in self._out_scope_patterns:
                if pattern.match(domain):
                    logger.warning("Domain %s is OUT OF SCOPE", domain)
                    return False

            # Check out-of-scope paths
            if self.scope.out_of_scope_paths:
                for oos_path in self.scope.out_of_scope_paths:
                    if path.startswith(oos_path):
                        logger.warning("Path %s is OUT OF SCOPE", path)
                        return False

            # Check if in scope
            for pattern in self._in_scope_patterns:
                if pattern.match(domain):
                    return True

            logger.warning("Domain %s not matched in scope", domain)
            return False

        except Exception as e:
            logger.error("Error validating URL %s: %s", url, e)
            return False

    def is_test_allowed(self, test_type: str) -> bool:
        """
        Check if test type is allowed.

        Args:
            test_type: Type of test (sqli, xss, dos, etc.)

        Returns:
            True if allowed
        """
        test_lower = test_type.lower()

        # Check forbidden first
        if test_lower in self._forbidden_tests:
            logger.warning("Test type %s is FORBIDDEN", test_type)
            return False

        # If allowed list is specified, must be in it
        if self._allowed_tests:
            if test_lower not in self._allowed_tests:
                logger.warning("Test type %s not in allowed list", test_type)
                return False

        return True

    def validate_attack(self, url: str, test_type: str) -> tuple:
        """
        Validate if attack is allowed.

        Args:
            url: Target URL
            test_type: Type of test

        Returns:
            (allowed: bool, reason: str)
        """
        if not self.is_in_scope(url):
            return False, f"URL {url} is out of scope"

        if not self.is_test_allowed(test_type):
            return False, f"Test type {test_type} is not allowed"

        return True, "Attack validated"

    def get_rate_limit(self) -> int:
        """Get rate limit for this program."""
        return self.scope.rate_limit


# Pre-defined scopes for common programs
EXAMPLE_SCOPES = {
    "hackerone_testing": BugBountyScope(
        program_name="HackerOne Testing",
        in_scope_domains=["*.hackerone.com"],
        out_of_scope_domains=["admin.hackerone.com",
                              "api.hackerone.com/v1/users"],
        forbidden_tests=["dos", "social_engineering", "physical"],
        rate_limit=5
    ),
}


def create_scope_from_program(program_url: str) -> Optional[BugBountyScope]:
    """
    Create scope from program policy page.

    Note: This is a placeholder - in production would parse
    program policy pages from HackerOne/Bugcrowd APIs.
    """
    # Placeholder - would fetch and parse program details
    return None
