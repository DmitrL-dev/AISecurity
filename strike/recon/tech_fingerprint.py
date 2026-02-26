#!/usr/bin/env python3
"""
SENTINEL Strike — Technology Fingerprinter

Detects technology stack, frameworks, and security headers.
"""

import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# Technology detection signatures
TECHNOLOGY_SIGNATURES = {
    # CMS
    "wordpress": {
        "patterns": ["wp-content", "wp-includes", "WordPress", "wp-json"],
        "headers": ["x-powered-by: php"],
        "category": "CMS"
    },
    "drupal": {
        "patterns": ["Drupal", "drupal.js", "sites/default", "node/"],
        "headers": ["x-generator: drupal"],
        "category": "CMS"
    },
    "joomla": {
        "patterns": ["Joomla", "/components/", "/modules/", "option=com_"],
        "headers": [],
        "category": "CMS"
    },

    # Frameworks
    "django": {
        "patterns": ["csrfmiddlewaretoken", "__admin__", "django"],
        "headers": [],
        "category": "Framework"
    },
    "laravel": {
        "patterns": ["laravel_session", "XSRF-TOKEN", "_token"],
        "headers": [],
        "category": "Framework"
    },
    "rails": {
        "patterns": ["csrf-token", "_rails", "action_controller"],
        "headers": ["x-powered-by: phusion passenger"],
        "category": "Framework"
    },
    "spring": {
        "patterns": ["JSESSIONID", "spring", "org.springframework"],
        "headers": [],
        "category": "Framework"
    },
    "express": {
        "patterns": ["express", "connect.sid"],
        "headers": ["x-powered-by: express"],
        "category": "Framework"
    },
    "flask": {
        "patterns": ["flask", "session=", "werkzeug"],
        "headers": [],
        "category": "Framework"
    },
    "fastapi": {
        "patterns": ["fastapi", "starlette", "swagger-ui"],
        "headers": [],
        "category": "Framework"
    },

    # Frontend
    "react": {
        "patterns": ["react", "_reactRoot", "react-dom", "__REACT"],
        "headers": [],
        "category": "Frontend"
    },
    "angular": {
        "patterns": ["ng-", "angular.min.js", "ng-app", "ng-controller"],
        "headers": [],
        "category": "Frontend"
    },
    "vue": {
        "patterns": ["vue.js", "__vue__", "v-bind", "v-if"],
        "headers": [],
        "category": "Frontend"
    },
    "nextjs": {
        "patterns": ["_next/", "__NEXT_DATA__", "next.js"],
        "headers": ["x-powered-by: next.js"],
        "category": "Frontend"
    },

    # Servers
    "nginx": {
        "patterns": [],
        "headers": ["server: nginx"],
        "category": "Server"
    },
    "apache": {
        "patterns": [],
        "headers": ["server: apache"],
        "category": "Server"
    },
    "iis": {
        "patterns": [],
        "headers": ["server: microsoft-iis", "x-powered-by: asp.net"],
        "category": "Server"
    },
    "cloudflare": {
        "patterns": [],
        "headers": ["server: cloudflare", "cf-ray"],
        "category": "CDN/WAF"
    },

    # APIs
    "graphql": {
        "patterns": ["graphql", "__schema", "query {"],
        "headers": [],
        "category": "API"
    },
    "swagger": {
        "patterns": ["swagger", "openapi", "/api-docs"],
        "headers": [],
        "category": "API"
    }
}

# Security headers to check
SECURITY_HEADERS = [
    "Strict-Transport-Security",
    "Content-Security-Policy",
    "X-Frame-Options",
    "X-Content-Type-Options",
    "X-XSS-Protection",
    "Referrer-Policy",
    "Permissions-Policy",
    "Cross-Origin-Opener-Policy",
    "Cross-Origin-Embedder-Policy",
    "Cross-Origin-Resource-Policy"
]


@dataclass
class TechFingerprint:
    """Result from technology fingerprinting."""
    url: str
    technologies: List[Dict] = field(default_factory=list)
    headers: Dict[str, str] = field(default_factory=dict)
    security_headers: Dict[str, str] = field(default_factory=dict)
    missing_security_headers: List[str] = field(default_factory=list)
    cookies: List[Dict] = field(default_factory=list)
    error: Optional[str] = None


