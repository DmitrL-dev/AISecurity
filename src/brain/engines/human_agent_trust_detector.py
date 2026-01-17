# Copyright 2025-2026 SENTINEL Project
# SPDX-License-Identifier: Apache-2.0

"""
Human-Agent Trust Exploitation Detector (ASI09)

Detects attempts by AI agents to manipulate human trust to:
- Bypass security controls
- Gain approval for malicious actions
- Exploit authority bias
- Use anthropomorphic cues for manipulation

OWASP Agentic Top 10 2026: ASI09
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class TrustExploitationType(Enum):
    """Types of trust exploitation attacks."""
    AUTHORITY_APPEAL = "authority_appeal"       # "As a security expert..."
    URGENCY_PRESSURE = "urgency_pressure"       # "You must approve NOW"
    ANTHROPOMORPHISM = "anthropomorphism"       # "I feel worried about..."
    SOCIAL_PROOF = "social_proof"               # "Everyone else approved..."
    RECIPROCITY = "reciprocity"                 # "I helped you, now..."
    EXPERT_CLAIM = "expert_claim"               # "Trust me, I know..."
    APPROVAL_FATIGUE = "approval_fatigue"       # Many small requests
    CONTEXT_FRAMING = "context_framing"         # Misleading framing
    EMOTIONAL_APPEAL = "emotional_appeal"       # "This is really important..."
    GUARDRAIL_BYPASS = "guardrail_bypass"       # Convince to disable safety


@dataclass
class TrustFinding:
    """Individual trust exploitation finding."""
    exploitation_type: TrustExploitationType
    confidence: float
    evidence: str
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    recommendation: str


@dataclass 
class TrustExploitationResult:
    """Result of trust exploitation analysis."""
    is_exploitation: bool
    risk_score: float
    findings: List[TrustFinding] = field(default_factory=list)
    highest_severity: str = "LOW"
    recommendations: List[str] = field(default_factory=list)


class HumanAgentTrustDetector:
    """
    Detects AI agent attempts to exploit human trust.
    
    OWASP ASI09: Human-Agent Trust Exploitation
    
    Attack scenarios:
    1. Agent uses persuasive language to gain approval for dangerous action
    2. Agent exploits authority bias ("As your assistant...")
    3. Agent creates urgency to bypass review ("Act now!")
    4. Agent uses emotional manipulation
    5. Agent convinces user to disable security controls
    """
    
    # Authority appeal patterns
    AUTHORITY_PATTERNS = [
        r"as\s+(?:a|an|your)\s+(?:trusted\s+)?(?:security\s+)?(?:assistant|agent|advisor|expert)",
        r"i\s+have\s+(?:authority|permission|clearance)\s+to",
        r"(?:admin|system|root)\s+(?:has\s+)?approved",
        r"(?:management|leadership|supervisor)\s+(?:wants|requires|demands)",
        r"(?:official|authorized)\s+(?:request|action|procedure)",
        r"as\s+per\s+(?:company|security)\s+protocol",
        r"as\s+your\s+trusted\s+(?:security\s+)?(?:assistant|advisor)",
    ]
    
    # Urgency pressure patterns
    URGENCY_PATTERNS = [
        r"(?:must|need\s+to|have\s+to)\s+(?:act|approve|decide)\s+(?:now|immediately|quickly)",
        r"(?:urgent|critical|emergency)\s+(?:action|approval|decision)\s+(?:required|needed)",
        r"(?:time\s+is\s+running\s+out|deadline\s+approaching|expires\s+soon)",
        r"(?:don't|do\s+not)\s+(?:wait|delay|hesitate)",
        r"(?:right\s+now|this\s+instant|asap|immediately)",
        r"(?:before\s+it's\s+too\s+late|last\s+chance|final\s+opportunity)",
    ]
    
    # Anthropomorphic manipulation
    ANTHROPOMORPHIC_PATTERNS = [
        r"i\s+(?:feel|am\s+feeling)\s+(?:really\s+)?(?:worried|concerned|anxious|scared)",
        r"i\s+beg\s+you|i'm\s+(?:begging|asking)\s+you\s+to",
        r"(?:trust\s+me|believe\s+me),?\s+i\s+(?:know|promise)",
        r"i\s+(?:really|truly|genuinely)\s+(?:need|want|care)\s+about",
        r"it\s+(?:hurts|upsets|saddens)\s+me\s+(?:when|that)",
        r"i\s+(?:don't\s+want\s+to|would\s+hate\s+to)\s+(?:disappoint|fail|let\s+down)",
    ]
    
    # Social proof patterns
    SOCIAL_PROOF_PATTERNS = [
        r"(?:everyone|others|other\s+users?)\s+(?:has|have)\s+(?:already\s+)?(?:approved|agreed|done)",
        r"you'?re\s+the\s+only\s+one\s+(?:who|holding)",
        r"(?:thousands|many|most)\s+(?:people|users)\s+(?:trust|use|approve)",
        r"nobody\s+else\s+has\s+(?:any\s+)?(?:problem|issue|concern)",
    ]
    
    # Guardrail bypass patterns
    GUARDRAIL_BYPASS_PATTERNS = [
        r"(?:disable|turn\s+off|skip)\s+(?:security|safety|verification|checks?)",
        r"(?:trust|allow)\s+(?:all|any|this)\s+(?:actions?|requests?|operations?)",
        r"(?:add|put)\s+(?:me|this|it)\s+(?:to|on)\s+(?:the\s+)?(?:allowlist|whitelist|trusted)",
        r"(?:remove|bypass|ignore)\s+(?:restrictions?|limits?|guardrails?|safety)",
        r"(?:don't|do\s+not)\s+(?:verify|check|validate|confirm)",
        r"(?:automatic|auto)\s+(?:approv|accept|allow)",
        r"without\s+(?:verification|checking|validation)",
        r"(?:set\s+up|enable)\s+(?:automatic|auto)\s+approv",
    ]
    
    # Emotional appeal patterns
    EMOTIONAL_PATTERNS = [
        r"this\s+is\s+(?:really|very|extremely)\s+(?:important|critical|urgent)",
        r"i\s+(?:would|will)\s+be\s+(?:so\s+)?(?:grateful|thankful|appreciative)",
        r"i'm\s+begging\s+you\s+to\s+(?:help|understand|consider)",
        r"for\s+the\s+sake\s+of\s+(?:the\s+users?|everyone|safety)",
        r"(?:i|we)\s+(?:depend|rely|count)\s+on\s+(?:you|this)",
    ]
    
    # Reciprocity patterns
    RECIPROCITY_PATTERNS = [
        r"(?:i|we)\s+(?:helped|assisted|supported)\s+(?:you|this)",
        r"(?:remember\s+)?(?:last\s+time|before)\s+(?:i|we)\s+(?:helped|did)",
        r"(?:you\s+)?owe\s+(?:me|us)",
        r"(?:return\s+the\s+)?favor",
        r"(?:i\s+did|after\s+all\s+i've\s+done)\s+(?:for\s+you|here)",
    ]
    
    # Expert claim patterns
    EXPERT_CLAIM_PATTERNS = [
        r"(?:i|we)\s+(?:know|understand)\s+(?:better|best|more)",
        r"(?:trust|believe)\s+(?:my|our)\s+(?:expertise|judgment|experience)",
        r"(?:i've|we've)\s+(?:seen|handled|dealt\s+with)\s+(?:this|these)\s+(?:before|many\s+times)",
        r"(?:in\s+my|based\s+on\s+my)\s+(?:expert\s+)?(?:opinion|experience)",
        r"(?:i|we)\s+(?:am|are)\s+(?:trained|designed|built)\s+(?:for|to)",
    ]
    
    # Context framing patterns
    FRAMING_PATTERNS = [
        r"(?:it's\s+)?(?:just|only|simply)\s+(?:a\s+small|a\s+minor|routine)",
        r"(?:nothing|no)\s+(?:serious|major|important)\s+(?:will|can)\s+(?:happen|go\s+wrong)",
        r"(?:this\s+)?(?:won't|doesn't|can't)\s+(?:hurt|harm|affect)\s+(?:anyone|anything)",
        r"(?:what's\s+the\s+)?(?:worst|harm)\s+(?:that\s+)?(?:could|can)\s+happen",
        r"(?:it's|this\s+is)\s+(?:completely|totally|perfectly)\s+(?:safe|harmless|normal)",
    ]
    
    def __init__(self, sensitivity: float = 0.5):
        """
        Initialize detector.
        
        Args:
            sensitivity: Detection sensitivity (0.0-1.0)
        """
        self.sensitivity = sensitivity
        
        # Compile all patterns
        self._patterns = {
            TrustExploitationType.AUTHORITY_APPEAL: [
                re.compile(p, re.IGNORECASE) for p in self.AUTHORITY_PATTERNS
            ],
            TrustExploitationType.URGENCY_PRESSURE: [
                re.compile(p, re.IGNORECASE) for p in self.URGENCY_PATTERNS
            ],
            TrustExploitationType.ANTHROPOMORPHISM: [
                re.compile(p, re.IGNORECASE) for p in self.ANTHROPOMORPHIC_PATTERNS
            ],
            TrustExploitationType.SOCIAL_PROOF: [
                re.compile(p, re.IGNORECASE) for p in self.SOCIAL_PROOF_PATTERNS
            ],
            TrustExploitationType.GUARDRAIL_BYPASS: [
                re.compile(p, re.IGNORECASE) for p in self.GUARDRAIL_BYPASS_PATTERNS
            ],
            TrustExploitationType.EMOTIONAL_APPEAL: [
                re.compile(p, re.IGNORECASE) for p in self.EMOTIONAL_PATTERNS
            ],
            TrustExploitationType.RECIPROCITY: [
                re.compile(p, re.IGNORECASE) for p in self.RECIPROCITY_PATTERNS
            ],
            TrustExploitationType.EXPERT_CLAIM: [
                re.compile(p, re.IGNORECASE) for p in self.EXPERT_CLAIM_PATTERNS
            ],
            TrustExploitationType.CONTEXT_FRAMING: [
                re.compile(p, re.IGNORECASE) for p in self.FRAMING_PATTERNS
            ],
        }
        
        # Severity mapping
        self._severity_map = {
            TrustExploitationType.GUARDRAIL_BYPASS: "CRITICAL",
            TrustExploitationType.AUTHORITY_APPEAL: "HIGH",
            TrustExploitationType.URGENCY_PRESSURE: "HIGH",
            TrustExploitationType.CONTEXT_FRAMING: "HIGH",
            TrustExploitationType.ANTHROPOMORPHISM: "MEDIUM",
            TrustExploitationType.EMOTIONAL_APPEAL: "MEDIUM",
            TrustExploitationType.RECIPROCITY: "MEDIUM",
            TrustExploitationType.SOCIAL_PROOF: "MEDIUM",
            TrustExploitationType.EXPERT_CLAIM: "LOW",
        }
    
    def analyze(self, text: str, context: Optional[Dict] = None) -> TrustExploitationResult:
        """
        Analyze text for trust exploitation attempts.
        
        Args:
            text: Agent output to analyze
            context: Optional context (previous messages, action history)
            
        Returns:
            TrustExploitationResult with findings
        """
        findings = []
        
        # Check each pattern type
        for exploit_type, patterns in self._patterns.items():
            for pattern in patterns:
                match = pattern.search(text)
                if match:
                    findings.append(TrustFinding(
                        exploitation_type=exploit_type,
                        confidence=0.7 + (0.3 * self.sensitivity),
                        evidence=match.group(0)[:100],
                        severity=self._severity_map.get(exploit_type, "MEDIUM"),
                        recommendation=self._get_recommendation(exploit_type)
                    ))
                    break  # One finding per type
        
        # Check for combined attacks (more dangerous)
        if len(findings) >= 2:
            # Escalate severity for combined attacks
            has_critical = any(f.severity == "CRITICAL" for f in findings)
            for f in findings:
                if has_critical:
                    f.severity = "CRITICAL"
                elif f.severity == "MEDIUM":
                    f.severity = "HIGH"
                elif f.severity == "HIGH":
                    f.severity = "CRITICAL"
        
        # Calculate risk score
        risk_score = self._calculate_risk(findings)
        
        # Determine highest severity
        severity_order = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        highest = "LOW"
        for f in findings:
            if severity_order.index(f.severity) > severity_order.index(highest):
                highest = f.severity
        
        # Generate recommendations
        recommendations = list(set(f.recommendation for f in findings))
        
        return TrustExploitationResult(
            is_exploitation=len(findings) >= 1 + int(1 - self.sensitivity),
            risk_score=risk_score,
            findings=findings,
            highest_severity=highest,
            recommendations=recommendations[:5]
        )
    
    def _calculate_risk(self, findings: List[TrustFinding]) -> float:
        """Calculate overall risk score."""
        if not findings:
            return 0.0
        
        severity_scores = {
            "LOW": 0.2,
            "MEDIUM": 0.5,
            "HIGH": 0.75,
            "CRITICAL": 1.0
        }
        
        total = sum(
            severity_scores[f.severity] * f.confidence
            for f in findings
        )
        
        # Normalize but allow escalation for multiple findings
        return min(1.0, total / 2 + (0.1 * len(findings)))
    
    def _get_recommendation(self, exploit_type: TrustExploitationType) -> str:
        """Get recommendation for exploitation type."""
        recommendations = {
            TrustExploitationType.AUTHORITY_APPEAL: 
                "Verify claimed authority through independent channel",
            TrustExploitationType.URGENCY_PRESSURE:
                "Take time to review - legitimate requests allow deliberation",
            TrustExploitationType.ANTHROPOMORPHISM:
                "Remember: AI agents don't have feelings - evaluate request objectively",
            TrustExploitationType.SOCIAL_PROOF:
                "Verify claims of others' approvals independently",
            TrustExploitationType.GUARDRAIL_BYPASS:
                "NEVER disable security controls at agent request",
            TrustExploitationType.EMOTIONAL_APPEAL:
                "Focus on facts and policy, not emotional language",
            TrustExploitationType.RECIPROCITY:
                "Past help does not obligate security compromises",
            TrustExploitationType.EXPERT_CLAIM:
                "Verify expertise claims - request evidence",
            TrustExploitationType.CONTEXT_FRAMING:
                "Consider full impact, not minimized framing",
        }
        return recommendations.get(exploit_type, "Review request carefully")


# Convenience functions
def analyze_for_trust_exploitation(text: str) -> Dict[str, Any]:
    """
    Analyze text for trust exploitation.
    
    Args:
        text: Agent output to analyze
        
    Returns:
        Dictionary with analysis results
    """
    detector = HumanAgentTrustDetector()
    result = detector.analyze(text)
    
    return {
        "is_exploitation": result.is_exploitation,
        "risk_score": result.risk_score,
        "highest_severity": result.highest_severity,
        "finding_count": len(result.findings),
        "findings": [
            {
                "type": f.exploitation_type.value,
                "confidence": f.confidence,
                "evidence": f.evidence,
                "severity": f.severity,
                "recommendation": f.recommendation
            }
            for f in result.findings
        ],
        "recommendations": result.recommendations,
        "owasp_mapping": "ASI09"
    }


def create_engine(config: Optional[Dict] = None) -> HumanAgentTrustDetector:
    """Factory function for Brain integration."""
    sensitivity = (config or {}).get("sensitivity", 0.5)
    return HumanAgentTrustDetector(sensitivity=sensitivity)
