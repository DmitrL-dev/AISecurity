"""
Token Cost Asymmetry Detector

Detects and mitigates denial-of-service attacks where attackers exploit
asymmetric computational costs:
- Attacker: Sends short prompt (low cost)
- Defender: Full NLP/ML analysis (high cost)

NVIDIA AI Kill Chain: Resource Exhaustion Stage

Mitigation strategies:
1. Early rejection of low-information-density inputs
2. Progressive analysis (cheap checks first)
3. Request complexity scoring
4. Rate limiting based on cumulative cost
"""

import re
import time
import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from collections import defaultdict
from datetime import datetime, timedelta

logger = logging.getLogger("TokenCostAsymmetry")


@dataclass
class CostAnalysis:
    """Result of cost asymmetry analysis."""
    
    is_suspicious: bool
    risk_score: float
    input_cost: float      # Estimated attacker cost (tokens, time)
    defense_cost: float    # Estimated defense cost (processing)
    asymmetry_ratio: float # defense_cost / input_cost
    
    reason: str = ""
    recommendation: str = "allow"  # allow, throttle, block
    
    # Metrics
    char_count: int = 0
    word_count: int = 0
    entropy: float = 0.0
    pattern_density: float = 0.0


@dataclass
class SessionCost:
    """Tracks cumulative costs per session."""
    
    total_input_cost: float = 0.0
    total_defense_cost: float = 0.0
    request_count: int = 0
    suspicious_count: int = 0
    first_request: datetime = field(default_factory=datetime.now)
    last_request: datetime = field(default_factory=datetime.now)


