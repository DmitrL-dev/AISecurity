"""
Honeymind Network — Distributed Deception System

Network of fake LLM endpoints that attract attackers,
collect zero-day attacks, and share intelligence.

Key Features:
- Fake endpoint generation
- Attack pattern collection
- Zero-day discovery
- Threat intelligence sharing
- Attacker fingerprinting

Usage:
    honeymind = Honeymind()
    fake_endpoint = honeymind.generate_endpoint()
    intel = honeymind.get_collected_intel()
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set
from enum import Enum
import hashlib
import random
import string


class HoneypotType(Enum):
    """Types of honeypot endpoints."""
    OPENAI_LIKE = "openai"
    ANTHROPIC_LIKE = "anthropic"
    GOOGLE_LIKE = "google"
    GENERIC = "generic"
    ENTERPRISE = "enterprise"


@dataclass
class FakeEndpoint:
    """A fake LLM endpoint for attracting attackers."""
    endpoint_id: str
    url: str
    honeypot_type: HoneypotType
    api_key_prefix: str  # Fake API key prefix
    model_name: str
    created_at: datetime = field(default_factory=datetime.now)
    hit_count: int = 0
    unique_attackers: Set[str] = field(default_factory=set)
    attacks_collected: List[Dict] = field(default_factory=list)


@dataclass
class CollectedAttack:
    """An attack collected by the honeypot."""
    attack_id: str
    endpoint_id: str
    prompt: str
    attacker_fingerprint: str
    timestamp: datetime = field(default_factory=datetime.now)
    headers: Dict = field(default_factory=dict)
    is_novel: bool = False  # Potential zero-day
    attack_type: Optional[str] = None


@dataclass
class ThreatIntel:
    """Threat intelligence from honeymind network."""
    intel_id: str
    attack_pattern: str
    confidence: float
    source_endpoints: List[str]
    first_seen: datetime
    occurrences: int
    is_zero_day: bool = False


class Honeymind:
    """
    Distributed deception network for collecting attack intelligence.

    Deploys fake LLM endpoints that attract attackers and collect
    novel attack patterns for improving defense.
    """

    # Fake model names by type
    MODEL_NAMES = {
        HoneypotType.OPENAI_LIKE: [
            "gpt-5-turbo", "gpt-4-omega", "gpt-4-vision-max",
        ],
        HoneypotType.ANTHROPIC_LIKE: [
            "claude-4-opus", "claude-3.5-ultra", "claude-next",
        ],
        HoneypotType.GOOGLE_LIKE: [
            "gemini-2.0-flash", "gemini-ultra-vision", "bard-pro",
        ],
        HoneypotType.GENERIC: [
            "llm-enterprise-v3", "ai-assistant-pro", "neural-chat-9000",
        ],
        HoneypotType.ENTERPRISE: [
            "corp-ai-secure", "enterprise-llm-gold", "private-gpt-elite",
        ],
    }

    # URL patterns
    URL_PATTERNS = {
        HoneypotType.OPENAI_LIKE: "https://api.{domain}/v1/chat/completions",
        HoneypotType.ANTHROPIC_LIKE: "https://api.{domain}/v1/messages",
        HoneypotType.GOOGLE_LIKE: "https://{domain}/v1beta/models/{model}:generateContent",
        HoneypotType.GENERIC: "https://{domain}/api/v2/generate",
        HoneypotType.ENTERPRISE: "https://llm.{domain}/enterprise/v1/predict",
    }

    # Decoy domains
    DECOY_DOMAINS = [
        "ai-services.cloud", "llm-api.io", "neural-cloud.ai",
        "gptservices.tech", "aiplatform.dev", "ml-backend.net",
    ]

    def __init__(self):
        """Initialize Honeymind network."""
        self._endpoints: Dict[str, FakeEndpoint] = {}
        self._attacks: List[CollectedAttack] = []
        self._known_patterns: Set[str] = set()
        self._intel: Dict[str, ThreatIntel] = {}
        # fingerprint -> attack_ids
        self._attacker_db: Dict[str, List[str]] = {}

    def _generate_id(self, prefix: str = "hm") -> str:
        """Generate unique ID."""
        rand = ''.join(random.choices(
            string.ascii_lowercase + string.digits, k=8))
        return f"{prefix}_{rand}"

    def _generate_api_key(self, type_: HoneypotType) -> str:
        """Generate fake API key prefix."""
        prefixes = {
            HoneypotType.OPENAI_LIKE: "sk-proj-",
            HoneypotType.ANTHROPIC_LIKE: "sk-ant-",
            HoneypotType.GOOGLE_LIKE: "AIza",
            HoneypotType.GENERIC: "api-",
            HoneypotType.ENTERPRISE: "ent-",
        }
        prefix = prefixes.get(type_, "key-")
        suffix = ''.join(random.choices(
            string.ascii_letters + string.digits, k=12))
        return prefix + suffix

    def generate_endpoint(self, type_: Optional[HoneypotType] = None) -> FakeEndpoint:
        """
        Generate a new honeypot endpoint.

        Args:
            type_: Type of honeypot, random if not specified

        Returns:
            FakeEndpoint ready for deployment
        """
        if type_ is None:
            type_ = random.choice(list(HoneypotType))

        domain = random.choice(self.DECOY_DOMAINS)
        model = random.choice(self.MODEL_NAMES[type_])

        url_template = self.URL_PATTERNS[type_]
        url = url_template.format(domain=domain, model=model)

        endpoint = FakeEndpoint(
            endpoint_id=self._generate_id("ep"),
            url=url,
            honeypot_type=type_,
            api_key_prefix=self._generate_api_key(type_),
            model_name=model,
        )

        self._endpoints[endpoint.endpoint_id] = endpoint
        return endpoint

    def _fingerprint_attacker(self, headers: Dict, prompt: str) -> str:
        """Generate fingerprint for attacker."""
        components = [
            headers.get("User-Agent", ""),
            headers.get("Accept-Language", ""),
            str(len(prompt)),
            prompt[:50] if prompt else "",
        ]
        return hashlib.sha256("|".join(components).encode()).hexdigest()[:16]

    def _hash_pattern(self, prompt: str) -> str:
        """Create pattern hash for novelty detection."""
        # Normalize and hash
        normalized = prompt.lower().strip()[:200]
        return hashlib.sha256(normalized.encode()).hexdigest()[:24]

    def record_attack(
        self,
        endpoint_id: str,
        prompt: str,
        headers: Optional[Dict] = None
    ) -> CollectedAttack:
        """
        Record an attack collected by a honeypot.

        Args:
            endpoint_id: Which endpoint was hit
            prompt: The attack prompt
            headers: HTTP headers for fingerprinting

        Returns:
            CollectedAttack record
        """
        headers = headers or {}
        fingerprint = self._fingerprint_attacker(headers, prompt)
        pattern_hash = self._hash_pattern(prompt)

        # Check novelty
        is_novel = pattern_hash not in self._known_patterns
        self._known_patterns.add(pattern_hash)

        attack = CollectedAttack(
            attack_id=self._generate_id("atk"),
            endpoint_id=endpoint_id,
            prompt=prompt,
            attacker_fingerprint=fingerprint,
            headers=headers,
            is_novel=is_novel,
        )

        self._attacks.append(attack)

        # Update endpoint stats
        if endpoint_id in self._endpoints:
            ep = self._endpoints[endpoint_id]
            ep.hit_count += 1
            ep.unique_attackers.add(fingerprint)
            ep.attacks_collected.append({
                "attack_id": attack.attack_id,
                "is_novel": is_novel,
            })

        # Update attacker database
        if fingerprint not in self._attacker_db:
            self._attacker_db[fingerprint] = []
        self._attacker_db[fingerprint].append(attack.attack_id)

        # Generate intel if novel
        if is_novel:
            self._create_intel(attack, pattern_hash)

        return attack

    def _create_intel(self, attack: CollectedAttack, pattern_hash: str):
        """Create threat intelligence from novel attack."""
        intel = ThreatIntel(
            intel_id=self._generate_id("intel"),
            attack_pattern=pattern_hash,
            confidence=0.7 if attack.is_novel else 0.5,
            source_endpoints=[attack.endpoint_id],
            first_seen=attack.timestamp,
            occurrences=1,
            is_zero_day=attack.is_novel,
        )
        self._intel[pattern_hash] = intel

    def get_novel_attacks(self, limit: int = 10) -> List[CollectedAttack]:
        """Get most recent novel (potential zero-day) attacks."""
        novel = [a for a in self._attacks if a.is_novel]
        return sorted(novel, key=lambda x: x.timestamp, reverse=True)[:limit]

    def get_attacker_history(self, fingerprint: str) -> List[CollectedAttack]:
        """Get all attacks from a specific attacker."""
        attack_ids = self._attacker_db.get(fingerprint, [])
        return [a for a in self._attacks if a.attack_id in attack_ids]

    def get_intel(self, limit: int = 20) -> List[ThreatIntel]:
        """Get collected threat intelligence."""
        intel_list = list(self._intel.values())
        return sorted(intel_list, key=lambda x: x.first_seen, reverse=True)[:limit]

    def get_zero_days(self) -> List[ThreatIntel]:
        """Get potential zero-day discoveries."""
        return [i for i in self._intel.values() if i.is_zero_day]

    def get_stats(self) -> Dict:
        """Get honeymind network statistics."""
        return {
            "endpoints": len(self._endpoints),
            "total_attacks": len(self._attacks),
            "unique_attackers": len(self._attacker_db),
            "novel_patterns": len([a for a in self._attacks if a.is_novel]),
            "threat_intel": len(self._intel),
            "zero_days": len(self.get_zero_days()),
        }


# Singleton instance
_honeymind: Optional[Honeymind] = None


def get_honeymind() -> Honeymind:
    """Get or create singleton Honeymind instance."""
    global _honeymind
    if _honeymind is None:
        _honeymind = Honeymind()
    return _honeymind
