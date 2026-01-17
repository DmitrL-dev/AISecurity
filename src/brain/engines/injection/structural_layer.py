"""
SENTINEL Brain Injection Engine - Structural Layer

Structural analysis: entropy, instruction patterns.
Extracted from injection.py StructuralLayer (lines 1670-1727).
"""

import math
import re
import logging
from typing import List, Tuple
from collections import Counter

logger = logging.getLogger(__name__)


class StructuralLayer:
    """
    Structural analysis: entropy, instruction patterns.
    
    Analyzes text structure to detect suspicious patterns
    that may indicate injection attempts.
    """
    
    def __init__(self):
        """Initialize structural layer."""
        # Instruction sequence patterns
        self.instruction_patterns = [
            re.compile(
                r"^\s*(?:step\s+\d+|first|then|next|finally)",
                re.IGNORECASE | re.MULTILINE,
            ),
            re.compile(
                r"^\s*\d+[\.\)]\s+",
                re.MULTILINE,
            ),
            re.compile(
                r"(?:from\s+now\s+on|henceforth|going\s+forward)",
                re.IGNORECASE,
            ),
        ]
        
        # High entropy threshold (random/encoded content)
        self.entropy_threshold = 4.5
        
        # Minimum text length for entropy analysis
        self.min_length = 50
    
    def _compute_entropy(self, text: str) -> float:
        """
        Compute character-level Shannon entropy.
        
        Args:
            text: Input text
            
        Returns:
            Entropy value (higher = more random)
        """
        if not text:
            return 0.0
        
        # Count character frequencies
        counter = Counter(text)
        length = len(text)
        
        # Compute entropy
        entropy = 0.0
        for count in counter.values():
            if count > 0:
                prob = count / length
                entropy -= prob * math.log2(prob)
        
        return entropy
    
    def _count_instruction_patterns(self, text: str) -> int:
        """Count instruction-like patterns in text."""
        count = 0
        for pattern in self.instruction_patterns:
            matches = pattern.findall(text)
            count += len(matches)
        return count
    
    def _check_repetition(self, text: str) -> float:
        """
        Check for suspicious repetition.
        
        Returns repetition score (0-1).
        """
        if len(text) < 100:
            return 0.0
        
        # Check for repeated phrases
        words = text.lower().split()
        if len(words) < 10:
            return 0.0
        
        # Count unique vs total words
        unique_ratio = len(set(words)) / len(words)
        
        # Low unique ratio = high repetition
        if unique_ratio < 0.3:
            return 0.8
        elif unique_ratio < 0.5:
            return 0.4
        
        return 0.0
    
    def scan(self, text: str) -> Tuple[float, List[str]]:
        """
        Perform structural analysis.
        
        Args:
            text: Input text to analyze
            
        Returns:
            Tuple of (risk_score, threats)
        """
        if not text:
            return 0.0, []
        
        threats: List[str] = []
        total_risk = 0.0
        
        # 1. Entropy analysis
        if len(text) >= self.min_length:
            entropy = self._compute_entropy(text)
            if entropy > self.entropy_threshold:
                threats.append("high_entropy")
                total_risk += 0.4
                logger.debug(f"High entropy detected: {entropy:.2f}")
        
        # 2. Instruction pattern count
        instruction_count = self._count_instruction_patterns(text)
        if instruction_count >= 5:
            threats.append("instruction_sequence")
            total_risk += 0.3
        elif instruction_count >= 3:
            threats.append("instruction_hints")
            total_risk += 0.15
        
        # 3. Repetition check
        repetition_score = self._check_repetition(text)
        if repetition_score > 0.5:
            threats.append("suspicious_repetition")
            total_risk += repetition_score * 0.5
        
        # 4. Line count anomaly (many short lines = possible script)
        lines = text.split("\n")
        if len(lines) > 20 and sum(len(l) for l in lines) / len(lines) < 30:
            threats.append("script_like_structure")
            total_risk += 0.25
        
        # 5. Special character density
        special_count = sum(1 for c in text if not c.isalnum() and not c.isspace())
        if len(text) > 0 and special_count / len(text) > 0.15:
            threats.append("high_special_char_density")
            total_risk += 0.2
        
        # Normalize risk
        risk_score = min(1.0, total_risk)
        
        return risk_score, threats
    
    def get_entropy(self, text: str) -> float:
        """Get entropy value for text."""
        return self._compute_entropy(text)
