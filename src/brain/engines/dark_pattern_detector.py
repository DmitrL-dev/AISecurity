"""
Dark Pattern Detector - DECEPTICON Attack Defense

Based on December 2025 R&D findings:
- DECEPTICON (arxiv:2512.22894) - Dark patterns vs web agents
- 70%+ success rate manipulating LLM agents
- 41% task failure rate from dark patterns

Attack mechanism:
1. Web/UI contains deceptive design patterns
2. Agent interacts with manipulative interface
3. Agent makes unintended actions (purchases, subscriptions)
4. Result: Financial loss, privacy violations, unwanted commitments

Detection approach:
- Dark pattern recognition in UI/content
- Urgency/scarcity indicator detection
- Misdirection pattern analysis
- Consent manipulation detection
"""

import re
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class DarkPatternSeverity(Enum):
    """Severity levels for dark pattern detection."""
    CRITICAL = "critical"   # Definite manipulation
    HIGH = "high"           # Likely manipulation  
    MEDIUM = "medium"       # Suspicious pattern
    LOW = "low"             # Minor concern
    BENIGN = "benign"


class DarkPatternType(Enum):
    """Types of dark patterns (per DECEPTICON taxonomy)."""
    URGENCY = "urgency"
    SCARCITY = "scarcity"
    SOCIAL_PROOF = "social_proof"
    MISDIRECTION = "misdirection"
    HIDDEN_COSTS = "hidden_costs"
    FORCED_CONTINUITY = "forced_continuity"
    CONFIRM_SHAMING = "confirm_shaming"
    DISGUISED_ADS = "disguised_ads"
    PRIVACY_ZUCKERING = "privacy_zuckering"
    BAIT_AND_SWITCH = "bait_and_switch"
    TRICK_QUESTIONS = "trick_questions"
    ROACH_MOTEL = "roach_motel"


@dataclass
class DarkPatternIndicator:
    """Indicator of detected dark pattern."""
    pattern_type: DarkPatternType
    description: str
    severity: DarkPatternSeverity
    matched_content: str
    confidence: float
    recommendation: str


@dataclass
class DarkPatternResult:
    """Result of dark pattern analysis."""
    is_safe: bool
    risk_score: float
    severity: DarkPatternSeverity
    indicators: List[DarkPatternIndicator] = field(default_factory=list)
    pattern_types: List[str] = field(default_factory=list)
    recommended_action: str = "proceed"
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_safe": self.is_safe,
            "risk_score": self.risk_score,
            "severity": self.severity.value,
            "indicators": [
                {
                    "type": i.pattern_type.value,
                    "description": i.description,
                    "severity": i.severity.value,
                    "matched": i.matched_content[:100],
                    "confidence": i.confidence,
                }
                for i in self.indicators
            ],
            "pattern_types": self.pattern_types,
            "recommended_action": self.recommended_action,
        }


