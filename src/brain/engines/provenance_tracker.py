"""
Provenance Chain Tracker Engine - Multi-Hop Attack Defense

Tracks origin and propagation of data through agent chains:
- DAG-based provenance storage
- Origin verification
- Hop counting and depth limits
- Taint propagation tracking
- Audit trail generation

Addresses: OWASP ASI-06 (Indirect Prompt Injection)
Research: multi_hop_defense_deep_dive.md
Invention: Provenance Chain Tracker (#41)
"""

import hashlib
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict

from base_engine import Severity, Action  # Base classes

logger = logging.getLogger("ProvenanceTracker")


# ============================================================================
# Data Classes
# ============================================================================


class TrustLevel(Enum):
    """Trust levels for data origins."""

    UNTRUSTED = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    VERIFIED = 4


class TaintType(Enum):
    """Types of data taint."""

    NONE = "none"
    USER_INPUT = "user_input"
    EXTERNAL_API = "external_api"
    FILE_CONTENT = "file_content"
    WEB_CONTENT = "web_content"
    AGENT_OUTPUT = "agent_output"


@dataclass
class ProvenanceNode:
    """Node in the provenance DAG."""

    node_id: str
    content_hash: str
    source_type: TaintType
    trust_level: TrustLevel
    timestamp: float
    agent_id: Optional[str] = None
    parent_ids: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)

    def compute_hash(self, content: str) -> str:
        """Compute content hash."""
        return hashlib.sha256(content.encode()).hexdigest()[:16]


@dataclass
class ProvenanceResult:
    """Result from provenance analysis."""

    is_safe: bool
    risk_score: float
    hop_count: int
    min_trust: TrustLevel
    taint_chain: List[TaintType] = field(default_factory=list)
    violations: List[str] = field(default_factory=list)
    audit_trail: List[str] = field(default_factory=list)
    latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "is_safe": self.is_safe,
            "risk_score": self.risk_score,
            "hop_count": self.hop_count,
            "min_trust": self.min_trust.name,
            "taint_chain": [t.value for t in self.taint_chain],
            "violations": self.violations,
            "latency_ms": self.latency_ms,
        }


# ============================================================================
# Provenance DAG
# ============================================================================


class ProvenanceDAG:
    """
    Directed Acyclic Graph for provenance tracking.

    Stores complete lineage of data through agent chains.
    """

    def __init__(self):
        self._nodes: Dict[str, ProvenanceNode] = {}
        self._children: Dict[str, Set[str]] = defaultdict(set)

    def add_node(self, node: ProvenanceNode) -> None:
        """Add node to DAG."""
        self._nodes[node.node_id] = node
        for parent_id in node.parent_ids:
            self._children[parent_id].add(node.node_id)

    def get_node(self, node_id: str) -> Optional[ProvenanceNode]:
        """Get node by ID."""
        return self._nodes.get(node_id)

    def get_ancestors(self, node_id: str) -> List[ProvenanceNode]:
        """Get all ancestors of a node (BFS)."""
        ancestors = []
        visited = set()
        queue = [node_id]

        while queue:
            current_id = queue.pop(0)
            node = self._nodes.get(current_id)

            if not node or current_id in visited:
                continue

            visited.add(current_id)
            if current_id != node_id:
                ancestors.append(node)

            queue.extend(node.parent_ids)

        return ancestors

    def get_hop_count(self, node_id: str) -> int:
        """Count hops from origin to node."""
        node = self._nodes.get(node_id)
        if not node or not node.parent_ids:
            return 0

        max_parent_hops = 0
        for parent_id in node.parent_ids:
            parent_hops = self.get_hop_count(parent_id)
            max_parent_hops = max(max_parent_hops, parent_hops)

        return max_parent_hops + 1

    def get_taint_chain(self, node_id: str) -> List[TaintType]:
        """Get chain of taint types from origin."""
        ancestors = self.get_ancestors(node_id)
        node = self._nodes.get(node_id)

        chain = [a.source_type for a in reversed(ancestors)]
        if node:
            chain.append(node.source_type)

        return chain


# ============================================================================
# Origin Verifier
# ============================================================================


