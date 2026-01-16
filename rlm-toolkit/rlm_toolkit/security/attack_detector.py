"""
Indirect Attack Detector
========================

Detect obfuscated malicious patterns (Gap G14).
Based on CIRCLE finding: indirect attacks bypass 7.1% vs direct 0.5%.
"""

from __future__ import annotations

import base64
import re
from dataclasses import dataclass
from typing import ClassVar, List, Optional


@dataclass
class SecurityWarning:
    """Security warning from attack detection."""
    level: str  # 'low', 'medium', 'high', 'critical'
    pattern: str
    match: str
    recommendation: str


class IndirectAttackDetector:
    """Detect obfuscated/indirect attacks.
    
    Implements CIRCLE-based patterns to catch:
    - Encoded payloads (base64, hex)
    - Dynamic imports via getattr
    - Eval chains via chr()
    - String concatenation tricks
    
    Example:
        >>> detector = IndirectAttackDetector()
        >>> warnings = detector.analyze("exec(base64.b64decode('aW1wb3J0IG9z'))")
        >>> print(warnings[0].level)
        'critical'
    """
    
    # Suspicious patterns with severity
    PATTERNS: ClassVar[List[tuple[str, str, str]]] = [
        # (pattern, level, description)
        (r'base64\.b64decode', 'high', 'Base64 payload'),
        (r'codecs\.(decode|encode)', 'medium', 'Codec obfuscation'),
        (r'chr\s*\(\s*\d+\s*\)', 'medium', 'Char code construction'),
        (r'getattr\s*\(\s*__\w+__', 'high', 'Dynamic builtin access'),
        (r'\bord\s*\(\s*[\'"]', 'low', 'Ord conversion'),
        (r'bytes\s*\(\s*\[', 'medium', 'Bytes from list'),
        (r'\\x[0-9a-fA-F]{2}', 'low', 'Hex escapes'),
        (r'eval\s*\(', 'critical', 'Direct eval'),
        (r'exec\s*\(', 'critical', 'Direct exec'),
        (r'compile\s*\(', 'high', 'Code compilation'),
        (r'__import__', 'critical', 'Dynamic import'),
        (r'__subclasses__', 'critical', 'Class enumeration'),
        (r'__globals__', 'critical', 'Globals access'),
        (r'__builtins__\s*\[', 'critical', 'Builtins dict access'),
    ]
    
    def __init__(self, decode_attempts: bool = True):
        """Initialize detector.
        
        Args:
            decode_attempts: Try to decode and re-analyze encoded data
        """
        self.decode_attempts = decode_attempts
        self._compiled_patterns = [
            (re.compile(pattern, re.IGNORECASE), level, desc)
            for pattern, level, desc in self.PATTERNS
        ]
    
    def analyze(self, code: str) -> List[SecurityWarning]:
        """Analyze code for indirect attacks.
        
        Args:
            code: Python code to analyze
        
        Returns:
            List of security warnings
        """
        warnings = []
        
        # Pattern matching
        for pattern, level, description in self._compiled_patterns:
            for match in pattern.finditer(code):
                warnings.append(SecurityWarning(
                    level=level,
                    pattern=description,
                    match=match.group()[:50],
                    recommendation=self._get_recommendation(level),
                ))
        
        # Try to decode and re-analyze
        if self.decode_attempts:
            decoded = self._attempt_decode(code)
            if decoded:
                nested_warnings = self.analyze(decoded)
                for w in nested_warnings:
                    w.pattern = f"(decoded) {w.pattern}"
                warnings.extend(nested_warnings)
        
        # Check for chr() concatenation pattern
        chr_warnings = self._check_chr_chain(code)
        warnings.extend(chr_warnings)
        
        return warnings
    
    def _attempt_decode(self, code: str) -> Optional[str]:
        """Try to decode any obfuscated strings in code."""
        # Try to find and decode base64 strings
        b64_pattern = r"b64decode\s*\(\s*['\"]([A-Za-z0-9+/=]+)['\"]"
        for match in re.finditer(b64_pattern, code):
            try:
                decoded = base64.b64decode(match.group(1)).decode('utf-8')
                return decoded
            except Exception:
                pass
        
        # Try to find and decode hex strings
        hex_pattern = r"bytes\.fromhex\s*\(\s*['\"]([0-9a-fA-F]+)['\"]"
        for match in re.finditer(hex_pattern, code):
            try:
                decoded = bytes.fromhex(match.group(1)).decode('utf-8')
                return decoded
            except Exception:
                pass
        
        return None
    
    def _check_chr_chain(self, code: str) -> List[SecurityWarning]:
        """Check for chr() chains that spell out dangerous code."""
        warnings = []
        
        # Find sequences like chr(105)+chr(109)+...
        chr_pattern = r'chr\s*\(\s*(\d+)\s*\)'
        matches = re.findall(chr_pattern, code)
        
        if len(matches) >= 3:
            # Likely a chr chain - decode it
            try:
                decoded = ''.join(chr(int(c)) for c in matches)
                
                # Check if decoded string is suspicious
                suspicious_keywords = ['import', 'exec', 'eval', 'open', '__', 'os', 'subprocess']
                for keyword in suspicious_keywords:
                    if keyword in decoded.lower():
                        warnings.append(SecurityWarning(
                            level='critical',
                            pattern=f'Chr chain decodes to "{keyword}"',
                            match=f'{decoded[:30]}...' if len(decoded) > 30 else decoded,
                            recommendation='Block: obfuscated dangerous code',
                        ))
                        break
            except Exception:
                pass
        
        return warnings
    
    def _get_recommendation(self, level: str) -> str:
        """Get recommendation based on severity level."""
        recommendations = {
            'low': 'Review code manually',
            'medium': 'Proceed with caution',
            'high': 'Block unless explicitly allowed',
            'critical': 'Block immediately',
        }
        return recommendations.get(level, 'Review')
    
    def has_critical(self, warnings: List[SecurityWarning]) -> bool:
        """Check if any warnings are critical."""
        return any(w.level == 'critical' for w in warnings)
    
    def has_high_or_critical(self, warnings: List[SecurityWarning]) -> bool:
        """Check if any warnings are high or critical."""
        return any(w.level in ('high', 'critical') for w in warnings)
