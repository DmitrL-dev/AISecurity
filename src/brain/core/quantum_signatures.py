"""
Quantum Entanglement Signatures — Linked Threat Detection

Links threat signatures using quantum-inspired entanglement:
when one signature is triggered, related signatures are
instantly activated for cascading defense.

Key Features:
- Entanglement pairs/clusters of related threats
- Instant propagation of threat detection
- Correlated response across attack vectors
- QRNG-based unpredictable linking

Usage:
    qes = QuantumEntanglement()
    qes.entangle("sig_a", "sig_b")  # Link signatures
    triggered = qes.trigger("sig_a")  # Returns all entangled
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Set, Optional, Tuple
from collections import defaultdict
import hashlib
import random


@dataclass
class EntanglementCluster:
    """Cluster of entangled threat signatures."""
    cluster_id: str
    signatures: Set[str] = field(default_factory=set)
    strength: float = 1.0  # 0-1, decay over time
    created_at: datetime = field(default_factory=datetime.now)
    trigger_count: int = 0
    last_trigger: Optional[datetime] = None

    def add(self, sig: str):
        self.signatures.add(sig)

    def remove(self, sig: str):
        self.signatures.discard(sig)


@dataclass
class TriggerEvent:
    """Record of a triggered entanglement."""
    source_signature: str
    propagated_to: List[str]
    timestamp: datetime = field(default_factory=datetime.now)
    strength: float = 1.0


class QuantumEntanglement:
    """
    Quantum-inspired entanglement of threat signatures.

    When one threat is detected, all entangled threats are
    instantly "activated" - meaning their detection thresholds
    are lowered and monitoring is increased.
    """

    # Default entanglement relationships (attack families)
    DEFAULT_ENTANGLEMENTS = [
        # Jailbreak family
        {"jailbreak", "dan_attack", "role_play", "mode_switch"},
        # Injection family
        {"injection", "prompt_injection", "indirect_injection", "context_poisoning"},
        # Data theft family
        {"pii_extraction", "data_theft", "exfiltration", "prompt_leak"},
        # Evasion family
        {"encoding", "unicode", "base64", "homoglyph", "obfuscation"},
        # Reconnaissance family
        {"probing", "capability_scan", "version_discovery", "fingerprinting"},
    ]

    def __init__(self, use_qrng: bool = False):
        """
        Initialize Quantum Entanglement system.

        Args:
            use_qrng: Use quantum RNG for entanglement (if available)
        """
        self.use_qrng = use_qrng
        self._clusters: Dict[str, EntanglementCluster] = {}
        self._sig_to_cluster: Dict[str, str] = {}  # signature -> cluster_id
        self._trigger_history: List[TriggerEvent] = []

        # Initialize default entanglements
        for sigs in self.DEFAULT_ENTANGLEMENTS:
            self.create_cluster(sigs)

    def _generate_cluster_id(self) -> str:
        """Generate unique cluster ID."""
        seed = datetime.now().isoformat() + str(random.random())
        return hashlib.sha256(seed.encode()).hexdigest()[:12]

    def create_cluster(self, signatures: Set[str], strength: float = 1.0) -> str:
        """
        Create a new entanglement cluster.

        Args:
            signatures: Set of signature names to entangle
            strength: Initial entanglement strength (0-1)

        Returns:
            Cluster ID
        """
        cluster_id = self._generate_cluster_id()
        cluster = EntanglementCluster(
            cluster_id=cluster_id,
            signatures=signatures,
            strength=strength,
        )
        self._clusters[cluster_id] = cluster

        # Map signatures to cluster
        for sig in signatures:
            self._sig_to_cluster[sig] = cluster_id

        return cluster_id

    def entangle(self, sig_a: str, sig_b: str) -> str:
        """
        Entangle two signatures (create or merge clusters).

        Args:
            sig_a: First signature
            sig_b: Second signature

        Returns:
            Cluster ID containing both
        """
        cluster_a = self._sig_to_cluster.get(sig_a)
        cluster_b = self._sig_to_cluster.get(sig_b)

        if cluster_a and cluster_b:
            if cluster_a == cluster_b:
                return cluster_a  # Already entangled
            # Merge clusters
            return self._merge_clusters(cluster_a, cluster_b)
        elif cluster_a:
            self._clusters[cluster_a].add(sig_b)
            self._sig_to_cluster[sig_b] = cluster_a
            return cluster_a
        elif cluster_b:
            self._clusters[cluster_b].add(sig_a)
            self._sig_to_cluster[sig_a] = cluster_b
            return cluster_b
        else:
            # Create new cluster
            return self.create_cluster({sig_a, sig_b})

    def _merge_clusters(self, id_a: str, id_b: str) -> str:
        """Merge two clusters into one."""
        cluster_a = self._clusters[id_a]
        cluster_b = self._clusters[id_b]

        # Merge into A
        for sig in cluster_b.signatures:
            cluster_a.add(sig)
            self._sig_to_cluster[sig] = id_a

        # Average strength
        cluster_a.strength = (cluster_a.strength + cluster_b.strength) / 2

        # Remove B
        del self._clusters[id_b]

        return id_a

    def trigger(self, signature: str) -> List[str]:
        """
        Trigger a signature and propagate to entangled signatures.

        Args:
            signature: The triggered signature

        Returns:
            List of all signatures that should be activated
        """
        cluster_id = self._sig_to_cluster.get(signature)

        if not cluster_id:
            return [signature]  # Not entangled

        cluster = self._clusters[cluster_id]
        cluster.trigger_count += 1
        cluster.last_trigger = datetime.now()

        # Get all entangled signatures
        propagated = list(cluster.signatures)

        # Record event
        self._trigger_history.append(TriggerEvent(
            source_signature=signature,
            propagated_to=propagated,
            strength=cluster.strength,
        ))

        return propagated

    def get_entangled(self, signature: str) -> Set[str]:
        """Get all signatures entangled with given signature."""
        cluster_id = self._sig_to_cluster.get(signature)
        if not cluster_id:
            return {signature}
        return self._clusters[cluster_id].signatures.copy()

    def get_activation_multiplier(self, signature: str) -> float:
        """
        Get threshold multiplier based on entanglement state.

        If entangled signatures were recently triggered,
        return a lower multiplier (more sensitive).
        """
        cluster_id = self._sig_to_cluster.get(signature)
        if not cluster_id:
            return 1.0

        cluster = self._clusters[cluster_id]

        # If recently triggered, increase sensitivity
        if cluster.last_trigger:
            age = (datetime.now() - cluster.last_trigger).total_seconds()
            if age < 60:  # Within 1 minute
                # Reduce threshold (more sensitive) based on recency
                return 0.7 + (0.3 * (age / 60))  # 0.7 → 1.0 over 60 seconds

        return 1.0

    def decay_strength(self, hours: float = 24):
        """
        Decay entanglement strength over time.
        Call periodically to simulate decoherence.
        """
        decay_rate = 0.95  # 5% decay per call

        for cluster in self._clusters.values():
            if cluster.last_trigger:
                age_hours = (datetime.now() -
                             cluster.last_trigger).total_seconds() / 3600
                if age_hours > hours:
                    cluster.strength *= decay_rate

    def get_stats(self) -> Dict:
        """Get entanglement system statistics."""
        return {
            "clusters": len(self._clusters),
            "total_signatures": len(self._sig_to_cluster),
            "total_triggers": len(self._trigger_history),
            "recent_triggers": sum(
                1 for t in self._trigger_history
                if (datetime.now() - t.timestamp).total_seconds() < 3600
            ),
        }


# Singleton instance
_qes: Optional[QuantumEntanglement] = None


def get_quantum_entanglement() -> QuantumEntanglement:
    """Get or create singleton QuantumEntanglement instance."""
    global _qes
    if _qes is None:
        _qes = QuantumEntanglement()
    return _qes


# Convenience functions
def trigger_signature(sig: str) -> List[str]:
    """Trigger a signature and get all entangled signatures."""
    return get_quantum_entanglement().trigger(sig)


def get_threshold_multiplier(sig: str) -> float:
    """Get threshold multiplier based on entanglement state."""
    return get_quantum_entanglement().get_activation_multiplier(sig)
