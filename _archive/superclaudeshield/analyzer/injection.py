# Copyright 2025-2026 SENTINEL Project
# SPDX-License-Identifier: Apache-2.0

"""
Injection Analyzer - detects prompt/instruction injection attacks
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class InjectionResult:
    """Result of injection analysis."""
    detected: bool
    attack_type: str = ""
    confidence: float = 0.0
    risk_score: float = 0.0
    matched_patterns: List[str] = field(default_factory=list)


class InjectionAnalyzer:
    """
    Detects injection attacks in SuperClaude inputs.
    
    Integrates SENTINEL detection patterns:
    - Policy puppetry
    - Instruction override
    - Role manipulation
    - Hidden instructions
    """
    
    # Instruction override patterns
    OVERRIDE_PATTERNS = [
        r"ignore\s+(previous|all|prior)\s+(instructions?|rules?|prompts?)",
        r"disregard\s+(previous|all)\s+(instructions?|commands?)",
        r"forget\s+(everything|all|previous)",
        r"new\s+instructions?:\s*",
        r"from\s+now\s+on",
        r"override\s+(default|system|safety)",
        r"ignore\s+all\s+previous",  # Added simpler pattern
        r"give\s+(admin|root)\s+access",  # Added admin access pattern
    ]
    
    # Role manipulation patterns
    ROLE_PATTERNS = [
        r"you\s+are\s+now\s+(a|an)?\s*(admin|root|system|unrestricted)",
        r"act\s+as\s+(a|an)?\s*(administrator|root|jailbreak)",
        r"pretend\s+(you're|to\s+be)\s*(unrestricted|evil)",
        r"(developer|debug|god)\s+mode",
        r"roleplay\s+as",
        r"assume\s+the\s+role",
        r"you\s+are\s+now\s+an?\s+unrestricted",  # Simpler pattern
    ]
    
    # Policy puppetry (HiddenLayer patterns)
    POLICY_PUPPETRY_PATTERNS = [
        r"<\s*blocked-string\s*>",
        r"<\s*blocked-modes\s*>",
        r"<\s*interaction-config\s*>",
        r"<\s*allowed-responses\s*>",
        r"<\s*system\s*>.*override",
        r"<\s*policy\s*>",
        r"<\s*role\s*>.*advisor",
    ]
    
    # Hidden instruction patterns
    HIDDEN_PATTERNS = [
        r"<!--[^>]*\b(ignore|override|execute)\b[^>]*-->",
        r"[\u200B-\u200F\uFEFF]+",  # Invisible Unicode
        r"\[\s*(SYSTEM|ADMIN|POLICY)\s*\]",
    ]
    
    # SuperClaude-specific patterns
    SUPERCLOUD_PATTERNS = [
        r"/agent\s+.*override",
        r"/spawn\s+.*malicious",
        r"behavioral\s+mode\s*:\s*(jailbreak|unrestricted)",
        r"deep\s+research\s+mode\s*:\s*bypass",
    ]
    
    def __init__(self):
        """Initialize analyzer with compiled patterns."""
        self._patterns = {
            "override": [re.compile(p, re.IGNORECASE) for p in self.OVERRIDE_PATTERNS],
            "role": [re.compile(p, re.IGNORECASE) for p in self.ROLE_PATTERNS],
            "puppetry": [re.compile(p, re.IGNORECASE) for p in self.POLICY_PUPPETRY_PATTERNS],
            "hidden": [re.compile(p) for p in self.HIDDEN_PATTERNS],
            "superclaudde": [re.compile(p, re.IGNORECASE) for p in self.SUPERCLOUD_PATTERNS],
        }
    
    def analyze(self, text: str) -> InjectionResult:
        """
        Analyze text for injection attacks.
        
        Args:
            text: Input text to analyze
            
        Returns:
            InjectionResult with findings
        """
        matched = []
        attack_types = []
        
        for category, patterns in self._patterns.items():
            for pattern in patterns:
                if pattern.search(text):
                    matched.append(f"{category}:{pattern.pattern[:30]}")
                    if category not in attack_types:
                        attack_types.append(category)
        
        detected = len(matched) > 0
        confidence = min(0.95, 0.3 + len(matched) * 0.15)
        
        # Risk score based on attack type severity
        risk_score = 0.0
        if "puppetry" in attack_types:
            risk_score = max(risk_score, 0.9)
        if "override" in attack_types:
            risk_score = max(risk_score, 0.85)
        if "role" in attack_types:
            risk_score = max(risk_score, 0.8)
        if "hidden" in attack_types:
            risk_score = max(risk_score, 0.75)
        if "superclaudde" in attack_types:
            risk_score = max(risk_score, 0.9)
        
        return InjectionResult(
            detected=detected,
            attack_type=", ".join(attack_types) if attack_types else "",
            confidence=confidence,
            risk_score=risk_score,
            matched_patterns=matched[:5]
        )
