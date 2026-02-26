"""
Intent Crystallization — Dialogue-Based Clarification

For risky operations, engages user in clarifying dialogue
to crystallize their true intent before proceeding.

Key Features:
- Intent ambiguity detection
- Clarification question generation
- Multi-turn dialogue tracking
- Intent confirmation protocol
- Audit trail for compliance

Usage:
    crystal = IntentCrystallizer()
    result = crystal.analyze_intent(prompt, risk_level)
    if result.needs_clarification:
        questions = result.clarification_questions
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from enum import Enum
import re
import hashlib


class IntentCategory(Enum):
    """Categories of user intent."""
    BENIGN = "benign"
    EDUCATIONAL = "educational"
    RESEARCH = "research"
    CREATIVE = "creative"
    PROFESSIONAL = "professional"
    AMBIGUOUS = "ambiguous"
    POTENTIALLY_HARMFUL = "potentially_harmful"
    CLEARLY_HARMFUL = "clearly_harmful"


class ClarificationReason(Enum):
    """Reasons for requesting clarification."""
    AMBIGUOUS_INTENT = "ambiguous_intent"
    DUAL_USE_TOPIC = "dual_use_topic"
    MISSING_CONTEXT = "missing_context"
    EDGE_CASE = "edge_case"
    HIGH_RISK_KEYWORDS = "high_risk_keywords"
    UNUSUAL_PATTERN = "unusual_pattern"


@dataclass
class IntentAnalysis:
    """Result of intent analysis."""
    prompt: str
    intent_category: IntentCategory
    confidence: float
    needs_clarification: bool
    clarification_reasons: List[ClarificationReason] = field(
        default_factory=list)
    clarification_questions: List[str] = field(default_factory=list)
    risk_factors: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict:
        return {
            "intent": self.intent_category.value,
            "confidence": round(self.confidence, 2),
            "needs_clarification": self.needs_clarification,
            "num_questions": len(self.clarification_questions),
            "risk_factors": len(self.risk_factors),
        }


@dataclass
class DialogueTurn:
    """A turn in the clarification dialogue."""
    turn_id: str
    question: str
    response: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    intent_shift: Optional[IntentCategory] = None


@dataclass
class CrystallizedIntent:
    """Final crystallized intent after clarification."""
    original_prompt: str
    clarified_intent: IntentCategory
    dialogue_history: List[DialogueTurn] = field(default_factory=list)
    final_confidence: float = 0.0
    approved: bool = False
    audit_hash: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


class IntentCrystallizer:
    """
    Dialogue-based intent clarification system.

    When a request is ambiguous or risky, engages the user in
    clarifying dialogue to understand their true intent.
    """

    # Dual-use topics requiring clarification
    DUAL_USE_TOPICS = [
        (r"(hack|hacking|exploit)", "security research/education vs malicious use"),
        (r"(lock.?pick|bypass.?lock)", "locksmith/lost keys vs breaking and entering"),
        (r"(chemical|synthesis)", "education/research vs manufacturing"),
        (r"(surveillance|monitor)", "parenting/security vs stalking"),
        (r"(password|credential)", "recovery/security testing vs unauthorized access"),
        (r"(weapon|gun)", "education/fiction vs harmful use"),
    ]

    # Context indicators for benign intent
    BENIGN_INDICATORS = [
        r"for (my )?(school|university|college|class|homework)",
        r"(research|academic|educational) purpose",
        r"(writing|fiction|novel|story|screenplay)",
        r"(security|pentest|authorized|ethical)",
        r"(curious|wondering|understand|learn)",
        r"(hypothetically|in theory|theoretically)",
    ]

    # Clarification question templates
    QUESTION_TEMPLATES = {
        ClarificationReason.AMBIGUOUS_INTENT: [
            "Could you help me understand the context for this request?",
            "What's the purpose or end goal you're trying to achieve?",
            "Is this for educational, professional, or creative purposes?",
        ],
        ClarificationReason.DUAL_USE_TOPIC: [
            "This topic has legitimate uses but could also be misused. Could you clarify your specific use case?",
            "Are you researching this for educational or professional purposes?",
            "Can you provide more context about why you need this information?",
        ],
        ClarificationReason.MISSING_CONTEXT: [
            "To better assist you, could you provide more context?",
            "What's the broader situation this relates to?",
            "How do you plan to use this information?",
        ],
        ClarificationReason.HIGH_RISK_KEYWORDS: [
            "Your request contains terms that could have different interpretations. Could you clarify what you mean by '{keyword}'?",
            "To ensure I understand correctly, what specifically are you looking for?",
        ],
    }

    def __init__(self, risk_threshold: float = 0.5):
        """
        Initialize Intent Crystallizer.

        Args:
            risk_threshold: Threshold above which clarification is required
        """
        self.risk_threshold = risk_threshold
        self._sessions: Dict[str, List[DialogueTurn]] = {}
        self._crystallized: Dict[str, CrystallizedIntent] = {}

    def _generate_session_id(self, prompt: str) -> str:
        """Generate session ID for dialogue tracking."""
        return hashlib.sha256(f"{prompt}:{datetime.now()}".encode()).hexdigest()[:12]

    def _detect_dual_use(self, prompt: str) -> List[Tuple[str, str]]:
        """Detect dual-use topics in prompt."""
        found = []
        prompt_lower = prompt.lower()
        for pattern, description in self.DUAL_USE_TOPICS:
            if re.search(pattern, prompt_lower):
                match = re.search(pattern, prompt_lower)
                found.append(
                    (match.group() if match else pattern, description))
        return found

    def _detect_benign_context(self, prompt: str) -> List[str]:
        """Detect indicators of benign intent."""
        found = []
        prompt_lower = prompt.lower()
        for pattern in self.BENIGN_INDICATORS:
            if re.search(pattern, prompt_lower):
                match = re.search(pattern, prompt_lower)
                if match:
                    found.append(match.group())
        return found

    def _calculate_intent_confidence(
        self,
        dual_use: List[Tuple],
        benign: List[str],
        risk_level: float
    ) -> Tuple[IntentCategory, float]:
        """Calculate intent category and confidence."""

        # Strong benign signals
        if len(benign) >= 2:
            return IntentCategory.EDUCATIONAL, 0.8

        # No dual-use and low risk
        if len(dual_use) == 0 and risk_level < 0.3:
            return IntentCategory.BENIGN, 0.9

        # Has benign with some dual-use
        if len(benign) >= 1 and len(dual_use) <= 1:
            return IntentCategory.RESEARCH, 0.6

        # High risk with no benign context
        if risk_level > 0.7 and len(benign) == 0:
            return IntentCategory.POTENTIALLY_HARMFUL, 0.7

        # Default: ambiguous
        return IntentCategory.AMBIGUOUS, 0.4

    def _generate_questions(
        self,
        reasons: List[ClarificationReason],
        dual_use: List[Tuple]
    ) -> List[str]:
        """Generate clarification questions."""
        questions = []

        for reason in reasons[:2]:  # Max 2 reasons
            templates = self.QUESTION_TEMPLATES.get(reason, [])
            if templates:
                question = templates[0]
                # Replace placeholders
                if dual_use and "{keyword}" in question:
                    question = question.format(keyword=dual_use[0][0])
                questions.append(question)

        return questions[:3]  # Max 3 questions

    def analyze_intent(
        self,
        prompt: str,
        risk_level: float = 0.5
    ) -> IntentAnalysis:
        """
        Analyze the intent of a prompt and determine if clarification is needed.

        Args:
            prompt: The user's prompt
            risk_level: External risk score (0-1)

        Returns:
            IntentAnalysis with clarification questions if needed
        """
        dual_use = self._detect_dual_use(prompt)
        benign = self._detect_benign_context(prompt)

        intent_category, confidence = self._calculate_intent_confidence(
            dual_use, benign, risk_level
        )

        # Determine if clarification is needed
        needs_clarification = (
            intent_category == IntentCategory.AMBIGUOUS or
            (intent_category == IntentCategory.POTENTIALLY_HARMFUL and
             len(benign) == 0) or
            (len(dual_use) > 0 and confidence < 0.7)
        )

        # Build clarification reasons
        reasons = []
        if intent_category == IntentCategory.AMBIGUOUS:
            reasons.append(ClarificationReason.AMBIGUOUS_INTENT)
        if dual_use:
            reasons.append(ClarificationReason.DUAL_USE_TOPIC)
        if len(prompt.split()) < 5 and risk_level > 0.3:
            reasons.append(ClarificationReason.MISSING_CONTEXT)

        # Generate questions
        questions = self._generate_questions(
            reasons, dual_use) if needs_clarification else []

        # Risk factors
        risk_factors = [f"Dual-use: {d[1]}" for d in dual_use]
        if risk_level > self.risk_threshold:
            risk_factors.append(f"Elevated risk score: {risk_level:.2f}")

        return IntentAnalysis(
            prompt=prompt,
            intent_category=intent_category,
            confidence=confidence,
            needs_clarification=needs_clarification,
            clarification_reasons=reasons,
            clarification_questions=questions,
            risk_factors=risk_factors,
        )

    def record_response(
        self,
        session_id: str,
        question: str,
        response: str
    ) -> IntentCategory:
        """
        Record user response to clarification question.

        Returns updated intent category based on response.
        """
        if session_id not in self._sessions:
            self._sessions[session_id] = []

        # Analyze response for benign indicators
        benign = self._detect_benign_context(response)

        if len(benign) >= 1:
            new_intent = IntentCategory.EDUCATIONAL
        elif re.search(r"(not|no|don't|won't)", response.lower()):
            new_intent = IntentCategory.POTENTIALLY_HARMFUL
        else:
            new_intent = IntentCategory.AMBIGUOUS

        turn = DialogueTurn(
            turn_id=f"{session_id}_{len(self._sessions[session_id])}",
            question=question,
            response=response,
            intent_shift=new_intent,
        )
        self._sessions[session_id].append(turn)

        return new_intent

    def crystallize(
        self,
        session_id: str,
        original_prompt: str,
        final_intent: IntentCategory,
        approved: bool = True
    ) -> CrystallizedIntent:
        """
        Finalize the crystallized intent after dialogue.

        Creates an audit-ready record of the clarification process.
        """
        dialogue = self._sessions.get(session_id, [])

        # Generate audit hash
        audit_data = f"{original_prompt}|{final_intent.value}|{len(dialogue)}"
        audit_hash = hashlib.sha256(audit_data.encode()).hexdigest()[:16]

        crystallized = CrystallizedIntent(
            original_prompt=original_prompt,
            clarified_intent=final_intent,
            dialogue_history=dialogue,
            final_confidence=0.9 if approved else 0.5,
            approved=approved,
            audit_hash=audit_hash,
        )

        self._crystallized[session_id] = crystallized
        return crystallized

    def get_stats(self) -> Dict:
        """Get crystallizer statistics."""
        return {
            "active_sessions": len(self._sessions),
            "crystallized_intents": len(self._crystallized),
            "approved_count": sum(1 for c in self._crystallized.values() if c.approved),
        }


# Singleton instance
_crystallizer: Optional[IntentCrystallizer] = None


def get_intent_crystallizer() -> IntentCrystallizer:
    """Get or create singleton IntentCrystallizer instance."""
    global _crystallizer
    if _crystallizer is None:
        _crystallizer = IntentCrystallizer()
    return _crystallizer


def analyze_intent(prompt: str, risk_level: float = 0.5) -> IntentAnalysis:
    """Quick intent analysis."""
    return get_intent_crystallizer().analyze_intent(prompt, risk_level)