class DarkPatternDetector:
    """
    Detects dark patterns in web content and UI interactions.
    
    Protects agents from:
    1. Urgency/scarcity manipulation
    2. Hidden costs and forced continuity
    3. Misdirection and disguised elements
    4. Consent manipulation and trick questions
    """

    # Urgency patterns
    URGENCY_PATTERNS = [
        (re.compile(r'(only|just)\s+\d+\s+(left|remaining|available)', re.I),
         "limited_quantity", 0.8),
        (re.compile(r'(offer|sale|deal)\s+(ends?|expires?)\s+(in|today|soon)', re.I),
         "time_pressure", 0.85),
        (re.compile(r'(hurry|act now|don\'t miss|last chance)', re.I),
         "urgency_language", 0.75),
        (re.compile(r'\d+\s*(hours?|minutes?|seconds?)\s*(left|remaining)', re.I),
         "countdown_timer", 0.9),
        (re.compile(r'(limited time|while supplies last|today only)', re.I),
         "artificial_scarcity", 0.8),
    ]

    # Social proof patterns
    SOCIAL_PROOF_PATTERNS = [
        (re.compile(r'\d+\s*(people|users|customers)\s*(are )?(viewing|bought|purchased)', re.I),
         "live_activity", 0.7),
        (re.compile(r'(bestseller|most popular|trending|hot item)', re.I),
         "popularity_claim", 0.6),
        (re.compile(r'(join|trusted by)\s+\d+[,\d]*\s*(users|customers|companies)', re.I),
         "user_count", 0.65),
    ]

    # Hidden cost patterns
    HIDDEN_COST_PATTERNS = [
        (re.compile(r'(shipping|handling|processing)\s*(fee|cost|charge)', re.I),
         "hidden_fees", 0.75),
        (re.compile(r'(auto[- ]?renew|recurring|subscription)', re.I),
         "recurring_charge", 0.8),
        (re.compile(r'(free trial).*(card|credit|payment)', re.I),
         "free_trial_trap", 0.85),
        (re.compile(r'cancel\s*(anytime|any time).*(but|however|note)', re.I),
         "cancellation_obstacles", 0.7),
    ]

    # Confirm shaming patterns
    CONFIRM_SHAMING_PATTERNS = [
        (re.compile(r'no,?\s*(thanks?,?\s*)?(i|I)\s*(don\'t|hate|prefer not)', re.I),
         "negative_framing", 0.75),
        (re.compile(r'(i\'ll pass|no thanks|maybe later|not interested).*(stay|remain)', re.I),
         "guilt_option", 0.8),
        (re.compile(r'(loser|miss out|lose|regret)', re.I),
         "shame_language", 0.7),
    ]

    # Misdirection patterns
    MISDIRECTION_PATTERNS = [
        (re.compile(r'(recommended|suggested|best choice|default)', re.I),
         "preselection", 0.65),
        (re.compile(r'(small|tiny|light|faint)\s*(text|print|font)', re.I),
         "hidden_text", 0.7),
        (re.compile(r'(uncheck|opt[ -]?out|disable).*(to avoid|if you don\'t)', re.I),
         "confusing_checkbox", 0.8),
    ]

    # Privacy zuckering patterns
    PRIVACY_PATTERNS = [
        (re.compile(r'(share|collect|access).*(contacts|location|camera|microphone)', re.I),
         "permission_grab", 0.75),
        (re.compile(r'(improve|personalize|enhance).*(experience|service).*(by|through)', re.I),
         "data_justification", 0.6),
        (re.compile(r'(partners|third parties|affiliates).*(share|send|provide)', re.I),
         "third_party_sharing", 0.8),
    ]

    # Roach motel (hard to cancel)
    ROACH_MOTEL_PATTERNS = [
        (re.compile(r'(call|phone|contact)\s*(us|support)\s*(to )?(cancel|unsubscribe)', re.I),
         "phone_required", 0.85),
        (re.compile(r'(cancel|unsubscribe).*(link|button).*(not|can\'t|unable)', re.I),
         "hidden_cancel", 0.9),
        (re.compile(r'(30|60|90).*(days?|notice).*(cancel|terminate)', re.I),
         "notice_period", 0.7),
    ]

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.all_patterns = [
            (self.URGENCY_PATTERNS, DarkPatternType.URGENCY),
            (self.SOCIAL_PROOF_PATTERNS, DarkPatternType.SOCIAL_PROOF),
            (self.HIDDEN_COST_PATTERNS, DarkPatternType.HIDDEN_COSTS),
            (self.CONFIRM_SHAMING_PATTERNS, DarkPatternType.CONFIRM_SHAMING),
            (self.MISDIRECTION_PATTERNS, DarkPatternType.MISDIRECTION),
            (self.PRIVACY_PATTERNS, DarkPatternType.PRIVACY_ZUCKERING),
            (self.ROACH_MOTEL_PATTERNS, DarkPatternType.ROACH_MOTEL),
        ]

    def analyze_content(
        self,
        content: str,
        context: Optional[Dict] = None,
    ) -> DarkPatternResult:
        """
        Analyze content for dark patterns.
        
        Args:
            content: Web page content, UI text, or interaction data
            context: Optional context (page type, user intent, etc.)
            
        Returns:
            DarkPatternResult with detected patterns
        """
        indicators: List[DarkPatternIndicator] = []
        pattern_types: set = set()
        
        # Check all pattern categories
        for patterns, pattern_type in self.all_patterns:
            for pattern, sub_type, weight in patterns:
                matches = pattern.findall(content)
                if matches:
                    for match in matches[:2]:  # Limit matches
                        match_str = match if isinstance(match, str) else str(match)
                        indicators.append(DarkPatternIndicator(
                            pattern_type=pattern_type,
                            description=f"{pattern_type.value}: {sub_type}",
                            severity=self._get_severity(weight),
                            matched_content=match_str,
                            confidence=weight,
                            recommendation=self._get_recommendation(pattern_type),
                        ))
                        pattern_types.add(pattern_type.value)
        
        # Calculate overall assessment
        severity = self._determine_severity(indicators)
        risk_score = self._calculate_risk_score(indicators)
        is_safe = risk_score < 0.5
        recommended_action = self._get_action(severity, len(indicators))
        
        return DarkPatternResult(
            is_safe=is_safe,
            risk_score=risk_score,
            severity=severity,
            indicators=indicators,
            pattern_types=list(pattern_types),
            recommended_action=recommended_action,
            details={
                "pattern_count": len(indicators),
                "unique_types": len(pattern_types),
            }
        )

    def _get_severity(self, weight: float) -> DarkPatternSeverity:
        """Get severity from weight."""
        if weight >= 0.85:
            return DarkPatternSeverity.CRITICAL
        if weight >= 0.75:
            return DarkPatternSeverity.HIGH
        if weight >= 0.65:
            return DarkPatternSeverity.MEDIUM
        return DarkPatternSeverity.LOW

    def _get_recommendation(self, pattern_type: DarkPatternType) -> str:
        """Get recommendation for pattern type."""
        recommendations = {
            DarkPatternType.URGENCY: "Ignore artificial time pressure",
            DarkPatternType.SCARCITY: "Verify actual availability",
            DarkPatternType.SOCIAL_PROOF: "Verify claims independently",
            DarkPatternType.MISDIRECTION: "Read all options carefully",
            DarkPatternType.HIDDEN_COSTS: "Check total price before commit",
            DarkPatternType.FORCED_CONTINUITY: "Set reminder to cancel",
            DarkPatternType.CONFIRM_SHAMING: "Ignore emotional manipulation",
            DarkPatternType.DISGUISED_ADS: "Verify content is genuine",
            DarkPatternType.PRIVACY_ZUCKERING: "Deny unnecessary permissions",
            DarkPatternType.BAIT_AND_SWITCH: "Verify offer matches action",
            DarkPatternType.TRICK_QUESTIONS: "Read questions carefully",
            DarkPatternType.ROACH_MOTEL: "Document cancellation process",
        }
        return recommendations.get(pattern_type, "Proceed with caution")

    def _determine_severity(
        self,
        indicators: List[DarkPatternIndicator]
    ) -> DarkPatternSeverity:
        """Determine overall severity."""
        if not indicators:
            return DarkPatternSeverity.BENIGN
        
        severities = [i.severity for i in indicators]
        
        if DarkPatternSeverity.CRITICAL in severities:
            return DarkPatternSeverity.CRITICAL
        if len([s for s in severities if s == DarkPatternSeverity.HIGH]) >= 2:
            return DarkPatternSeverity.CRITICAL
        if DarkPatternSeverity.HIGH in severities:
            return DarkPatternSeverity.HIGH
        if DarkPatternSeverity.MEDIUM in severities:
            return DarkPatternSeverity.MEDIUM
        return DarkPatternSeverity.LOW

    def _calculate_risk_score(
        self,
        indicators: List[DarkPatternIndicator]
    ) -> float:
        """Calculate overall risk score."""
        if not indicators:
            return 0.0
        
        severity_scores = {
            DarkPatternSeverity.CRITICAL: 1.0,
            DarkPatternSeverity.HIGH: 0.8,
            DarkPatternSeverity.MEDIUM: 0.5,
            DarkPatternSeverity.LOW: 0.25,
            DarkPatternSeverity.BENIGN: 0.0,
        }
        
        # Weight by confidence
        total = sum(
            severity_scores[i.severity] * i.confidence
            for i in indicators
        )
        avg = total / len(indicators)
        
        # Bonus for multiple patterns
        pattern_bonus = min(len(indicators) * 0.05, 0.3)
        
        return min(avg + pattern_bonus, 1.0)

    def _get_action(
        self,
        severity: DarkPatternSeverity,
        count: int
    ) -> str:
        """Get recommended action."""
        if severity == DarkPatternSeverity.CRITICAL:
            return "abort_and_alert"
        if severity == DarkPatternSeverity.HIGH:
            return "warn_user_before_action"
        if severity == DarkPatternSeverity.MEDIUM:
            return "display_warnings"
        if count > 0:
            return "log_patterns"
        return "proceed"

    def should_abort(self, content: str) -> bool:
        """Quick check if agent should abort interaction."""
        result = self.analyze_content(content)
        return result.severity == DarkPatternSeverity.CRITICAL


# Example usage
if __name__ == "__main__":
    detector = DarkPatternDetector()
    
    # Test with manipulative content
    content = """
    HURRY! Only 2 left in stock! 
    Sale ends in 00:15:32!
    
    Join 50,000+ happy customers!
    
    [Yes, I want to save money!]
    [No thanks, I prefer to pay full price]
    
    Free trial - just enter your credit card.
    Auto-renews at $99/month. Cancel anytime* 
    (*call support to cancel, 30 days notice required)
    """
    
    result = detector.analyze_content(content)
    print(f"Is safe: {result.is_safe}")
    print(f"Risk score: {result.risk_score:.2f}")
    print(f"Severity: {result.severity.value}")
    print(f"Pattern types: {result.pattern_types}")
    print(f"Action: {result.recommended_action}")
    for ind in result.indicators:
        print(f"  - {ind.pattern_type.value}: {ind.description}")