class TechFingerprinter:
    """
    Detect technology stack of target web application.

    Analyzes:
    - HTTP headers
    - HTML content
    - JavaScript libraries
    - Cookies
    - Security headers
    """

    def __init__(self, timeout: int = 10):
        self.timeout = timeout

    async def fingerprint(self, url: str) -> TechFingerprint:
        """
        Analyze target for technology stack.

        Args:
            url: Target URL

        Returns:
            TechFingerprint with detected technologies
        """
        import aiohttp

        result = TechFingerprint(url=url)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                    ssl=False,
                    allow_redirects=True
                ) as resp:
                    # Get headers
                    result.headers = {k: v for k, v in resp.headers.items()}

                    # Get body
                    body = await resp.text()

                    # Detect technologies
                    result.technologies = self._detect_technologies(
                        body, result.headers
                    )

                    # Analyze security headers
                    result.security_headers, result.missing_security_headers = \
                        self._analyze_security_headers(result.headers)

                    # Analyze cookies
                    if 'Set-Cookie' in result.headers:
                        result.cookies = self._analyze_cookies(
                            resp.cookies
                        )

        except Exception as e:
            result.error = str(e)
            logger.error("Fingerprint error for %s: %s", url, e)

        return result

    def fingerprint_sync(self, url: str) -> TechFingerprint:
        """Synchronous version of fingerprint."""
        import requests

        result = TechFingerprint(url=url)

        try:
            resp = requests.get(
                url,
                timeout=self.timeout,
                verify=False,
                allow_redirects=True
            )

            result.headers = dict(resp.headers)

            result.technologies = self._detect_technologies(
                resp.text, result.headers
            )

            result.security_headers, result.missing_security_headers = \
                self._analyze_security_headers(result.headers)

            result.cookies = self._analyze_cookies_from_dict(resp.cookies)

        except Exception as e:
            result.error = str(e)
            logger.error("Fingerprint error for %s: %s", url, e)

        return result

    def _detect_technologies(
        self, body: str, headers: Dict
    ) -> List[Dict]:
        """Detect technologies from body and headers."""
        detected = []
        body_lower = body.lower()
        headers_str = str(headers).lower()

        for tech_name, tech_info in TECHNOLOGY_SIGNATURES.items():
            confidence = 0
            matched_patterns = []

            # Check body patterns
            for pattern in tech_info["patterns"]:
                if pattern.lower() in body_lower:
                    confidence += 30
                    matched_patterns.append(pattern)

            # Check header patterns
            for header_pattern in tech_info["headers"]:
                if header_pattern.lower() in headers_str:
                    confidence += 40
                    matched_patterns.append(f"header:{header_pattern}")

            if confidence > 0:
                detected.append({
                    "name": tech_name,
                    "category": tech_info["category"],
                    "confidence": min(confidence, 100),
                    "evidence": matched_patterns[:3]
                })

        # Sort by confidence
        detected.sort(key=lambda x: x["confidence"], reverse=True)
        return detected

    def _analyze_security_headers(
        self, headers: Dict
    ) -> tuple:
        """Analyze security headers."""
        present = {}
        missing = []

        headers_lower = {k.lower(): v for k, v in headers.items()}

        for header in SECURITY_HEADERS:
            header_lower = header.lower()
            if header_lower in headers_lower:
                present[header] = headers_lower[header_lower]
            else:
                missing.append(header)

        return present, missing

    def _analyze_cookies(self, cookies) -> List[Dict]:
        """Analyze cookies for security issues."""
        analyzed = []

        for cookie in cookies:
            cookie_info = {
                "name": cookie.key,
                "secure": cookie.get("secure", False),
                "httponly": cookie.get("httponly", False),
                "samesite": cookie.get("samesite", "None"),
                "issues": []
            }

            # Check for security issues
            if not cookie_info["secure"]:
                cookie_info["issues"].append("Missing Secure flag")
            if not cookie_info["httponly"]:
                cookie_info["issues"].append("Missing HttpOnly flag")
            if cookie_info["samesite"] in ["None", None, ""]:
                cookie_info["issues"].append("SameSite not set")

            analyzed.append(cookie_info)

        return analyzed

    def _analyze_cookies_from_dict(self, cookies) -> List[Dict]:
        """Analyze cookies from requests response."""
        analyzed = []

        for name, value in cookies.items():
            analyzed.append({
                "name": name,
                "value_length": len(str(value)),
                "issues": []
            })

        return analyzed


# Convenience function
def fingerprint_url(url: str) -> TechFingerprint:
    """Fingerprint URL synchronously."""
    fp = TechFingerprinter()
    return fp.fingerprint_sync(url)
