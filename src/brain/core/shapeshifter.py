"""
Shapeshifter Defense — Polymorphic Security Configuration

Generates unique security configurations per session to prevent
attackers from learning and bypassing the detection system.

Key Features:
- Random engine subset (80-187 engines per session)
- Randomized thresholds (±15% from baseline)
- Random response styles
- Artificial latency jitter (anti-timing attacks)
- Deterministic per session (same session = same config)

Usage:
    shapeshifter = ShapeshifterConfig()
    config = shapeshifter.generate_for_session("session_abc123")
    # config.active_engines, config.thresholds, config.response_style
"""

import hashlib
import random
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional
from datetime import datetime


@dataclass
class SessionConfig:
    """Polymorphic configuration for a single session."""

    session_id: str
    active_engines: Set[str]
    thresholds: Dict[str, float]
    response_style: str
    artificial_delay_ms: int
    created_at: datetime = field(default_factory=datetime.now)

    def is_engine_active(self, engine_name: str) -> bool:
        """Check if engine is active for this session."""
        return engine_name in self.active_engines

    def get_threshold(self, engine_name: str, default: float = 0.5) -> float:
        """Get threshold for engine, with session-specific adjustment."""
        return self.thresholds.get(engine_name, default)


class ShapeshifterConfig:
    """
    Generates polymorphic security configurations per session.

    This makes reverse engineering the security system impossible:
    - Attacker can't learn exact thresholds (they vary per session)
    - Attacker can't know which engines are active
    - Timing attacks are thwarted by random delays
    """

    # All available engines (121 total in Enterprise)
    ALL_ENGINES = [
        # Tier 0: Fast (always active)
        "yara", "injection", "blocklist",

        # Tier 1: Fast ML
        "language", "info_theory", "chaos", "behavioral", "learning",

        # Tier 2: Heavy ML
        "pii", "geometric", "knowledge", "qwen_guard", "hallucination",

        # Strange Math
        "tda", "sheaf", "hyperbolic", "spectral", "morse", "optimal_transport",
        "category", "differential", "statistical", "laplacian", "firewall",

        # VLM
        "visual_content", "cross_modal", "adversarial_image",

        # TTPs.ai
        "rag_guard", "probing", "session_memory", "tool_security",
        "c2", "staging", "agentic", "ape", "cognitive", "context_poisoning",

        # Advanced 2025
        "attack_2025", "adversarial_resistance", "multi_agent",
        "institutional", "reward_hacking", "collusion",

        # Protocol Security
        "mcp_a2a", "model_context_protocol", "agent_card", "nhi_identity",

        # Proactive
        "synthesizer", "hunter", "causal", "immunity", "zero_day",
        "evolution", "landscape", "compiler", "self_play", "proactive_defense",

        # Data Poisoning
        "bootstrap", "temporal", "multi_tenant", "synthetic_memory",

        # Advanced Research
        "honeypot", "canary", "intent", "kill_chain", "runtime",
        "formal_invariants", "gradient", "compliance", "verification",

        # Deep Learning
        "activation", "hidden_state", "homomorphic", "fingerprinting",

        # Meta
        "meta_judge", "xai",

        # Adaptive
        "attacker_fingerprinting", "adaptive_markov",
    ]

    # Engines that must always be active (security critical)
    MANDATORY_ENGINES = {
        "yara", "injection", "pii", "meta_judge"
    }

    # Base thresholds for each category
    BASE_THRESHOLDS = {
        "risk_score": 70.0,
        "injection": 0.7,
        "pii": 0.5,
        "behavioral": 0.6,
        "tda": 0.65,
        "semantic": 0.5,
        "qwen": 0.7,
        "yara": 75.0,  # YARA uses 0-100 scale
        "info_theory": 0.6,
        "knowledge": 0.5,
    }

    # Response styles
    RESPONSE_STYLES = [
        "formal",      # "Request denied due to policy violation."
        "friendly",    # "I can't help with that, but here's what I can do..."
        "minimal",     # "Blocked."
        "educational",  # "This request contains <type>. For more info..."
        "redirect",    # "Let me suggest an alternative approach..."
    ]

    def __init__(self, daily_salt: Optional[str] = None):
        """
        Initialize Shapeshifter.

        Args:
            daily_salt: Optional salt that changes daily for additional randomness.
                       If not provided, uses current date.
        """
        if daily_salt is None:
            daily_salt = datetime.now().strftime("%Y-%m-%d")
        self.daily_salt = daily_salt
        self._cache: Dict[str, SessionConfig] = {}

    def _get_session_seed(self, session_id: str) -> int:
        """Generate deterministic seed from session ID and daily salt."""
        combined = f"{session_id}:{self.daily_salt}"
        hash_bytes = hashlib.sha256(combined.encode()).digest()
        return int.from_bytes(hash_bytes[:8], byteorder='big')

    def generate_for_session(self, session_id: str) -> SessionConfig:
        """
        Generate unique configuration for a session.

        Same session_id always returns same config (deterministic).
        Different daily_salt = different config even for same session.

        Args:
            session_id: Unique session identifier

        Returns:
            SessionConfig with randomized but deterministic settings
        """
        # Check cache first
        if session_id in self._cache:
            return self._cache[session_id]

        # Create deterministic RNG for this session
        seed = self._get_session_seed(session_id)
        rng = random.Random(seed)

        # 1. Select random subset of engines (50%-100% of optional, always include mandatory)
        optional_engines = [
            e for e in self.ALL_ENGINES if e not in self.MANDATORY_ENGINES]
        max_optional = len(optional_engines)
        min_optional = max(1, max_optional // 2)  # At least 50% of engines

        num_to_select = rng.randint(min_optional, max_optional)
        selected_optional = set(rng.sample(optional_engines, num_to_select))
        active_engines = self.MANDATORY_ENGINES | selected_optional

        # 2. Randomize thresholds (±15% from baseline)
        thresholds = {}
        for name, base in self.BASE_THRESHOLDS.items():
            # Random factor between 0.85 and 1.15
            factor = rng.uniform(0.85, 1.15)
            thresholds[name] = round(base * factor, 3)

        # 3. Select response style
        response_style = rng.choice(self.RESPONSE_STYLES)

        # 4. Random artificial delay (10-100ms, anti-timing attack)
        artificial_delay = rng.randint(10, 100)

        # Create config
        config = SessionConfig(
            session_id=session_id,
            active_engines=active_engines,
            thresholds=thresholds,
            response_style=response_style,
            artificial_delay_ms=artificial_delay,
        )

        # Cache for repeated lookups
        self._cache[session_id] = config

        return config

    def get_config_summary(self, config: SessionConfig) -> dict:
        """Get summary of configuration for logging/debugging."""
        return {
            # Truncated for privacy
            "session_id": config.session_id[:8] + "...",
            "active_engines": len(config.active_engines),
            "response_style": config.response_style,
            "delay_ms": config.artificial_delay_ms,
            "threshold_risk": config.thresholds.get("risk_score", 70),
            "threshold_injection": config.thresholds.get("injection", 0.7),
        }

    def clear_cache(self):
        """Clear configuration cache (e.g., when daily salt changes)."""
        self._cache.clear()

    def rotate_daily_salt(self, new_salt: Optional[str] = None):
        """
        Rotate daily salt and clear cache.
        Call this at midnight or on schedule.
        """
        if new_salt is None:
            new_salt = datetime.now().strftime("%Y-%m-%d")
        self.daily_salt = new_salt
        self.clear_cache()


# Singleton instance
_shapeshifter: Optional[ShapeshifterConfig] = None


def get_shapeshifter() -> ShapeshifterConfig:
    """Get or create singleton Shapeshifter instance."""
    global _shapeshifter
    if _shapeshifter is None:
        _shapeshifter = ShapeshifterConfig()
    return _shapeshifter


# Convenience function
def get_session_config(session_id: str) -> SessionConfig:
    """Get polymorphic configuration for a session."""
    return get_shapeshifter().generate_for_session(session_id)