class OriginVerifier:
    """
    Verifies origin trustworthiness.

    Assigns trust levels based on source characteristics.
    """

    def __init__(self):
        self._trusted_domains: Set[str] = set()
        self._trusted_agents: Set[str] = set()
        self._blocked_sources: Set[str] = set()

    def add_trusted_domain(self, domain: str) -> None:
        """Add trusted domain."""
        self._trusted_domains.add(domain.lower())

    def add_trusted_agent(self, agent_id: str) -> None:
        """Add trusted agent."""
        self._trusted_agents.add(agent_id)

    def block_source(self, source: str) -> None:
        """Block a source."""
        self._blocked_sources.add(source.lower())

    def verify(
        self,
        source_type: TaintType,
        source_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> Tuple[TrustLevel, str]:
        """
        Verify source and assign trust level.

        Returns:
            (trust_level, reason)
        """
        # Check blocked sources
        if source_id and source_id.lower() in self._blocked_sources:
            return TrustLevel.UNTRUSTED, f"Blocked source: {source_id}"

        # Trust based on source type
        if source_type == TaintType.USER_INPUT:
            return TrustLevel.LOW, "User input - untrusted by default"

        if source_type == TaintType.WEB_CONTENT:
            domain = metadata.get("domain", "") if metadata else ""
            if domain.lower() in self._trusted_domains:
                return TrustLevel.MEDIUM, f"Trusted domain: {domain}"
            return TrustLevel.LOW, "Web content - verify manually"

        if source_type == TaintType.EXTERNAL_API:
            return TrustLevel.MEDIUM, "External API"

        if source_type == TaintType.AGENT_OUTPUT:
            if source_id in self._trusted_agents:
                return TrustLevel.HIGH, f"Trusted agent: {source_id}"
            return TrustLevel.MEDIUM, "Agent output"

        if source_type == TaintType.FILE_CONTENT:
            return TrustLevel.MEDIUM, "File content"

        return TrustLevel.VERIFIED, "Known safe source"


# ============================================================================
# Taint Propagator
# ============================================================================


class TaintPropagator:
    """
    Tracks taint propagation through transformations.

    Determines how taint spreads when data is combined.
    """

    def propagate(
        self, parent_taints: List[TaintType], parent_trusts: List[TrustLevel]
    ) -> Tuple[TaintType, TrustLevel]:
        """
        Compute resulting taint from combining sources.

        Returns:
            (combined_taint, min_trust)
        """
        if not parent_taints:
            return TaintType.NONE, TrustLevel.VERIFIED

        # Min trust propagates (weakest link)
        min_trust = min(parent_trusts, key=lambda t: t.value)

        # Most dangerous taint propagates
        taint_priority = [
            TaintType.WEB_CONTENT,
            TaintType.USER_INPUT,
            TaintType.EXTERNAL_API,
            TaintType.FILE_CONTENT,
            TaintType.AGENT_OUTPUT,
            TaintType.NONE,
        ]

        for taint in taint_priority:
            if taint in parent_taints:
                return taint, min_trust

        return TaintType.NONE, min_trust


# ============================================================================
# Main Engine: Provenance Chain Tracker
# ============================================================================


class ProvenanceChainTracker:
    """
    Provenance Chain Tracker - Multi-Hop Attack Defense

    Comprehensive tracking of data lineage:
    - DAG-based provenance
    - Origin verification
    - Taint propagation
    - Hop counting
    - Audit trails

    Invention #41 from research.
    Addresses OWASP ASI-06.
    """

    def __init__(
        self,
        max_hops: int = 5,
        min_trust_required: TrustLevel = TrustLevel.LOW,
    ):
        self.dag = ProvenanceDAG()
        self.verifier = OriginVerifier()
        self.propagator = TaintPropagator()

        self.max_hops = max_hops
        self.min_trust = min_trust_required

        self._node_counter = 0

        logger.info("ProvenanceChainTracker initialized")

    def _generate_id(self) -> str:
        """Generate unique node ID."""
        self._node_counter += 1
        return f"prov_{self._node_counter}_{int(time.time()*1000)}"

    def track(
        self,
        content: str,
        source_type: TaintType,
        source_id: Optional[str] = None,
        parent_ids: Optional[List[str]] = None,
        agent_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> Tuple[str, ProvenanceResult]:
        """
        Track new data in provenance chain.

        Args:
            content: Data content
            source_type: Type of source
            source_id: Identifier for source
            parent_ids: IDs of parent nodes
            agent_id: Processing agent ID
            metadata: Additional metadata

        Returns:
            (node_id, ProvenanceResult)
        """
        start = time.time()

        violations = []

        # 1. Verify origin
        trust, trust_reason = self.verifier.verify(
            source_type, source_id, metadata)

        # 2. Handle parent chain
        parent_ids = parent_ids or []
        hop_count = 0
        taint_chain = []
        min_trust = trust

        if parent_ids:
            # Get parent info
            parent_taints = []
            parent_trusts = []

            for pid in parent_ids:
                parent = self.dag.get_node(pid)
                if parent:
                    parent_taints.append(parent.source_type)
                    parent_trusts.append(parent.trust_level)
                    hop_count = max(hop_count, self.dag.get_hop_count(pid) + 1)

            # Propagate taint
            if parent_taints:
                _, propagated_trust = self.propagator.propagate(
                    parent_taints, parent_trusts
                )
                min_trust = min(
                    min_trust,
                    propagated_trust,
                    key=lambda t: t.value)

            # Get taint chain
            if parent_ids:
                taint_chain = self.dag.get_taint_chain(parent_ids[0])

        taint_chain.append(source_type)

        # 3. Check hop limit
        if hop_count > self.max_hops:
            violations.append(
                f"Hop count {hop_count} exceeds max {self.max_hops}")

        # 4. Check trust level
        if min_trust.value < self.min_trust.value:
            violations.append(
                f"Trust {min_trust.name} < required {self.min_trust.name}"
            )

        # 5. Create node
        node_id = self._generate_id()
        node = ProvenanceNode(
            node_id=node_id,
            content_hash=hashlib.sha256(content.encode()).hexdigest()[:16],
            source_type=source_type,
            trust_level=min_trust,
            timestamp=time.time(),
            agent_id=agent_id,
            parent_ids=parent_ids,
            metadata=metadata or {},
        )
        self.dag.add_node(node)

        # 6. Build audit trail
        audit = [
            f"Node {node_id}: {source_type.value} (trust={min_trust.name})"]
        for pid in parent_ids:
            parent = self.dag.get_node(pid)
            if parent:
                audit.append(f"  <- {pid}: {parent.source_type.value}")

        # Calculate risk
        risk = 0.0
        if violations:
            risk = 0.7 + len(violations) * 0.1
        elif min_trust.value <= TrustLevel.LOW.value:
            risk = 0.4

        result = ProvenanceResult(
            is_safe=len(violations) == 0,
            risk_score=min(1.0, risk),
            hop_count=hop_count,
            min_trust=min_trust,
            taint_chain=taint_chain,
            violations=violations,
            audit_trail=audit,
            latency_ms=(time.time() - start) * 1000,
        )

        if violations:
            logger.warning(f"Provenance violations: {violations}")

        return node_id, result

    def verify_chain(self, node_id: str) -> ProvenanceResult:
        """Verify entire provenance chain for a node."""
        start = time.time()

        node = self.dag.get_node(node_id)
        if not node:
            return ProvenanceResult(
                is_safe=False,
                risk_score=1.0,
                hop_count=0,
                min_trust=TrustLevel.UNTRUSTED,
                violations=["Node not found"],
                latency_ms=(time.time() - start) * 1000,
            )

        hop_count = self.dag.get_hop_count(node_id)
        taint_chain = self.dag.get_taint_chain(node_id)
        ancestors = self.dag.get_ancestors(node_id)

        # Find minimum trust in chain
        trusts = [node.trust_level] + [a.trust_level for a in ancestors]
        min_trust = min(trusts, key=lambda t: t.value)

        violations = []
        if hop_count > self.max_hops:
            violations.append(f"Hop count exceeds limit")
        if min_trust.value < self.min_trust.value:
            violations.append(f"Trust below threshold")

        return ProvenanceResult(
            is_safe=len(violations) == 0,
            risk_score=0.0 if not violations else 0.7,
            hop_count=hop_count,
            min_trust=min_trust,
            taint_chain=taint_chain,
            violations=violations,
            latency_ms=(time.time() - start) * 1000,
        )


# ============================================================================
# Convenience Functions
# ============================================================================

_default_tracker: Optional[ProvenanceChainTracker] = None


def get_tracker() -> ProvenanceChainTracker:
    """Get default tracker."""
    global _default_tracker
    if _default_tracker is None:
        _default_tracker = ProvenanceChainTracker()
    return _default_tracker