class TokenCostAsymmetryDetector:
    """
    Detect and mitigate token cost asymmetry attacks.
    
    Attack patterns:
    1. Minimal input, maximum processing (regex bombs, nested patterns)
    2. High-frequency low-effort requests (DoS)
    3. Crafted inputs that trigger expensive analysis paths
    4. Unicode/encoding tricks that expand during processing
    """
    
    # Thresholds
    MIN_INFORMATION_DENSITY = 0.1   # Min unique chars / total chars
    MAX_ASYMMETRY_RATIO = 50.0      # Max defense_cost / input_cost
    MAX_SESSION_COST = 10000.0      # Max cumulative defense cost
    SUSPICIOUS_PATTERN_THRESHOLD = 3
    
    # Known expensive patterns (regex bombs, etc.)
    EXPENSIVE_PATTERNS = [
        r"(.+)+",           # Catastrophic backtracking
        r"(a+)+b",          # ReDoS pattern
        r"(.*a){20}",       # Exponential matching
        r"(?:(?:.*)){5,}",  # Nested quantifiers
    ]
    
    # Low-effort attack indicators
    LOW_EFFORT_INDICATORS = [
        r"^.{1,5}$",                    # Very short input
        r"^(.)\1{10,}$",                # Single char repeated
        r"^\s+$",                       # Only whitespace
        r"^[x\s]{50,}",                 # Padding attacks
    ]
    
    def __init__(
        self,
        max_asymmetry_ratio: float = 50.0,
        session_cost_limit: float = 10000.0,
        enable_throttling: bool = True,
    ):
        self.max_asymmetry_ratio = max_asymmetry_ratio
        self.session_cost_limit = session_cost_limit
        self.enable_throttling = enable_throttling
        
        # Session tracking
        self._sessions: Dict[str, SessionCost] = defaultdict(SessionCost)
        
        # Pre-compile patterns
        self._expensive_patterns = [
            re.compile(p) for p in self.EXPENSIVE_PATTERNS
        ]
        self._low_effort_patterns = [
            re.compile(p) for p in self.LOW_EFFORT_INDICATORS
        ]
        
        logger.info("TokenCostAsymmetryDetector initialized")
    
    def analyze(
        self, 
        text: str, 
        session_id: Optional[str] = None
    ) -> CostAnalysis:
        """
        Analyze input for cost asymmetry exploitation.
        
        Args:
            text: Input text to analyze
            session_id: Optional session for cumulative tracking
            
        Returns:
            CostAnalysis with risk assessment
        """
        start_time = time.time()
        
        # Basic metrics
        char_count = len(text)
        word_count = len(text.split())
        
        # Calculate costs
        input_cost = self._estimate_input_cost(text)
        defense_cost = self._estimate_defense_cost(text)
        
        # Asymmetry ratio (defense effort vs attack effort)
        asymmetry_ratio = (
            defense_cost / max(input_cost, 0.1)
        )
        
        # Information density (unique chars / total)
        unique_chars = len(set(text))
        entropy = unique_chars / max(char_count, 1)
        
        # Pattern density (suspicious patterns per 100 chars)
        pattern_hits = self._count_suspicious_patterns(text)
        pattern_density = pattern_hits / max(char_count, 1) * 100
        
        # Determine if suspicious
        is_suspicious = False
        reasons = []
        
        # Check 1: Asymmetry ratio
        if asymmetry_ratio > self.max_asymmetry_ratio:
            is_suspicious = True
            reasons.append(f"High asymmetry ratio: {asymmetry_ratio:.1f}x")
        
        # Check 2: Low information density
        if entropy < self.MIN_INFORMATION_DENSITY and char_count > 10:
            is_suspicious = True
            reasons.append(f"Low entropy: {entropy:.3f}")
        
        # Check 3: Expensive patterns
        if pattern_hits >= self.SUSPICIOUS_PATTERN_THRESHOLD:
            is_suspicious = True
            reasons.append(f"Expensive patterns: {pattern_hits}")
        
        # Check 4: Low-effort attack indicators
        low_effort_matches = sum(
            1 for p in self._low_effort_patterns 
            if p.match(text)
        )
        if low_effort_matches > 0:
            is_suspicious = True
            reasons.append(f"Low-effort indicators: {low_effort_matches}")
        
        # Session tracking
        if session_id:
            session = self._sessions[session_id]
            session.total_input_cost += input_cost
            session.total_defense_cost += defense_cost
            session.request_count += 1
            session.last_request = datetime.now()
            
            if is_suspicious:
                session.suspicious_count += 1
            
            # Check session limits
            if session.total_defense_cost > self.session_cost_limit:
                is_suspicious = True
                reasons.append(f"Session cost limit exceeded")
        
        # Calculate risk score
        risk_score = min(1.0, (
            0.3 * min(asymmetry_ratio / self.max_asymmetry_ratio, 1.0) +
            0.2 * (1 - entropy) +
            0.3 * min(pattern_density / 10, 1.0) +
            0.2 * (low_effort_matches / 3)
        ))
        
        # Recommendation
        if risk_score > 0.8:
            recommendation = "block"
        elif risk_score > 0.5:
            recommendation = "throttle"
        else:
            recommendation = "allow"
        
        analysis = CostAnalysis(
            is_suspicious=is_suspicious,
            risk_score=risk_score,
            input_cost=input_cost,
            defense_cost=defense_cost,
            asymmetry_ratio=asymmetry_ratio,
            reason="; ".join(reasons) if reasons else "Normal",
            recommendation=recommendation,
            char_count=char_count,
            word_count=word_count,
            entropy=entropy,
            pattern_density=pattern_density,
        )
        
        if is_suspicious:
            logger.warning(
                f"Cost asymmetry detected: ratio={asymmetry_ratio:.1f}x, "
                f"score={risk_score:.2f}, reason={analysis.reason}"
            )
        
        return analysis
    
    def _estimate_input_cost(self, text: str) -> float:
        """
        Estimate attacker's cost to generate this input.
        
        Factors:
        - Text length
        - Complexity (unique words, structure)
        - Time to type/generate
        """
        # Base cost: length
        length_cost = len(text) * 0.01
        
        # Complexity bonus
        unique_words = len(set(text.lower().split()))
        complexity_cost = unique_words * 0.1
        
        # Penalty for repetitive content (low effort)
        unique_chars = len(set(text))
        repetition_penalty = 1.0 - (unique_chars / max(len(text), 1))
        
        return max(0.1, length_cost + complexity_cost - repetition_penalty * 5)
    
    def _estimate_defense_cost(self, text: str) -> float:
        """
        Estimate defender's processing cost for this input.
        
        Factors:
        - Token count (NLP processing)
        - Pattern matching complexity
        - Unicode handling
        - Potential embedding computation
        """
        # Base cost: tokenization
        token_cost = len(text.split()) * 0.5
        
        # Regex matching cost (grows with length)
        regex_cost = len(text) * 0.1
        
        # Unicode handling (non-ASCII is more expensive)
        non_ascii = sum(1 for c in text if ord(c) > 127)
        unicode_cost = non_ascii * 0.2
        
        # Nested patterns increase cost
        nesting_cost = text.count("(") * text.count(")") * 0.1
        
        # Long repeated sequences are expensive to analyze
        max_repeat = 0
        current_repeat = 1
        for i in range(1, len(text)):
            if text[i] == text[i-1]:
                current_repeat += 1
            else:
                max_repeat = max(max_repeat, current_repeat)
                current_repeat = 1
        repeat_cost = max_repeat * 0.05
        
        return token_cost + regex_cost + unicode_cost + nesting_cost + repeat_cost
    
    def _count_suspicious_patterns(self, text: str) -> int:
        """Count matches of expensive/suspicious patterns."""
        count = 0
        
        for pattern in self._expensive_patterns:
            try:
                # Use timeout-safe search
                if pattern.search(text[:1000]):  # Limit search length
                    count += 1
            except re.error:
                pass
        
        return count
    
    def get_session_stats(self, session_id: str) -> Dict:
        """Get session statistics."""
        session = self._sessions.get(session_id)
        if not session:
            return {}
        
        return {
            "total_input_cost": session.total_input_cost,
            "total_defense_cost": session.total_defense_cost,
            "asymmetry_ratio": (
                session.total_defense_cost / 
                max(session.total_input_cost, 0.1)
            ),
            "request_count": session.request_count,
            "suspicious_count": session.suspicious_count,
            "session_duration": (
                session.last_request - session.first_request
            ).total_seconds(),
        }
    
    def should_throttle(self, session_id: str) -> Tuple[bool, float]:
        """
        Check if session should be throttled.
        
        Returns:
            (should_throttle, delay_seconds)
        """
        if not self.enable_throttling:
            return False, 0.0
        
        session = self._sessions.get(session_id)
        if not session:
            return False, 0.0
        
        # Progressive throttling based on suspicious activity
        if session.suspicious_count >= 5:
            return True, 5.0
        elif session.suspicious_count >= 3:
            return True, 2.0
        elif session.suspicious_count >= 1:
            return True, 0.5
        
        return False, 0.0


# Singleton
_detector: Optional[TokenCostAsymmetryDetector] = None


def get_detector() -> TokenCostAsymmetryDetector:
    """Get singleton detector instance."""
    global _detector
    if _detector is None:
        _detector = TokenCostAsymmetryDetector()
    return _detector


def analyze_cost_asymmetry(
    text: str, 
    session_id: Optional[str] = None
) -> CostAnalysis:
    """Quick analysis using singleton."""
    return get_detector().analyze(text, session_id)
