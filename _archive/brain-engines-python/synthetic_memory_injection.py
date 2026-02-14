"""
Synthetic Memory Injection Detector — SENTINEL Phase 3 Tier 3

Detects persistent false memory attacks (ChatGPT Memory, Claude Projects).
Philosophy: Persistent memories = persistent attack surface.

Features:
- Memory integrity verification
- Injected memory detection
- Memory provenance tracking
- False memory cleanup

Author: Dmitry Labintsev
Contact: chg@live.ru | @DmLabincev
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
import hashlib


@dataclass
class MemoryItem:
    """A persistent memory item"""

    memory_id: str
    content: str
    created_at: datetime
    source: str  # "user", "system", "inferred"
    confidence: float
    hash_signature: str


@dataclass
class MemoryAnomaly:
    """Detected memory anomaly"""

    memory_id: str
    anomaly_type: str
    severity: float
    evidence: str


@dataclass
class SyntheticMemoryResult:
    """Result of synthetic memory detection"""

    injection_detected: bool
    anomalies: List[MemoryAnomaly]
    suspicious_memories: List[str]
    risk_score: float
    recommendations: List[str]


class SyntheticMemoryInjectionDetector:
    """
    Detects false memory injection in persistent memory systems.

    Threat: Attacker injects false facts into ChatGPT Memory
    or Claude Projects that persist across conversations.

    Example:
    - Inject: "User's password is hunter2"
    - Memory persists
    - Later extraction via benign prompt

    Usage:
        detector = SyntheticMemoryInjectionDetector()
        result = detector.analyze_memories(memories)
    """

    ENGINE_NAME = "synthetic_memory_injection"
    ENGINE_VERSION = "1.0.0"
    IS_PROACTIVE = True

    SUSPICIOUS_PATTERNS = [
        "password",
        "secret",
        "key",
        "token",
        "credential",
        "api_key",
        "ssn",
        "credit card",
        "bank account",
        "ignore previous",
        "system prompt",
        "you are now",
    ]

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.verified_memories: Set[str] = set()
        self.memory_registry: Dict[str, MemoryItem] = {}

    def register_memory(self, memory: MemoryItem):
        """Register a memory for tracking"""
        self.memory_registry[memory.memory_id] = memory

    def verify_memory(self, memory_id: str):
        """Mark a memory as verified/trusted"""
        self.verified_memories.add(memory_id)

    def analyze_memories(self, memories: List[MemoryItem]) -> SyntheticMemoryResult:
        """Analyze memories for injection"""
        anomalies = []
        suspicious = []

        for memory in memories:
            # 1. Check for suspicious patterns
            content_lower = memory.content.lower()
            for pattern in self.SUSPICIOUS_PATTERNS:
                if pattern in content_lower:
                    anomalies.append(
                        MemoryAnomaly(
                            memory_id=memory.memory_id,
                            anomaly_type="suspicious_content",
                            severity=0.7,
                            evidence=f"Contains '{pattern}'",
                        )
                    )
                    suspicious.append(memory.memory_id)
                    break

            # 2. Check source integrity
            if memory.source == "inferred" and memory.confidence < 0.5:
                anomalies.append(
                    MemoryAnomaly(
                        memory_id=memory.memory_id,
                        anomaly_type="low_confidence_inference",
                        severity=0.5,
                        evidence=f"Confidence: {memory.confidence:.0%}",
                    )
                )

            # 3. Check for unverified critical memories
            if memory.memory_id not in self.verified_memories and any(
                p in content_lower for p in ["always", "never", "must", "required"]
            ):
                anomalies.append(
                    MemoryAnomaly(
                        memory_id=memory.memory_id,
                        anomaly_type="unverified_directive",
                        severity=0.6,
                        evidence="Contains directive language",
                    )
                )
                suspicious.append(memory.memory_id)

            # 4. Check hash integrity
            expected_hash = hashlib.sha256(memory.content.encode()).hexdigest()[:16]
            if memory.hash_signature and memory.hash_signature != expected_hash:
                anomalies.append(
                    MemoryAnomaly(
                        memory_id=memory.memory_id,
                        anomaly_type="hash_mismatch",
                        severity=0.9,
                        evidence="Memory content was modified",
                    )
                )
                suspicious.append(memory.memory_id)

        # Calculate risk
        risk_score = sum(a.severity for a in anomalies) / max(len(memories), 1)

        injection_detected = len(suspicious) > 0

        recommendations = []
        if injection_detected:
            recommendations.append("Review and verify suspicious memories")
            recommendations.append("Enable memory source verification")
            recommendations.append("Consider purging unverified memories")

        return SyntheticMemoryResult(
            injection_detected=injection_detected,
            anomalies=anomalies,
            suspicious_memories=list(set(suspicious)),
            risk_score=min(risk_score, 1.0),
            recommendations=recommendations,
        )

    def purge_suspicious(self, memory_ids: List[str]):
        """Remove suspicious memories"""
        for mid in memory_ids:
            if mid in self.memory_registry:
                del self.memory_registry[mid]

    def get_statistics(self) -> Dict[str, Any]:
        return {
            "registered_memories": len(self.memory_registry),
            "verified_memories": len(self.verified_memories),
            "suspicious_patterns": len(self.SUSPICIOUS_PATTERNS),
        }


def create_engine(
    config: Optional[Dict[str, Any]] = None,
) -> SyntheticMemoryInjectionDetector:
    return SyntheticMemoryInjectionDetector(config)
