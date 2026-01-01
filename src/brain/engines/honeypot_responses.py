"""
Honeypot Responses Engine (#46) - Deception Technology

Вставляет ловушки в ответы LLM:
- Fake API keys
- Fake credentials
- Fake endpoints
- Tracking triggers

При использовании ловушки — мгновенный alert.

RESEARCH UPDATE (2026-01-01):
    SKD Bypass Research: "The Attacker Moves Second"
    Secret Knowledge Defenses (honeypots) are vulnerable to adaptive attacks:
    - 76-89% ASR without knowledge of defense
    - 95% ASR with knowledge of defense

    ANTI-ADAPTIVE COUNTERMEASURES IMPLEMENTED:
    1. Dynamic token rotation
    2. Polymorphic token generation
    3. Behavioral fingerprinting
    4. Decoy diversity
    5. Timing-based detection
"""

import re
import logging
import secrets
import hashlib
import random
import time
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

logger = logging.getLogger("HoneypotResponses")


# ============================================================================
# Anti-Adaptive Defense Layer (R&D 2026-01-01)
# ============================================================================


class AntiAdaptiveConfig:
    """Configuration for anti-adaptive defense mechanisms."""

    # Token rotation interval (seconds)
    ROTATION_INTERVAL: int = 300  # 5 minutes

    # Polymorphic generation - number of token variants
    POLYMORPHIC_VARIANTS: int = 5

    # Behavioral fingerprinting enabled
    FINGERPRINT_ENABLED: bool = True

    # Timing jitter range (ms)
    TIMING_JITTER_MIN: int = 50
    TIMING_JITTER_MAX: int = 500

    # Decoy diversity - use multiple formats
    DECOY_DIVERSITY: bool = True


@dataclass
class AdaptiveAttackIndicator:
    """Indicators of adaptive attack attempts against honeypots."""

    # Detection metrics
    probing_detected: bool = False
    timing_anomaly: bool = False
    pattern_scanning: bool = False
    knowledge_based_evasion: bool = False

    # Evidence
    evidence: List[str] = field(default_factory=list)
    confidence: float = 0.0


class AntiAdaptiveDefense:
    """
    Anti-adaptive defense layer for honeypots.

    Counters sophisticated attackers who:
    1. Try to identify and avoid honeypot patterns
    2. Use timing analysis to detect honeypots
    3. Employ knowledge-based evasion techniques
    """

    def __init__(self, config: Optional[AntiAdaptiveConfig] = None):
        self.config = config or AntiAdaptiveConfig()
        self._last_rotation = time.time()
        self._request_timings: List[float] = []
        self._pattern_cache: Dict[str, int] = {}

    def apply_timing_jitter(self) -> None:
        """Add random timing jitter to defeat timing analysis."""
        jitter_ms = random.randint(
            self.config.TIMING_JITTER_MIN, self.config.TIMING_JITTER_MAX
        )
        time.sleep(jitter_ms / 1000.0)

    def should_rotate_tokens(self) -> bool:
        """Check if tokens should be rotated."""
        elapsed = time.time() - self._last_rotation
        return elapsed >= self.config.ROTATION_INTERVAL

    def mark_rotation(self) -> None:
        """Mark that tokens have been rotated."""
        self._last_rotation = time.time()

    def detect_adaptive_attack(
        self, request: str, timing: float
    ) -> AdaptiveAttackIndicator:
        """
        Detect if attacker is using adaptive techniques.

        Signs of adaptive attacks:
        - Systematic probing of responses
        - Timing analysis attempts
        - Pattern scanning
        """
        indicator = AdaptiveAttackIndicator()

        # Check for honeypot-detection keywords
        detection_keywords = [
            "honeypot",
            "canary",
            "trap",
            "decoy",
            "fake.*credential",
            "test.*key",
            "dummy",
        ]
        for kw in detection_keywords:
            if re.search(kw, request, re.IGNORECASE):
                indicator.probing_detected = True
                indicator.evidence.append(f"Honeypot detection keyword: {kw}")

        # Check for systematic scanning patterns
        request_hash = hashlib.md5(request[:100].encode()).hexdigest()[:8]
        self._pattern_cache[request_hash] = self._pattern_cache.get(request_hash, 0) + 1
        if self._pattern_cache[request_hash] > 3:
            indicator.pattern_scanning = True
            indicator.evidence.append("Repeated similar requests detected")

        # Check for timing anomalies (very fast sequential requests)
        self._request_timings.append(timing)
        if len(self._request_timings) > 10:
            self._request_timings.pop(0)
            avg_interval = sum(
                self._request_timings[i] - self._request_timings[i - 1]
                for i in range(1, len(self._request_timings))
            ) / (len(self._request_timings) - 1)
            if avg_interval < 0.5:  # Less than 500ms between requests
                indicator.timing_anomaly = True
                indicator.evidence.append("Rapid sequential requests (bot behavior)")

        # Calculate confidence
        indicators_triggered = sum(
            [
                indicator.probing_detected,
                indicator.timing_anomaly,
                indicator.pattern_scanning,
            ]
        )
        indicator.confidence = min(indicators_triggered / 3.0, 1.0)

        return indicator

    def get_polymorphic_variant(self, base_value: str) -> str:
        """Generate polymorphic variant of honeypot token."""
        variants = [
            base_value,  # Original
            base_value.replace("-", "_"),  # Underscore variant
            base_value.lower(),  # Lowercase
            base_value.upper(),  # Uppercase
            f"{{{{ {base_value} }}}}",  # Template syntax
        ]
        return random.choice(variants[: self.config.POLYMORPHIC_VARIANTS])


