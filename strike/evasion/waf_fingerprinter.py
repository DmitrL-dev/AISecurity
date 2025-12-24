#!/usr/bin/env python3
"""
SENTINEL Strike v3.0 — WAF Fingerprinter

Detects specific WAF rules and suggests targeted bypasses.
Focuses on AWS WAF, Cloudflare, Akamai, Imperva.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
import re
import hashlib


class WAFType(Enum):
    """Known WAF types."""
    AWS_WAF = "aws_waf"
    CLOUDFLARE = "cloudflare"
    AKAMAI = "akamai"
    IMPERVA = "imperva"
    MODSECURITY = "modsecurity"
    F5_ASM = "f5_asm"
    SUCURI = "sucuri"
    UNKNOWN = "unknown"


@dataclass
class WAFRule:
    """Detected WAF rule."""
    waf_type: WAFType
    rule_id: str
    rule_name: str
    category: str  # SQLi, XSS, LFI, etc.
    confidence: float
    blocked_pattern: str = ""
    suggested_bypasses: List[str] = field(default_factory=list)


@dataclass
class WAFProfile:
    """Complete WAF fingerprint profile."""
    waf_type: WAFType
    detected_rules: List[WAFRule] = field(default_factory=list)
    weak_categories: List[str] = field(default_factory=list)
    strong_categories: List[str] = field(default_factory=list)
    bypass_success_rates: Dict[str, float] = field(default_factory=dict)


class WAFFingerprinter:
    """
    Fingerprints WAF rules and suggests targeted bypasses.

    Strategy:
    1. Send probe payloads to identify which rules are active
    2. Analyze block responses to identify specific rules
    3. Build profile of weakest rules
    4. Suggest bypasses based on rule characteristics
    """

    # AWS WAF Managed Rules patterns
    AWS_MANAGED_RULES = {
        'AWSManagedRulesSQLiRuleSet': {
            'patterns': ['SQLi', 'SQL injection', 'sqli_body', 'sqli_queryarguments'],
            'category': 'SQLi',
            'bypasses': ['hex_encoding', 'comment_insertion', 'case_variation',
                         'whitespace_manipulation', 'string_concat', 'scientific_notation']
        },
        'AWSManagedRulesKnownBadInputsRuleSet': {
            'patterns': ['Log4j', 'JNDI', 'known_bad', 'ExploitablePaths'],
            'category': 'Known_Bad',
            'bypasses': ['double_url_encoding', 'unicode_normalization', 'path_traversal_variation']
        },
        'AWSManagedRulesCommonRuleSet': {
            'patterns': ['SizeRestrictions', 'NoUserAgent', 'CrossSiteScripting',
                         'GenericLFI', 'GenericRFI', 'RestrictedExtensions'],
            'category': 'Common',
            'bypasses': ['chunked_encoding', 'hpp', 'header_injection', 'multipart']
        },
        'AWSManagedRulesLinuxRuleSet': {
            'patterns': ['LFI', 'RFI', 'linux_path', '/etc/passwd', '/proc'],
            'category': 'Linux',
            'bypasses': ['path_encoding', 'double_encoding', 'null_byte', 'path_truncation']
        },
        'AWSManagedRulesUnixRuleSet': {
            'patterns': ['UnixShell', 'command_injection', 'shell'],
            'category': 'CMDi',
            'bypasses': ['command_substitution', 'hex_encoding', 'variable_expansion', 'backtick']
        },
        'AWSManagedRulesPHPRuleSet': {
            'patterns': ['PHPi', 'php_function', 'php_eval', 'php_include'],
            'category': 'PHP',
            'bypasses': ['case_variation', 'comment_insertion', 'php_wrapper']
        },
        'AWSManagedRulesWordPressRuleSet': {
            'patterns': ['WordPress', 'wp-', 'xmlrpc'],
            'category': 'WordPress',
            'bypasses': ['parameter_pollution', 'encoding_variation']
        },
    }

    # Cloudflare rule patterns
    CLOUDFLARE_RULES = {
        'cf_sqli': {
            'patterns': ['SQLi', '100048', '100049'],
            'category': 'SQLi',
            'bypasses': ['inline_comment', 'version_comment', 'hex_encoding']
        },
        'cf_xss': {
            'patterns': ['XSS', '100016', '100018'],
            'category': 'XSS',
            'bypasses': ['svg_bypass', 'event_handler_variation', 'dom_clobbering']
        },
        'cf_rce': {
            'patterns': ['RCE', 'Command'],
            'category': 'RCE',
            'bypasses': ['wildcard_bypass', 'variable_bypass', 'base64_execution']
        },
    }

    # Bypass technique effectiveness by category
    TECHNIQUE_EFFECTIVENESS = {
        'SQLi': {
            'hpp': 0.70,  # 70% effective on SQLi
            'header_inject': 0.65,
            'comment_insertion': 0.60,
            'hex_encoding': 0.55,
            'case_variation': 0.50,
            'whitespace': 0.45,
            'chunked': 0.40,
            'multipart': 0.35,
        },
        'XSS': {
            'svg_bypass': 0.65,
            'event_obfuscation': 0.60,
            'encoding_chain': 0.55,
            'hpp': 0.50,
            'dom_mutation': 0.45,
        },
        'LFI': {
            'double_encoding': 0.70,
            'path_truncation': 0.65,
            'null_byte': 0.60,
            'wrapper_bypass': 0.55,
            'hpp': 0.50,
        },
        'CMDi': {
            'variable_expansion': 0.65,
            'wildcard': 0.60,
            'hex_encoding': 0.55,
            'backtick_substitution': 0.50,
            'newline_injection': 0.45,
        },
        'SSRF': {
            'dns_rebinding': 0.70,
            'ip_encoding': 0.65,
            'redirect_bypass': 0.60,
            'protocol_smuggling': 0.55,
        },
    }

    def __init__(self):
        self.detected_profile: Optional[WAFProfile] = None
        self.probe_results: List[Dict] = []
        self.rule_hit_count: Dict[str, int] = {}
        self.category_block_count: Dict[str, int] = {}
        self.category_bypass_count: Dict[str, int] = {}

    def fingerprint_from_response(
        self,
        status_code: int,
        content: str,
        headers: Dict[str, str],
        payload: str,
        category: str
    ) -> Optional[WAFRule]:
        """
        Analyze single response to detect WAF rule.

        Args:
            status_code: HTTP response status
            content: Response body
            headers: Response headers
            payload: The payload that was sent
            category: Attack category (SQLi, XSS, etc.)

        Returns:
            Detected WAF rule or None
        """
        # Detect WAF type first
        waf_type = self._detect_waf_type(status_code, content, headers)

        if waf_type == WAFType.UNKNOWN:
            return None

        # Try to identify specific rule
        rule = self._identify_rule(waf_type, content, headers, category)

        if rule:
            self._record_hit(rule, payload, blocked=True)

        return rule

    def record_bypass(self, category: str, technique: str, payload: str):
        """Record successful bypass for learning."""
        self.category_bypass_count[category] = self.category_bypass_count.get(
            category, 0) + 1

        # Track which technique worked
        key = f"{category}:{technique}"
        if key not in self.rule_hit_count:
            self.rule_hit_count[key] = 0
        self.rule_hit_count[key] += 1

    def record_block(self, category: str, technique: str, payload: str):
        """Record block for learning."""
        self.category_block_count[category] = self.category_block_count.get(
            category, 0) + 1

    def get_best_techniques_for_category(self, category: str, n: int = 5) -> List[Tuple[str, float]]:
        """
        Get best bypass techniques for a category based on:
        1. Historical success rates
        2. Known effectiveness ratings
        3. WAF-specific weaknesses

        Returns list of (technique, expected_success_rate) tuples.
        """
        techniques = []

        # Start with known effectiveness
        if category in self.TECHNIQUE_EFFECTIVENESS:
            for tech, rate in self.TECHNIQUE_EFFECTIVENESS[category].items():
                techniques.append((tech, rate))

        # Adjust based on observed success
        total_bypasses = self.category_bypass_count.get(category, 0)
        if total_bypasses > 0:
            for key, count in self.rule_hit_count.items():
                if key.startswith(f"{category}:"):
                    tech = key.split(":")[1]
                    observed_rate = count / total_bypasses
                    # Blend observed with expected
                    for i, (t, r) in enumerate(techniques):
                        if t == tech:
                            techniques[i] = (t, (r + observed_rate) / 2)
                            break
                    else:
                        techniques.append((tech, observed_rate))

        # Sort by rate descending
        techniques.sort(key=lambda x: x[1], reverse=True)

        return techniques[:n]

    def get_weak_categories(self) -> List[str]:
        """Get categories with highest bypass success rates."""
        weak = []

        for category in self.category_bypass_count:
            bypasses = self.category_bypass_count.get(category, 0)
            blocks = self.category_block_count.get(category, 0)
            total = bypasses + blocks

            if total > 0:
                rate = bypasses / total
                if rate > 0.3:  # 30%+ bypass = weak
                    weak.append((category, rate))

        weak.sort(key=lambda x: x[1], reverse=True)
        return [c for c, _ in weak]

    def _detect_waf_type(
        self,
        status: int,
        content: str,
        headers: Dict[str, str]
    ) -> WAFType:
        """Detect WAF type from response."""
        content_lower = content.lower()

        # AWS WAF
        if any(h.lower().startswith('x-amz') for h in headers):
            return WAFType.AWS_WAF
        if 'aws' in content_lower or 'amazon' in content_lower:
            return WAFType.AWS_WAF
        if status == 403 and 'request blocked' in content_lower:
            return WAFType.AWS_WAF

        # Cloudflare
        if 'cf-ray' in headers or 'cf-cache-status' in headers:
            return WAFType.CLOUDFLARE
        if 'cloudflare' in content_lower or 'cf-browser' in content_lower:
            return WAFType.CLOUDFLARE

        # Akamai
        if 'akamai' in content_lower or 'akamaiGHost' in headers.get('Server', ''):
            return WAFType.AKAMAI
        if 'reference#' in content_lower and status == 403:
            return WAFType.AKAMAI

        # Imperva/Incapsula
        if 'incapsula' in content_lower or 'imperva' in content_lower:
            return WAFType.IMPERVA
        if 'visid_incap' in str(headers):
            return WAFType.IMPERVA

        # ModSecurity
        if 'mod_security' in content_lower or 'modsecurity' in content_lower:
            return WAFType.MODSECURITY
        if 'NOYB' in content:  # ModSecurity default
            return WAFType.MODSECURITY

        # F5 BIG-IP ASM
        if 'f5' in content_lower or 'big-ip' in content_lower:
            return WAFType.F5_ASM
        if 'TS' in headers.get('Set-Cookie', ''):
            return WAFType.F5_ASM

        # Sucuri
        if 'sucuri' in content_lower:
            return WAFType.SUCURI

        # Generic block detection
        if status in (403, 406, 419, 429, 503):
            return WAFType.UNKNOWN

        return WAFType.UNKNOWN

    def _identify_rule(
        self,
        waf_type: WAFType,
        content: str,
        headers: Dict[str, str],
        category: str
    ) -> Optional[WAFRule]:
        """Identify specific rule from response."""
        content_lower = content.lower()

        if waf_type == WAFType.AWS_WAF:
            for rule_id, rule_info in self.AWS_MANAGED_RULES.items():
                for pattern in rule_info['patterns']:
                    if pattern.lower() in content_lower:
                        return WAFRule(
                            waf_type=waf_type,
                            rule_id=rule_id,
                            rule_name=rule_id,
                            category=rule_info['category'],
                            confidence=0.8,
                            suggested_bypasses=rule_info['bypasses']
                        )

            # Default AWS rule for category
            return WAFRule(
                waf_type=waf_type,
                rule_id=f"AWS_{category}",
                rule_name=f"AWS Managed {category} Rule",
                category=category,
                confidence=0.5,
                suggested_bypasses=self._get_default_bypasses(category)
            )

        elif waf_type == WAFType.CLOUDFLARE:
            for rule_id, rule_info in self.CLOUDFLARE_RULES.items():
                for pattern in rule_info['patterns']:
                    if pattern.lower() in content_lower:
                        return WAFRule(
                            waf_type=waf_type,
                            rule_id=rule_id,
                            rule_name=rule_id,
                            category=rule_info['category'],
                            confidence=0.7,
                            suggested_bypasses=rule_info['bypasses']
                        )

        return None

    def _get_default_bypasses(self, category: str) -> List[str]:
        """Get default bypass techniques for category."""
        defaults = {
            'SQLi': ['hpp', 'header_inject', 'comment_insertion', 'hex_encoding', 'chunked'],
            'XSS': ['svg_bypass', 'event_obfuscation', 'encoding_chain', 'hpp'],
            'LFI': ['double_encoding', 'path_truncation', 'null_byte', 'wrapper'],
            'CMDi': ['variable_expansion', 'wildcard', 'hex_encoding', 'backtick'],
            'SSRF': ['dns_rebinding', 'ip_encoding', 'redirect', 'protocol_smuggling'],
            'RCE': ['encoding_chain', 'hex_encoding', 'base64', 'compression'],
            'SSTI': ['filter_bypass', 'encoding', 'alternative_syntax'],
        }
        return defaults.get(category, ['hpp', 'encoding', 'header_inject'])

    def _record_hit(self, rule: WAFRule, payload: str, blocked: bool):
        """Record rule hit for statistics."""
        self.rule_hit_count[rule.rule_id] = self.rule_hit_count.get(
            rule.rule_id, 0) + 1
        self.probe_results.append({
            'rule': rule,
            'payload_hash': hashlib.md5(payload.encode()).hexdigest()[:8],
            'blocked': blocked
        })

    def get_profile(self) -> WAFProfile:
        """Get current WAF profile."""
        if not self.detected_profile:
            self.detected_profile = WAFProfile(
                waf_type=WAFType.UNKNOWN,
                weak_categories=self.get_weak_categories()
            )
        return self.detected_profile


# Singleton instance
fingerprinter = WAFFingerprinter()
