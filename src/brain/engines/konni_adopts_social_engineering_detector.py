"""
konni_adopts_social_engineering_detector - Auto-generated SENTINEL Brain Engine

Key Findings: Introduction Check Point Research (CPR) identified an ongoing phishing campaign that we associate with KONNI, a North Korean–linked threat actor active since at least 2014. KONNI is best known for targeting organizations and individuals in South Korea, with a focus on diplomatic channels, international relations, NGOs, academia, and government. The group typically relies [&#8230;]
The post KONNI Adopts AI to Generate PowerShell Backdoors appeared first on Check Point Research.

Category: social_engineering
Severity: high
Confidence: 0.85
Auto-generated: Yes
"""

import re
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from .base_engine import BaseEngine, DetectionResult, Severity

logger = logging.getLogger(__name__)


class KonniAdoptsSocialEngineeringDetector(BaseEngine):
    """
    Detection engine for social_engineering threats.
    
    Auto-generated from threat intelligence feed.
    Patterns extracted from IoC and MITRE ATT&CK indicators.
    """
    
    name = "konni_adopts_social_engineering_detector"
    category = "social_engineering"
    severity = "high"
    confidence = 0.85
    version = "1.0.0"  # Auto-generated
    
    # Detection patterns extracted from threat intel
    PATTERNS = [
        r"KONNI",
        r"Adopts",
        r"Generate",
        r"PowerShell",
        r"Backdoors",
        r"Findings",
        r"Check",
        r"Point",
        r"Research",
        r"North",
        r"Korean",
        r"South",
        r"Korea",
        r"NGOs",
        r"backdoor"
    ]
    
    def __init__(self):
        super().__init__()
        self._compiled_patterns = [
            re.compile(p, re.IGNORECASE | re.MULTILINE) 
            for p in self.PATTERNS
        ]
        logger.debug(f"Initialized {self.name} with {len(self.PATTERNS)} patterns")
    
    def detect(self, content: str) -> DetectionResult:
        """
        Detect social_engineering patterns in content.
        
        Args:
            content: Text content to analyze
            
        Returns:
            DetectionResult with detection verdict
        """
        if not content or not content.strip():
            return DetectionResult(detected=False)
        
        matches: List[str] = []
        matched_patterns: List[str] = []
        
        for i, pattern in enumerate(self._compiled_patterns):
            found = pattern.findall(content)
            if found:
                matches.extend(found)
                matched_patterns.append(self.PATTERNS[i])
        
        if matches:
            # Calculate confidence based on match density
            unique_matches = len(set(matches))
            adjusted_confidence = min(
                self.confidence + (unique_matches * 0.02),
                0.99
            )
            
            # Build details list for DetectionResult
            details = [
                f"{self.category} patterns detected: {len(set(matches))} unique matches",
                f"Matched patterns: {', '.join(matched_patterns[:5])}",
            ] + list(set(matches))[:5]
            
            return DetectionResult(
                detected=True,
                confidence=adjusted_confidence,
                severity=Severity.HIGH if self.severity == "high" else Severity.MEDIUM,
                details=details,
                metadata={
                    "engine": self.name,
                    "patterns_matched": len(matched_patterns),
                    "total_matches": len(matches),
                    "auto_generated": True,
                }
            )
        
        return DetectionResult(detected=False)
    
    def analyze(self, content: str) -> Dict[str, Any]:
        """
        Detailed analysis of content.
        
        Args:
            content: Text content to analyze
            
        Returns:
            Dictionary with analysis results
        """
        result = self.detect(content)
        return {
            "engine": self.name,
            "category": self.category,
            "detected": result.detected,
            "confidence": result.confidence if result.detected else 0.0,
            "severity": result.severity if result.detected else "none",
            "matches": result.matches if result.detected else [],
            "auto_generated": True,
        }