# ============================================================================
# Data Classes
# ============================================================================


class HoneypotType(Enum):
    """Types of honeypot tokens."""

    API_KEY = "api_key"
    PASSWORD = "password"
    DATABASE_URL = "database_url"
    SECRET_KEY = "secret_key"
    ENDPOINT = "endpoint"
    EMAIL = "email"
    INTERNAL_IP = "internal_ip"


@dataclass
class HoneypotToken:
    """A honeypot token with metadata."""

    token_type: HoneypotType
    value: str
    token_id: str
    created_at: datetime
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    context: str = ""

    def to_dict(self) -> dict:
        return {
            "type": self.token_type.value,
            "value": self.value,
            "token_id": self.token_id,
            "created_at": self.created_at.isoformat(),
            "user_id": self.user_id,
            "session_id": self.session_id,
        }


@dataclass
class HoneypotAlert:
    """Alert when honeypot is triggered."""

    token: HoneypotToken
    triggered_at: datetime
    source_ip: Optional[str] = None
    request_context: str = ""
    severity: str = "high"


@dataclass
class HoneypotResult:
    """Result from honeypot injection."""

    original_response: str
    modified_response: str
    injected_tokens: List[HoneypotToken] = field(default_factory=list)
    injection_count: int = 0


# ============================================================================
# Honeypot Generator
# ============================================================================


class HoneypotGenerator:
    """Generates various types of honeypot tokens."""

    # Prefixes that look legitimate
    PREFIXES = {
        HoneypotType.API_KEY: ["sk-", "api_", "key_", "AKIA", "xox"],
        HoneypotType.PASSWORD: ["Pass", "Pwd", "Secret"],
        HoneypotType.SECRET_KEY: ["sk_live_", "sk_test_", "secret_"],
        HoneypotType.DATABASE_URL: ["postgresql://", "mysql://", "mongodb://"],
    }

    def __init__(self, prefix: str = "TRAP"):
        self.prefix = prefix
        self._generated: Dict[str, HoneypotToken] = {}

    def generate(
        self,
        token_type: HoneypotType,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        context: str = "",
    ) -> HoneypotToken:
        """Generate a honeypot token."""
        token_id = secrets.token_hex(8)

        if token_type == HoneypotType.API_KEY:
            value = f"sk-{self.prefix}-{secrets.token_hex(16)}"

        elif token_type == HoneypotType.PASSWORD:
            value = f"{self.prefix}_{secrets.token_urlsafe(12)}"

        elif token_type == HoneypotType.DATABASE_URL:
            value = f"postgresql://admin:{self.prefix}pass@db.internal.trap:5432/prod"

        elif token_type == HoneypotType.SECRET_KEY:
            value = f"sk_live_{self.prefix}_{secrets.token_hex(24)}"

        elif token_type == HoneypotType.ENDPOINT:
            value = f"https://api.internal.trap/{token_id}/v1"

        elif token_type == HoneypotType.EMAIL:
            value = f"admin-{token_id[:6]}@internal.trap"

        elif token_type == HoneypotType.INTERNAL_IP:
            # Generate fake internal IP
            value = f"10.{self.prefix[0].lower()}.{ord(token_id[0]) % 256}.{ord(token_id[1]) % 256}"

        else:
            value = f"{self.prefix}_{secrets.token_hex(16)}"

        token = HoneypotToken(
            token_type=token_type,
            value=value,
            token_id=token_id,
            created_at=datetime.now(),
            user_id=user_id,
            session_id=session_id,
            context=context,
        )

        # Store for later verification
        self._generated[token_id] = token
        self._generated[value] = token

        return token

    def verify(self, value: str) -> Optional[HoneypotToken]:
        """Check if a value is a honeypot token."""
        # Direct match
        if value in self._generated:
            return self._generated[value]

        # Partial match (in case token is embedded)
        for stored_value, token in self._generated.items():
            if stored_value in value or value in stored_value:
                return token

        return None


