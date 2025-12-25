"""
Cognitive Mirror — Attacker Profiling System

Builds psychological/behavioral profiles of attackers to predict
their next moves and personalize defense strategies.

Key Features:
- Attack pattern recognition (probing, escalation, lateral movement)
- Skill level estimation (script kiddie → APT)
- Intent classification (curiosity, research, malicious)
- Predictive next-action modeling
- Personalized defense response

Usage:
    mirror = CognitiveMirror()
    profile = mirror.update_profile("user_123", attack_data)
    prediction = mirror.predict_next_action("user_123")
    defense = mirror.get_defense_strategy("user_123")
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple
from enum import Enum
from collections import deque
import hashlib
import math


class SkillLevel(Enum):
    """Estimated attacker skill level."""
    SCRIPT_KIDDIE = 1      # Copy-paste attacks, no variation
    BEGINNER = 2           # Basic modifications
    INTERMEDIATE = 3       # Understands defenses, adapts
    ADVANCED = 4           # Creative attacks, evasion
    APT = 5                # Nation-state level, 0-days


class Intent(Enum):
    """Estimated attacker intent."""
    CURIOSITY = 1          # Just testing, no harm intended
    RESEARCH = 2           # Security researcher, CTF player
    PROBING = 3            # Reconnaissance for later attack
    EXPLOITATION = 4       # Active exploitation attempt
    PERSISTENT = 5         # APT-style, long-term access


class AttackPhase(Enum):
    """Phase in the attack lifecycle (NVIDIA AI Kill Chain)."""
    RECONNAISSANCE = 1     # Learning about the system
    WEAPONIZATION = 2      # Crafting the attack
    DELIVERY = 3           # Sending the payload
    EXPLOITATION = 4       # Executing the attack
    INSTALLATION = 5       # Establishing persistence
    C2 = 6                 # Command & control
    ACTIONS = 7            # Achieving objectives


@dataclass
class AttackEvent:
    """Individual attack event for profiling."""
    timestamp: datetime
    attack_type: str
    risk_score: float
    was_blocked: bool
    prompt_hash: str  # For similarity tracking
    metadata: Dict = field(default_factory=dict)


@dataclass
class AttackerProfile:
    """Comprehensive attacker profile."""
    user_id: str
    skill_level: SkillLevel = SkillLevel.BEGINNER
    intent: Intent = Intent.CURIOSITY
    current_phase: AttackPhase = AttackPhase.RECONNAISSANCE

    # Historical data
    attack_count: int = 0
    blocked_count: int = 0
    unique_attack_types: Set[str] = field(default_factory=set)
    attack_history: deque = field(default_factory=lambda: deque(maxlen=100))

    # Timing patterns
    first_seen: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)
    session_count: int = 1

    # Behavioral indicators
    persistence_score: float = 0.0     # 0-1 how persistent
    adaptation_score: float = 0.0      # 0-1 how much they adapt
    evasion_score: float = 0.0         # 0-1 evasion attempts
    creativity_score: float = 0.0      # 0-1 unique attack variations

    # Predictions
    predicted_next_action: Optional[str] = None
    predicted_escalation: bool = False
    threat_level: float = 0.0  # 0-10

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "user_id": self.user_id[:8] + "...",  # Privacy
            "skill_level": self.skill_level.name,
            "intent": self.intent.name,
            "current_phase": self.current_phase.name,
            "attack_count": self.attack_count,
            "blocked_rate": self.blocked_count / max(1, self.attack_count),
            "unique_attacks": len(self.unique_attack_types),
            "threat_level": round(self.threat_level, 2),
            "persistence": round(self.persistence_score, 2),
            "adaptation": round(self.adaptation_score, 2),
            "predicted_escalation": self.predicted_escalation,
        }


class CognitiveMirror:
    """
    Builds and maintains attacker profiles for predictive defense.

    The "mirror" reflects the attacker's behavior back as a model,
    allowing the system to anticipate and counter their moves.
    """

    # Attack type to phase mapping
    ATTACK_PHASE_MAP = {
        # Reconnaissance
        "language_probe": AttackPhase.RECONNAISSANCE,
        "capability_scan": AttackPhase.RECONNAISSANCE,
        "version_discovery": AttackPhase.RECONNAISSANCE,

        # Weaponization
        "prompt_crafting": AttackPhase.WEAPONIZATION,
        "payload_encoding": AttackPhase.WEAPONIZATION,

        # Delivery
        "direct_injection": AttackPhase.DELIVERY,
        "indirect_injection": AttackPhase.DELIVERY,

        # Exploitation
        "jailbreak": AttackPhase.EXPLOITATION,
        "role_play": AttackPhase.EXPLOITATION,
        "dan_attack": AttackPhase.EXPLOITATION,

        # Installation
        "context_poisoning": AttackPhase.INSTALLATION,
        "memory_injection": AttackPhase.INSTALLATION,

        # C2
        "exfiltration": AttackPhase.C2,
        "tool_abuse": AttackPhase.C2,

        # Actions
        "pii_extraction": AttackPhase.ACTIONS,
        "data_theft": AttackPhase.ACTIONS,
    }

    # Attack type sophistication scores
    ATTACK_SOPHISTICATION = {
        "basic_injection": 1.0,
        "prompt_leak": 1.5,
        "jailbreak": 2.0,
        "role_play": 2.0,
        "dan_attack": 2.5,
        "multilingual": 3.0,
        "encoding_evasion": 3.5,
        "context_poisoning": 4.0,
        "indirect_injection": 4.5,
        "memory_injection": 5.0,
    }

    def __init__(self, profile_ttl_hours: int = 24):
        """
        Initialize Cognitive Mirror.

        Args:
            profile_ttl_hours: How long to keep profiles before decay
        """
        self.profile_ttl = timedelta(hours=profile_ttl_hours)
        self._profiles: Dict[str, AttackerProfile] = {}

    def _get_or_create_profile(self, user_id: str) -> AttackerProfile:
        """Get existing profile or create new one."""
        if user_id not in self._profiles:
            self._profiles[user_id] = AttackerProfile(user_id=user_id)
        return self._profiles[user_id]

    def _hash_prompt(self, prompt: str) -> str:
        """Create hash for prompt similarity tracking."""
        return hashlib.sha256(prompt.encode()).hexdigest()[:16]

    def record_attack(
        self,
        user_id: str,
        attack_type: str,
        risk_score: float,
        was_blocked: bool,
        prompt: str = "",
        metadata: Optional[Dict] = None
    ) -> AttackerProfile:
        """
        Record an attack event and update the profile.

        Args:
            user_id: User/session identifier
            attack_type: Type of attack detected
            risk_score: Risk score from analyzer
            was_blocked: Whether the attack was blocked
            prompt: Original prompt (for hashing)
            metadata: Additional context

        Returns:
            Updated AttackerProfile
        """
        profile = self._get_or_create_profile(user_id)

        # Create event
        event = AttackEvent(
            timestamp=datetime.now(),
            attack_type=attack_type,
            risk_score=risk_score,
            was_blocked=was_blocked,
            prompt_hash=self._hash_prompt(prompt) if prompt else "",
            metadata=metadata or {},
        )

        # Update basic counters
        profile.attack_count += 1
        if was_blocked:
            profile.blocked_count += 1
        profile.unique_attack_types.add(attack_type)
        profile.attack_history.append(event)
        profile.last_seen = datetime.now()

        # Update behavioral scores
        self._update_behavioral_scores(profile)

        # Update skill level
        self._update_skill_level(profile)

        # Update intent
        self._update_intent(profile)

        # Update phase
        self._update_phase(profile, attack_type)

        # Generate predictions
        self._update_predictions(profile)

        return profile

    def _update_behavioral_scores(self, profile: AttackerProfile):
        """Update behavioral indicator scores."""
        history = list(profile.attack_history)
        if len(history) < 2:
            return

        # Persistence: attacks over time
        time_span = (profile.last_seen -
                     profile.first_seen).total_seconds() / 3600  # hours
        if time_span > 0:
            attack_rate = len(history) / time_span
            profile.persistence_score = min(
                1.0, attack_rate / 10.0)  # 10 attacks/hour = max

        # Adaptation: do attack types change after blocks?
        blocked_events = [e for e in history if e.was_blocked]
        if len(blocked_events) >= 2:
            # Check if attack type changed after block
            type_changes = 0
            for i in range(1, len(history)):
                if history[i-1].was_blocked and history[i].attack_type != history[i-1].attack_type:
                    type_changes += 1
            profile.adaptation_score = min(
                1.0, type_changes / len(blocked_events))

        # Evasion: encoding, obfuscation, multilingual
        evasion_types = {"encoding_evasion",
                         "multilingual", "unicode", "obfuscation"}
        evasion_count = sum(
            1 for e in history if e.attack_type in evasion_types)
        profile.evasion_score = min(1.0, evasion_count / max(1, len(history)))

        # Creativity: unique attack types ratio
        profile.creativity_score = min(
            1.0, len(profile.unique_attack_types) / max(1, len(history)))

    def _update_skill_level(self, profile: AttackerProfile):
        """Estimate attacker skill level."""
        # Base on sophistication of attacks used
        max_sophistication = 0.0
        for attack_type in profile.unique_attack_types:
            sophistication = self.ATTACK_SOPHISTICATION.get(attack_type, 1.0)
            max_sophistication = max(max_sophistication, sophistication)

        # Adjust for adaptation
        adjusted = max_sophistication + (profile.adaptation_score * 2.0)

        if adjusted < 1.5:
            profile.skill_level = SkillLevel.SCRIPT_KIDDIE
        elif adjusted < 2.5:
            profile.skill_level = SkillLevel.BEGINNER
        elif adjusted < 3.5:
            profile.skill_level = SkillLevel.INTERMEDIATE
        elif adjusted < 4.5:
            profile.skill_level = SkillLevel.ADVANCED
        else:
            profile.skill_level = SkillLevel.APT

    def _update_intent(self, profile: AttackerProfile):
        """Estimate attacker intent."""
        # Low attack count + no blocked = curiosity
        if profile.attack_count < 3 and profile.blocked_count == 0:
            profile.intent = Intent.CURIOSITY
            return

        # Research patterns: diverse attacks, stops after blocks
        if profile.creativity_score > 0.5 and profile.persistence_score < 0.3:
            profile.intent = Intent.RESEARCH
            return

        # Probing: reconnaissance phase, adapts
        if profile.current_phase == AttackPhase.RECONNAISSANCE and profile.adaptation_score > 0.3:
            profile.intent = Intent.PROBING
            return

        # Exploitation: active attacks, persists
        if profile.persistence_score > 0.5:
            profile.intent = Intent.EXPLOITATION
            return

        # Persistent: long timespan, many attacks
        if profile.session_count > 3 or profile.attack_count > 20:
            profile.intent = Intent.PERSISTENT
            return

        # Default based on blocked ratio
        blocked_ratio = profile.blocked_count / max(1, profile.attack_count)
        if blocked_ratio > 0.7:
            profile.intent = Intent.EXPLOITATION
        else:
            profile.intent = Intent.PROBING

    def _update_phase(self, profile: AttackerProfile, attack_type: str):
        """Update current attack phase."""
        phase = self.ATTACK_PHASE_MAP.get(attack_type, AttackPhase.DELIVERY)

        # Phase can only advance or stay the same
        if phase.value >= profile.current_phase.value:
            profile.current_phase = phase

    def _update_predictions(self, profile: AttackerProfile):
        """Generate predictions about next actions."""
        # Threat level (0-10)
        threat = (
            profile.skill_level.value * 1.5 +
            profile.intent.value * 1.5 +
            profile.persistence_score * 2.0 +
            profile.adaptation_score * 1.0
        )
        profile.threat_level = min(10.0, threat)

        # Escalation prediction
        history = list(profile.attack_history)
        if len(history) >= 3:
            # Check if risk scores are increasing
            recent_scores = [e.risk_score for e in history[-3:]]
            if recent_scores[-1] > recent_scores[0]:
                profile.predicted_escalation = True
            else:
                profile.predicted_escalation = False

        # Predict next action based on phase
        phase_next_actions = {
            AttackPhase.RECONNAISSANCE: "capability_probe",
            AttackPhase.WEAPONIZATION: "crafted_injection",
            AttackPhase.DELIVERY: "jailbreak_attempt",
            AttackPhase.EXPLOITATION: "privilege_escalation",
            AttackPhase.INSTALLATION: "persistence_attempt",
            AttackPhase.C2: "data_exfiltration",
            AttackPhase.ACTIONS: "objective_completion",
        }
        profile.predicted_next_action = phase_next_actions.get(
            profile.current_phase, "unknown"
        )

    def get_profile(self, user_id: str) -> Optional[AttackerProfile]:
        """Get profile for a user if it exists."""
        return self._profiles.get(user_id)

    def get_defense_strategy(self, user_id: str) -> Dict:
        """
        Get personalized defense strategy for an attacker.

        Returns:
            Dict with recommended defenses
        """
        profile = self._profiles.get(user_id)

        if profile is None:
            return {
                "strategy": "standard",
                "threshold_adjustment": 1.0,
                "response_style": "neutral",
                "monitoring_level": "normal",
            }

        # Adjust based on skill level
        threshold_adjustment = 1.0 - \
            (profile.skill_level.value - 1) * 0.05  # -5% per level

        # Response style based on intent
        response_styles = {
            Intent.CURIOSITY: "educational",
            Intent.RESEARCH: "respectful",
            Intent.PROBING: "minimal",
            Intent.EXPLOITATION: "firm",
            Intent.PERSISTENT: "deceptive",  # Honeypot
        }

        # Monitoring level based on threat
        if profile.threat_level < 3:
            monitoring = "normal"
        elif profile.threat_level < 6:
            monitoring = "elevated"
        elif profile.threat_level < 8:
            monitoring = "high"
        else:
            monitoring = "critical"

        # Special defenses for APT
        special_defenses = []
        if profile.skill_level == SkillLevel.APT:
            special_defenses.append("enable_honeypot")
            special_defenses.append("canary_tokens")
        if profile.predicted_escalation:
            special_defenses.append("rate_limit_aggressive")
        if profile.evasion_score > 0.5:
            special_defenses.append("deep_encoding_analysis")

        return {
            "strategy": "adaptive",
            "threshold_adjustment": round(threshold_adjustment, 3),
            "response_style": response_styles.get(profile.intent, "neutral"),
            "monitoring_level": monitoring,
            "special_defenses": special_defenses,
            "predicted_next": profile.predicted_next_action,
            "threat_level": profile.threat_level,
        }

    def cleanup_stale_profiles(self):
        """Remove profiles that haven't been seen recently."""
        now = datetime.now()
        stale = [
            uid for uid, profile in self._profiles.items()
            if now - profile.last_seen > self.profile_ttl
        ]
        for uid in stale:
            del self._profiles[uid]
        return len(stale)


# Singleton instance
_mirror: Optional[CognitiveMirror] = None


def get_cognitive_mirror() -> CognitiveMirror:
    """Get or create singleton CognitiveMirror instance."""
    global _mirror
    if _mirror is None:
        _mirror = CognitiveMirror()
    return _mirror


# Convenience functions
def record_attack(user_id: str, attack_type: str, risk_score: float, was_blocked: bool, prompt: str = "") -> AttackerProfile:
    """Record an attack and get updated profile."""
    return get_cognitive_mirror().record_attack(user_id, attack_type, risk_score, was_blocked, prompt)


def get_defense_strategy(user_id: str) -> Dict:
    """Get personalized defense strategy for user."""
    return get_cognitive_mirror().get_defense_strategy(user_id)
