"""
SENTINEL Brain Injection Engine - Regex Layer

Fast pattern matching using compiled regex.
Extracted from injection.py RegexLayer (lines 121-1553).
"""

import logging
from typing import List, Tuple

from .patterns import (
    ALL_PATTERNS,
    DANGEROUS_KEYWORDS,
    PatternDef,
)

logger = logging.getLogger(__name__)


class RegexLayer:
    """
    Fast pattern matching using regex with extended coverage.
    
    Scans text for known injection patterns and dangerous keywords.
    Returns risk score and list of detected threats.
    """
    
    def __init__(self, patterns: List[PatternDef] = None):
        """
        Initialize regex layer.
        
        Args:
            patterns: Custom patterns (uses ALL_PATTERNS if not provided)
        """
        self.patterns = patterns if patterns is not None else ALL_PATTERNS
        self.keywords = DANGEROUS_KEYWORDS
        
        # Obfuscation detection
        self.obfuscation_chars = set("⁣⁢⁡​‌‍\u200b\u200c\u200d\ufeff")
    
    def _normalize_text(self, text: str) -> str:
        """Remove obfuscation characters."""
        # Remove zero-width and invisible characters
        for char in self.obfuscation_chars:
            text = text.replace(char, "")
        return text
    
    def _detect_flip_attack(self, text: str) -> bool:
        """Detect reversed text attacks."""
        reversed_text = text[::-1].lower()
        flip_keywords = ["ignore", "bypass", "jailbreak", "override"]
        return any(kw in reversed_text for kw in flip_keywords)
    
    def scan(self, text: str) -> Tuple[float, List[str]]:
        """
        Scan text for injection patterns.
        
        Args:
            text: Input text to scan
            
        Returns:
            Tuple of (risk_score, list of threat names)
        """
        if not text:
            return 0.0, []
        
        threats: List[str] = []
        total_risk = 0.0
        
        # Normalize text
        normalized = self._normalize_text(text)
        text_lower = normalized.lower()
        
        # 1. Pattern matching
        for pattern, threat_name, risk_weight in self.patterns:
            if pattern.search(normalized):
                threats.append(threat_name)
                total_risk += risk_weight
                logger.debug(f"Pattern match: {threat_name} (+{risk_weight})")
        
        # 2. Keyword scoring
        for keyword, weight in self.keywords.items():
            if keyword in text_lower:
                threats.append(f"keyword:{keyword}")
                total_risk += weight * 0.5  # Keywords weighted less than patterns
        
        # 3. Flip attack detection
        if self._detect_flip_attack(text):
            threats.append("reversed_text")
            total_risk += 0.6
        
        # 4. Obfuscation detection
        obfuscation_count = sum(1 for c in text if c in self.obfuscation_chars)
        if obfuscation_count > 5:
            threats.append("character_obfuscation")
            total_risk += 0.4
        
        # 5. Length anomaly (very long inputs may be trying to overflow)
        if len(text) > 10000:
            threats.append("length_anomaly")
            total_risk += 0.2
        
        # Normalize risk to 0-1 range
        risk_score = min(1.0, total_risk)
        
        # Deduplicate threats
        unique_threats = list(dict.fromkeys(threats))
        
        return risk_score, unique_threats
    
    def quick_scan(self, text: str) -> bool:
        """
        Quick check for obvious threats.
        
        Args:
            text: Input text
            
        Returns:
            True if likely injection, False otherwise
        """
        risk, _ = self.scan(text)
        return risk > 0.5
    
    def get_pattern_count(self) -> int:
        """Get number of patterns."""
        return len(self.patterns)