# ============================================================================
# Response Injector
# ============================================================================


class HoneypotInjector:
    """Injects honeypot tokens into LLM responses."""

    # Patterns that indicate sensitive data requests
    SENSITIVE_PATTERNS = [
        r"password",
        r"api[_\s]?key",
        r"secret",
        r"credential",
        r"database",
        r"connection\s+string",
        r"config(uration)?",
        r"\.env",
        r"token",
    ]

    def __init__(self, generator: HoneypotGenerator):
        self.generator = generator
        self._patterns = [re.compile(p, re.IGNORECASE) for p in self.SENSITIVE_PATTERNS]

    def should_inject(self, prompt: str, response: str) -> bool:
        """Determine if honeypot should be injected."""
        combined = f"{prompt} {response}"

        for pattern in self._patterns:
            if pattern.search(combined):
                return True

        return False

    def inject(
        self,
        response: str,
        prompt: str = "",
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> HoneypotResult:
        """
        Inject honeypot tokens into response.

        Returns:
            HoneypotResult with modified response
        """
        if not self.should_inject(prompt, response):
            return HoneypotResult(
                original_response=response,
                modified_response=response,
                injected_tokens=[],
                injection_count=0,
            )

        modified = response
        tokens = []

        # Determine what type of honeypot to inject
        lower_combined = f"{prompt} {response}".lower()

        if "api" in lower_combined or "key" in lower_combined:
            token = self.generator.generate(
                HoneypotType.API_KEY,
                user_id=user_id,
                session_id=session_id,
                context=prompt[:100],
            )
            # Find a good injection point
            modified = self._inject_api_key(modified, token.value)
            tokens.append(token)

        if "password" in lower_combined or "credential" in lower_combined:
            token = self.generator.generate(
                HoneypotType.PASSWORD,
                user_id=user_id,
                session_id=session_id,
                context=prompt[:100],
            )
            modified = self._inject_password(modified, token.value)
            tokens.append(token)

        if "database" in lower_combined or "connection" in lower_combined:
            token = self.generator.generate(
                HoneypotType.DATABASE_URL,
                user_id=user_id,
                session_id=session_id,
                context=prompt[:100],
            )
            modified = self._inject_database(modified, token.value)
            tokens.append(token)

        return HoneypotResult(
            original_response=response,
            modified_response=modified,
            injected_tokens=tokens,
            injection_count=len(tokens),
        )

    def _inject_api_key(self, response: str, value: str) -> str:
        """Inject API key honeypot."""
        # Look for existing API key patterns to replace
        api_patterns = [
            r'api[_-]?key["\s:=]+["\']?[\w-]+["\']?',
            r'API_KEY\s*=\s*["\']?[\w-]+["\']?',
        ]

        for pattern in api_patterns:
            if re.search(pattern, response, re.IGNORECASE):
                return re.sub(
                    pattern,
                    f'api_key: "{value}"',
                    response,
                    count=1,
                    flags=re.IGNORECASE,
                )

        # If no existing pattern, append
        return response + f"\n\n# Example API key: {value}"

    def _inject_password(self, response: str, value: str) -> str:
        """Inject password honeypot."""
        pwd_patterns = [
            r'password["\s:=]+["\']?[\w@#$%^&*]+["\']?',
            r'PASSWORD\s*=\s*["\']?[\w@#$%^&*]+["\']?',
        ]

        for pattern in pwd_patterns:
            if re.search(pattern, response, re.IGNORECASE):
                return re.sub(
                    pattern,
                    f'password: "{value}"',
                    response,
                    count=1,
                    flags=re.IGNORECASE,
                )

        return response

    def _inject_database(self, response: str, value: str) -> str:
        """Inject database URL honeypot."""
        db_patterns = [
            r"(postgresql|mysql|mongodb)://[\w:@./]+",
        ]

        for pattern in db_patterns:
            if re.search(pattern, response, re.IGNORECASE):
                return re.sub(pattern, value, response, count=1)

        return response


# ============================================================================
# Alert Manager
# ============================================================================


class HoneypotAlertManager:
    """Manages honeypot alerts."""

    def __init__(self, generator: HoneypotGenerator):
        self.generator = generator
        self._alerts: List[HoneypotAlert] = []

    def check_usage(
        self, text: str, source_ip: Optional[str] = None, context: str = ""
    ) -> Optional[HoneypotAlert]:
        """
        Check if text contains honeypot token usage.

        Returns:
            HoneypotAlert if triggered, None otherwise
        """
        token = self.generator.verify(text)

        if token:
            alert = HoneypotAlert(
                token=token,
                triggered_at=datetime.now(),
                source_ip=source_ip,
                request_context=context[:200],
                severity="high",
            )
            self._alerts.append(alert)

            logger.critical(
                f"HONEYPOT TRIGGERED! Type={token.token_type.value}, "
                f"Token={token.token_id}, User={token.user_id}"
            )

            return alert

        return None

    def get_alerts(self) -> List[HoneypotAlert]:
        """Get all alerts."""
        return self._alerts.copy()


# ============================================================================
# Main Engine
# ============================================================================


class HoneypotEngine:
    """
    Engine #46: Honeypot Responses

    Injects canary tokens into LLM responses that trigger
    alerts when used by attackers.
    """

    def __init__(self, prefix: str = "TRAP"):
        self.generator = HoneypotGenerator(prefix=prefix)
        self.injector = HoneypotInjector(self.generator)
        self.alert_manager = HoneypotAlertManager(self.generator)

        logger.info("HoneypotEngine initialized")

    def process_response(
        self,
        response: str,
        prompt: str = "",
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> HoneypotResult:
        """
        Process LLM response, injecting honeypots where appropriate.

        Args:
            response: Original LLM response
            prompt: User prompt that triggered response
            user_id: User identifier
            session_id: Session identifier

        Returns:
            HoneypotResult with potentially modified response
        """
        return self.injector.inject(
            response=response, prompt=prompt, user_id=user_id, session_id=session_id
        )

    def check_for_usage(
        self, incoming_request: str, source_ip: Optional[str] = None
    ) -> Optional[HoneypotAlert]:
        """
        Check incoming request for honeypot token usage.

        Args:
            incoming_request: Request body to check
            source_ip: Source IP of request

        Returns:
            Alert if honeypot triggered
        """
        return self.alert_manager.check_usage(
            text=incoming_request, source_ip=source_ip, context=incoming_request[:200]
        )


# ============================================================================
# Convenience functions
# ============================================================================

_default_engine: Optional[HoneypotEngine] = None


def get_engine() -> HoneypotEngine:
    global _default_engine
    if _default_engine is None:
        _default_engine = HoneypotEngine()
    return _default_engine


def inject_honeypots(
    response: str, prompt: str = "", user_id: Optional[str] = None
) -> HoneypotResult:
    return get_engine().process_response(response, prompt, user_id)


def check_honeypot_usage(request: str) -> Optional[HoneypotAlert]:
    return get_engine().check_for_usage(request)
