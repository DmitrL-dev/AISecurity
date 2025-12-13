"""
Enhanced TDA Module - Advanced Topological Data Analysis for LLM Security

Based on 2025 research:
  - ICML 2025: Zigzag Persistence for layer-by-layer LLM analysis
  - Medium Feb 2025: TDA for attention maps vulnerability detection
  - NeurIPS 2025 Workshop: Mathematical foundations of LLM security

Capabilities:
  - Persistence Diagrams with visualization data
  - Bottleneck and Wasserstein distances
  - Zigzag Persistence for hidden state evolution
  - Attention Pattern Topology analysis
  - Topological fingerprinting of prompts

Author: SENTINEL Team
Date: 2025-12-09
"""

import logging
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Tuple, Any
import hashlib

# GUDHI for precise TDA (optional, falls back to approximation)
try:
    import gudhi
    GUDHI_AVAILABLE = True
except ImportError:
    GUDHI_AVAILABLE = False

logger = logging.getLogger("TDAEnhanced")
if GUDHI_AVAILABLE:
    logger.info("GUDHI available - using precise TDA computations")


# ============================================================================
# Enums and Data Classes
# ============================================================================

class TopologicalFeatureType(str, Enum):
    """Types of topological features detected."""
    CONNECTED_COMPONENT = "H0"  # β₀
    LOOP = "H1"                  # β₁
    VOID = "H2"                  # β₂
    HIGHER = "Hn"               # Higher homology


@dataclass
class PersistencePair:
    """A single persistence pair (birth, death)."""
    birth: float
    death: float
    dimension: int

    @property
    def lifetime(self) -> float:
        """Persistence lifetime."""
        return self.death - self.birth if self.death < np.inf else np.inf

    @property
    def midpoint(self) -> float:
        """Midpoint on the persistence bar."""
        if self.death < np.inf:
            return (self.birth + self.death) / 2
        return self.birth


@dataclass
class PersistenceDiagram:
    """Full persistence diagram with pairs per dimension."""
    pairs: List[PersistencePair] = field(default_factory=list)
    max_dimension: int = 2

    def get_pairs(self, dimension: int) -> List[PersistencePair]:
        """Get pairs for specific dimension."""
        return [p for p in self.pairs if p.dimension == dimension]

    def betti_number(self, dimension: int, threshold: float = 0.0) -> int:
        """Count features with lifetime > threshold."""
        return sum(1 for p in self.get_pairs(dimension)
                   if p.lifetime > threshold and p.lifetime < np.inf)

    def total_persistence(self, dimension: int) -> float:
        """Sum of all lifetimes in dimension."""
        return sum(p.lifetime for p in self.get_pairs(dimension)
                   if p.lifetime < np.inf)

    def entropy(self, dimension: int) -> float:
        """Persistence entropy for dimension."""
        lifetimes = [p.lifetime for p in self.get_pairs(dimension)
                     if p.lifetime < np.inf and p.lifetime > 0]
        if not lifetimes:
            return 0.0
        total = sum(lifetimes)
        probs = [l / total for l in lifetimes]
        return -sum(p * np.log(p + 1e-10) for p in probs)

    def to_array(self, dimension: int) -> np.ndarray:
        """Convert to numpy array for distance computations."""
        pairs = self.get_pairs(dimension)
        if not pairs:
            return np.array([]).reshape(0, 2)
        return np.array([[p.birth, p.death] for p in pairs
                         if p.death < np.inf])


@dataclass
class ZigzagPersistence:
    """
    Zigzag persistence for tracking features through layers.

    Based on ICML 2025 research on tracking information
    evolution through LLM layers.
    """
    layer_diagrams: List[PersistenceDiagram] = field(default_factory=list)
    transitions: List[Dict[str, int]] = field(default_factory=list)

    def add_layer(self, diagram: PersistenceDiagram, transition: Dict[str, int]):
        """Add a layer's topology and transition info."""
        self.layer_diagrams.append(diagram)
        if transition:
            self.transitions.append(transition)

    def feature_flow(self, dimension: int) -> List[int]:
        """Track how many features exist at each layer."""
        return [d.betti_number(dimension) for d in self.layer_diagrams]

    def stability_score(self) -> float:
        """Measure how stable features are across layers."""
        if len(self.layer_diagrams) < 2:
            return 1.0

        h1_flow = self.feature_flow(1)
        if max(h1_flow) == 0:
            return 1.0

        variance = np.var(h1_flow)
        mean = np.mean(h1_flow) + 1e-10
        cv = np.sqrt(variance) / mean  # Coefficient of variation

        return max(0.0, 1.0 - cv)


@dataclass
class AttentionTopology:
    """Topological analysis of attention patterns."""
    graph_betti: Dict[str, int] = field(default_factory=dict)  # β₀, β₁
    attention_entropy: float = 0.0
    sparsity: float = 0.0
    clustering_coefficient: float = 0.0
    is_anomalous: bool = False
    anomaly_reason: str = ""


@dataclass
class TopologicalFingerprint:
    """
    Unique topological signature of a prompt or response.

    Can be used for:
    - Attack pattern recognition
    - Model fingerprinting
    - Anomaly detection
    """
    fingerprint_id: str
    betti_signature: Tuple[int, int, int]  # (β₀, β₁, β₂)
    # Total persistence per dim
    persistence_signature: Tuple[float, float, float]
    entropy_signature: Tuple[float, float, float]
    landscape_hash: str

    def similarity(self, other: 'TopologicalFingerprint') -> float:
        """Compute similarity to another fingerprint."""
        # Betti similarity
        betti_dist = np.sqrt(sum((a - b) ** 2
                                 for a, b in zip(self.betti_signature,
                                                 other.betti_signature)))
        betti_sim = 1.0 / (1.0 + betti_dist)

        # Persistence similarity
        pers_dist = np.sqrt(sum((a - b) ** 2
                                for a, b in zip(self.persistence_signature,
                                                other.persistence_signature)))
        pers_sim = 1.0 / (1.0 + pers_dist)

        # Hash similarity (exact or not)
        hash_sim = 1.0 if self.landscape_hash == other.landscape_hash else 0.0

        return 0.4 * betti_sim + 0.4 * pers_sim + 0.2 * hash_sim


# ============================================================================
# Distance Metrics
# ============================================================================

class PersistenceDistance:
    """
    Distance metrics between persistence diagrams.
    """

    @staticmethod
    def bottleneck_distance(dgm1: np.ndarray, dgm2: np.ndarray) -> float:
        """
        Bottleneck distance between two persistence diagrams.

        This is the ∞-Wasserstein distance - the maximum matching cost.
        """
        if len(dgm1) == 0 and len(dgm2) == 0:
            return 0.0
        if len(dgm1) == 0:
            return max((d - b) / 2 for b, d in dgm2)
        if len(dgm2) == 0:
            return max((d - b) / 2 for b, d in dgm1)

        # Simplified bottleneck: use greedy matching
        # Full implementation would use Hungarian algorithm
        costs = []

        for b1, d1 in dgm1:
            min_cost = (d1 - b1) / 2  # Cost to match to diagonal
            for b2, d2 in dgm2:
                cost = max(abs(b1 - b2), abs(d1 - d2))
                min_cost = min(min_cost, cost)
            costs.append(min_cost)

        for b2, d2 in dgm2:
            min_cost = (d2 - b2) / 2
            for b1, d1 in dgm1:
                cost = max(abs(b1 - b2), abs(d1 - d2))
                min_cost = min(min_cost, cost)
            costs.append(min_cost)

        return max(costs) if costs else 0.0

    @staticmethod
    def wasserstein_distance(dgm1: np.ndarray, dgm2: np.ndarray,
                             p: int = 2) -> float:
        """
        p-Wasserstein distance between persistence diagrams.

        For p=2, this is the standard "earth mover's distance" variant.
        """
        if len(dgm1) == 0 and len(dgm2) == 0:
            return 0.0
        if len(dgm1) == 0:
            return sum(((d - b) / 2) ** p for b, d in dgm2) ** (1/p)
        if len(dgm2) == 0:
            return sum(((d - b) / 2) ** p for b, d in dgm1) ** (1/p)

        # Simplified: include diagonal projections
        total = 0.0

        # Match each point to closest in other diagram or diagonal
        for b1, d1 in dgm1:
            diag_cost = ((d1 - b1) / 2) ** p
            min_cost = diag_cost
            for b2, d2 in dgm2:
                cost = (abs(b1 - b2) ** p + abs(d1 - d2) ** p)
                min_cost = min(min_cost, cost)
            total += min_cost

        return total ** (1/p)

    @staticmethod
    def landscape_distance(landscape1: np.ndarray,
                           landscape2: np.ndarray) -> float:
        """L2 distance between persistence landscapes."""
        if landscape1.shape != landscape2.shape:
            # Pad smaller to match
            max_shape = (max(landscape1.shape[0], landscape2.shape[0]),
                         max(landscape1.shape[1], landscape2.shape[1]))

            l1_padded = np.zeros(max_shape)
            l2_padded = np.zeros(max_shape)

            l1_padded[:landscape1.shape[0], :landscape1.shape[1]] = landscape1
            l2_padded[:landscape2.shape[0], :landscape2.shape[1]] = landscape2

            return float(np.linalg.norm(l1_padded - l2_padded))

        return float(np.linalg.norm(landscape1 - landscape2))


# ============================================================================
# GUDHI Backend (Precise TDA)
# ============================================================================

class GUDHIBackend:
    """
    GUDHI-powered precise TDA computations.

    Provides:
    - Rips complex for point clouds
    - Alpha complex for low-dimensional data
    - Exact Betti numbers and persistence diagrams

    Falls back to approximation if GUDHI unavailable.
    """

    def __init__(self, max_dimension: int = 2, max_edge_length: float = float('inf')):
        self.max_dimension = max_dimension
        self.max_edge_length = max_edge_length
        self.gudhi_available = GUDHI_AVAILABLE

    def compute_persistence_rips(
        self,
        points: np.ndarray
    ) -> PersistenceDiagram:
        """
        Compute persistence using Rips complex.

        Args:
            points: (n_points, n_dimensions) point cloud

        Returns:
            PersistenceDiagram with exact persistence pairs
        """
        diagram = PersistenceDiagram(max_dimension=self.max_dimension)

        if len(points) < 2:
            return diagram

        if self.gudhi_available:
            try:
                # Build Rips complex
                rips = gudhi.RipsComplex(
                    points=points, max_edge_length=self.max_edge_length)
                simplex_tree = rips.create_simplex_tree(
                    max_dimension=self.max_dimension + 1)

                # Compute persistence
                simplex_tree.compute_persistence()
                pairs = simplex_tree.persistence()

                for dim, (birth, death) in pairs:
                    if dim <= self.max_dimension:
                        diagram.pairs.append(PersistencePair(
                            birth=birth,
                            death=death if death != float('inf') else np.inf,
                            dimension=dim
                        ))

                logger.debug(
                    f"GUDHI Rips: {len(diagram.pairs)} pairs computed")

            except Exception as e:
                logger.warning(f"GUDHI Rips failed, using approximation: {e}")
                return self._approximate_persistence(points)
        else:
            return self._approximate_persistence(points)

        return diagram

    def compute_persistence_alpha(
        self,
        points: np.ndarray
    ) -> PersistenceDiagram:
        """
        Compute persistence using Alpha complex (faster for low-dim data).

        Best for 2D/3D point clouds.
        """
        diagram = PersistenceDiagram(max_dimension=self.max_dimension)

        if len(points) < 2:
            return diagram

        if self.gudhi_available and points.shape[1] <= 3:
            try:
                alpha = gudhi.AlphaComplex(points=points)
                simplex_tree = alpha.create_simplex_tree()

                simplex_tree.compute_persistence()
                pairs = simplex_tree.persistence()

                for dim, (birth, death) in pairs:
                    if dim <= self.max_dimension:
                        diagram.pairs.append(PersistencePair(
                            # Alpha uses squared distances
                            birth=np.sqrt(birth),
                            death=np.sqrt(death) if death != float(
                                'inf') else np.inf,
                            dimension=dim
                        ))

                logger.debug(
                    f"GUDHI Alpha: {len(diagram.pairs)} pairs computed")

            except Exception as e:
                logger.warning(f"GUDHI Alpha failed: {e}")
                return self.compute_persistence_rips(points)
        else:
            return self.compute_persistence_rips(points)

        return diagram

    def betti_numbers(self, points: np.ndarray, threshold: float = 0.0) -> Tuple[int, int, int]:
        """
        Compute Betti numbers β₀, β₁, β₂ for point cloud.
        """
        diagram = self.compute_persistence_rips(points)
        return (
            diagram.betti_number(0, threshold),
            diagram.betti_number(1, threshold),
            diagram.betti_number(2, threshold)
        )

    def bottleneck_distance_gudhi(
        self,
        dgm1: PersistenceDiagram,
        dgm2: PersistenceDiagram,
        dimension: int = 1
    ) -> float:
        """
        Exact bottleneck distance using GUDHI.
        """
        if self.gudhi_available:
            try:
                arr1 = dgm1.to_array(dimension)
                arr2 = dgm2.to_array(dimension)

                if len(arr1) == 0 or len(arr2) == 0:
                    return 0.0

                return gudhi.bottleneck_distance(arr1, arr2)
            except Exception as e:
                logger.warning(f"GUDHI bottleneck failed: {e}")

        # Fallback to approximation
        return PersistenceDistance.bottleneck_distance(
            dgm1.to_array(dimension),
            dgm2.to_array(dimension)
        )

    def _approximate_persistence(self, points: np.ndarray) -> PersistenceDiagram:
        """Fallback approximation when GUDHI unavailable."""
        diagram = PersistenceDiagram(max_dimension=self.max_dimension)

        n = len(points)
        if n < 2:
            return diagram

        # Compute pairwise distances
        dists = []
        for i in range(min(n, 100)):
            for j in range(i + 1, min(n, 100)):
                dists.append(np.linalg.norm(points[i] - points[j]))

        if not dists:
            return diagram

        dists = sorted(dists)

        # H0: Components merge
        for i, d in enumerate(dists[:min(n-1, 20)]):
            diagram.pairs.append(PersistencePair(0.0, d, 0))

        # H1: Approximate loops
        for i, d in enumerate(dists[n:n+10] if len(dists) > n else []):
            diagram.pairs.append(PersistencePair(d * 0.5, d, 1))

        return diagram


# ============================================================================
# Zigzag Persistence Engine
# ============================================================================

class ZigzagEngine:
    """
    Computes zigzag persistence for layer-by-layer analysis.

    Based on ICML 2025: Tracking information evolution through LLM layers.
    """

    def __init__(self, max_dim: int = 1):
        self.max_dim = max_dim

    def analyze_layer_sequence(
        self,
        layer_activations: List[np.ndarray]
    ) -> ZigzagPersistence:
        """
        Analyze how topology evolves through layers.

        Args:
            layer_activations: List of activation matrices per layer

        Returns:
            ZigzagPersistence with full analysis
        """
        result = ZigzagPersistence()

        prev_diagram = None

        for i, activations in enumerate(layer_activations):
            # Compute persistence for this layer
            diagram = self._compute_layer_persistence(activations)

            # Compute transition from previous layer
            transition = {}
            if prev_diagram is not None:
                transition = self._compute_transition(prev_diagram, diagram)

            result.add_layer(diagram, transition)
            prev_diagram = diagram

        return result

    def _compute_layer_persistence(
        self,
        activations: np.ndarray
    ) -> PersistenceDiagram:
        """Compute persistence diagram for single layer."""
        diagram = PersistenceDiagram(max_dimension=self.max_dim)

        if len(activations) < 3:
            return diagram

        # Simplified: use distance matrix approach
        try:
            # Compute pairwise distances
            n = len(activations)
            dists = np.zeros((n, n))
            for i in range(n):
                for j in range(i + 1, n):
                    d = np.linalg.norm(activations[i] - activations[j])
                    dists[i, j] = dists[j, i] = d

            # Simulate Rips filtration
            max_dist = dists.max()

            # H0: Connected components (simplified)
            # All points eventually merge, creating n-1 death events
            for i in range(n - 1):
                death = dists.flat[np.argsort(dists.flat)[n + i]]
                diagram.pairs.append(PersistencePair(
                    birth=0.0, death=death, dimension=0
                ))

            # H1: Loops (simplified - detect cycles in distance graph)
            if self.max_dim >= 1:
                threshold = np.percentile(dists.flat, 50)
                # Count potential cycles
                adj = (dists < threshold) & (dists > 0)
                degrees = adj.sum(axis=1)

                # Excess edges indicate cycles
                num_edges = adj.sum() // 2
                num_cycles = max(0, num_edges - n + 1)

                for c in range(num_cycles):
                    birth = threshold * (0.5 + 0.1 * c)
                    death = max_dist * (0.8 + 0.05 * c)
                    diagram.pairs.append(PersistencePair(
                        birth=birth, death=death, dimension=1
                    ))

        except Exception as e:
            logger.warning(f"Zigzag computation failed: {e}")

        return diagram

    def _compute_transition(
        self,
        prev: PersistenceDiagram,
        curr: PersistenceDiagram
    ) -> Dict[str, int]:
        """Compute transition statistics between layers."""
        return {
            "h0_change": curr.betti_number(0) - prev.betti_number(0),
            "h1_change": curr.betti_number(1) - prev.betti_number(1),
            "persistence_change": int(curr.total_persistence(1) -
                                      prev.total_persistence(1))
        }


# ============================================================================
# Attention Topology Engine
# ============================================================================

class AttentionTopologyEngine:
    """
    Analyzes topological structure of attention patterns.

    Based on Feb 2025 research: TDA for attention map vulnerability detection.
    """

    def __init__(self, threshold: float = 0.1):
        self.threshold = threshold

    def analyze_attention(
        self,
        attention_matrix: np.ndarray
    ) -> AttentionTopology:
        """
        Analyze attention matrix as a weighted graph.

        Args:
            attention_matrix: (seq_len, seq_len) attention weights

        Returns:
            AttentionTopology with graph analysis
        """
        result = AttentionTopology()

        try:
            n = attention_matrix.shape[0]

            # 1. Compute graph properties
            # Threshold to create adjacency
            adj = attention_matrix > self.threshold

            # β₀: Connected components
            result.graph_betti["b0"] = self._count_components(adj)

            # β₁: Cycles (using Euler characteristic)
            num_edges = adj.sum() // 2
            num_vertices = n
            # χ = V - E + F, for planar: F = 1 + E - V (if connected)
            # β₁ ≈ E - V + components
            result.graph_betti["b1"] = max(0,
                                           num_edges - num_vertices + result.graph_betti["b0"])

            # 2. Attention entropy
            # Higher entropy = more uniform attention = potentially suspicious
            flat_attn = attention_matrix.flatten()
            flat_attn = flat_attn[flat_attn > 0]
            if len(flat_attn) > 0:
                probs = flat_attn / flat_attn.sum()
                result.attention_entropy = - \
                    np.sum(probs * np.log(probs + 1e-10))

            # 3. Sparsity
            result.sparsity = 1.0 - (adj.sum() / (n * n))

            # 4. Clustering coefficient
            result.clustering_coefficient = self._clustering_coefficient(adj)

            # 5. Anomaly detection
            result = self._detect_anomalies(result)

        except Exception as e:
            logger.warning(f"Attention topology failed: {e}")

        return result

    def _count_components(self, adj: np.ndarray) -> int:
        """Count connected components via BFS."""
        n = len(adj)
        visited = [False] * n
        components = 0

        for start in range(n):
            if visited[start]:
                continue

            # BFS
            queue = [start]
            visited[start] = True

            while queue:
                node = queue.pop(0)
                for neighbor in range(n):
                    if adj[node, neighbor] and not visited[neighbor]:
                        visited[neighbor] = True
                        queue.append(neighbor)

            components += 1

        return components

    def _clustering_coefficient(self, adj: np.ndarray) -> float:
        """Compute average clustering coefficient."""
        n = len(adj)
        coefficients = []

        for i in range(n):
            neighbors = np.where(adj[i])[0]
            k = len(neighbors)
            if k < 2:
                continue

            # Count edges between neighbors
            links = sum(1 for j in range(k) for l in range(j + 1, k)
                        if adj[neighbors[j], neighbors[l]])

            max_links = k * (k - 1) // 2
            coefficients.append(links / max_links if max_links > 0 else 0)

        return float(np.mean(coefficients)) if coefficients else 0.0

    def _detect_anomalies(
        self,
        topology: AttentionTopology
    ) -> AttentionTopology:
        """Detect topological anomalies in attention."""
        anomalies = []

        # Too many components = fragmented attention
        if topology.graph_betti.get("b0", 1) > 5:
            anomalies.append("fragmented_attention")

        # Too many cycles = unusual attention patterns
        if topology.graph_betti.get("b1", 0) > 10:
            anomalies.append("cyclic_attention")

        # Very high entropy = uniform (possibly adversarial)
        if topology.attention_entropy > 4.0:
            anomalies.append("entropy_anomaly")

        # Very low clustering = dispersed attention
        if topology.clustering_coefficient < 0.1:
            anomalies.append("low_clustering")

        if anomalies:
            topology.is_anomalous = True
            topology.anomaly_reason = ", ".join(anomalies)

        return topology


# ============================================================================
# Topological Fingerprinting
# ============================================================================

class TopologicalFingerprinter:
    """
    Creates unique topological fingerprints of prompts/responses.

    Use cases:
    - Attack pattern database
    - Model behavior fingerprinting
    - Anomaly signature matching
    """

    def __init__(self, num_landscapes: int = 3, resolution: int = 50):
        self.num_landscapes = num_landscapes
        self.resolution = resolution

    def fingerprint(
        self,
        embeddings: np.ndarray,
        diagram: Optional[PersistenceDiagram] = None
    ) -> TopologicalFingerprint:
        """
        Create topological fingerprint from embeddings.
        """
        # Compute diagram if not provided
        if diagram is None:
            diagram = self._quick_persistence(embeddings)

        # Betti signature
        betti_sig = (
            diagram.betti_number(0),
            diagram.betti_number(1),
            diagram.betti_number(2)
        )

        # Persistence signature
        pers_sig = (
            diagram.total_persistence(0),
            diagram.total_persistence(1),
            diagram.total_persistence(2)
        )

        # Entropy signature
        entropy_sig = (
            diagram.entropy(0),
            diagram.entropy(1),
            diagram.entropy(2)
        )

        # Landscape hash
        landscape = self._compute_landscape(diagram)
        landscape_hash = hashlib.md5(landscape.tobytes()).hexdigest()[:16]

        # Generate ID
        fp_id = hashlib.sha256(
            f"{betti_sig}{pers_sig}{landscape_hash}".encode()
        ).hexdigest()[:12]

        return TopologicalFingerprint(
            fingerprint_id=fp_id,
            betti_signature=betti_sig,
            persistence_signature=pers_sig,
            entropy_signature=entropy_sig,
            landscape_hash=landscape_hash
        )

    def _quick_persistence(self, embeddings: np.ndarray) -> PersistenceDiagram:
        """Quick persistence computation for fingerprinting."""
        diagram = PersistenceDiagram()

        if len(embeddings) < 3:
            return diagram

        # Use distance-based approximation
        n = len(embeddings)
        dists = []
        for i in range(min(n, 50)):
            for j in range(i + 1, min(n, 50)):
                dists.append(np.linalg.norm(embeddings[i] - embeddings[j]))

        if not dists:
            return diagram

        dists = sorted(dists)

        # Create approximate pairs
        for i, d in enumerate(dists[:10]):
            diagram.pairs.append(PersistencePair(0, d, 0))

        for i, d in enumerate(dists[10:15]):
            diagram.pairs.append(PersistencePair(d * 0.5, d, 1))

        return diagram

    def _compute_landscape(self, diagram: PersistenceDiagram) -> np.ndarray:
        """Compute persistence landscape for hashing."""
        landscape = np.zeros((self.num_landscapes, self.resolution))

        pairs = diagram.get_pairs(1)  # Use H1
        if not pairs:
            return landscape

        # Get range
        all_values = []
        for p in pairs:
            if p.death < np.inf:
                all_values.extend([p.birth, p.death])

        if not all_values:
            return landscape

        t_min, t_max = min(all_values), max(all_values)
        if t_max <= t_min:
            return landscape

        t_grid = np.linspace(t_min, t_max, self.resolution)

        for i, t in enumerate(t_grid):
            heights = []
            for p in pairs:
                if p.birth <= t <= p.death and p.death < np.inf:
                    mid = (p.birth + p.death) / 2
                    half_life = (p.death - p.birth) / 2
                    height = half_life - abs(t - mid)
                    heights.append(max(0, height))

            heights = sorted(heights, reverse=True)
            for k in range(min(len(heights), self.num_landscapes)):
                landscape[k, i] = heights[k]

        return landscape


# ============================================================================
# Main Enhanced TDA Engine
# ============================================================================

class TDAEnhancedEngine:
    """
    Enhanced TDA Engine with 2025 research techniques.

    Provides:
    - Standard persistent homology
    - Zigzag persistence for layer analysis
    - Attention topology analysis
    - Topological fingerprinting
    - Multiple distance metrics
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}

        self.zigzag = ZigzagEngine(max_dim=1)
        self.attention_tda = AttentionTopologyEngine()
        self.fingerprinter = TopologicalFingerprinter()
        self.distance = PersistenceDistance()

        self.fingerprint_db: List[TopologicalFingerprint] = []

        logger.info("TDAEnhancedEngine initialized with 2025 techniques")

    def analyze_embeddings(
        self,
        embeddings: np.ndarray
    ) -> Dict[str, Any]:
        """Full TDA analysis of embeddings."""
        # Create fingerprint
        fingerprint = self.fingerprinter.fingerprint(embeddings)

        # Check against known patterns
        matches = self.find_similar_fingerprints(fingerprint, threshold=0.8)

        return {
            "fingerprint": {
                "id": fingerprint.fingerprint_id,
                "betti": fingerprint.betti_signature,
                "persistence": fingerprint.persistence_signature,
                "entropy": fingerprint.entropy_signature
            },
            "similar_patterns": len(matches),
            "is_known_pattern": len(matches) > 0
        }

    def analyze_layer_sequence(
        self,
        layer_activations: List[np.ndarray]
    ) -> Dict[str, Any]:
        """Zigzag persistence analysis of layer sequence."""
        zigzag_result = self.zigzag.analyze_layer_sequence(layer_activations)

        return {
            "num_layers": len(zigzag_result.layer_diagrams),
            "h0_flow": zigzag_result.feature_flow(0),
            "h1_flow": zigzag_result.feature_flow(1),
            "stability_score": zigzag_result.stability_score(),
            "transitions": zigzag_result.transitions
        }

    def analyze_attention(
        self,
        attention_matrix: np.ndarray
    ) -> Dict[str, Any]:
        """Attention pattern topology analysis."""
        result = self.attention_tda.analyze_attention(attention_matrix)

        return {
            "betti_numbers": result.graph_betti,
            "entropy": result.attention_entropy,
            "sparsity": result.sparsity,
            "clustering": result.clustering_coefficient,
            "is_anomalous": result.is_anomalous,
            "anomaly_reason": result.anomaly_reason
        }

    def compute_diagram_distance(
        self,
        dgm1: np.ndarray,
        dgm2: np.ndarray,
        metric: str = "wasserstein"
    ) -> float:
        """Compute distance between persistence diagrams."""
        if metric == "wasserstein":
            return self.distance.wasserstein_distance(dgm1, dgm2)
        elif metric == "bottleneck":
            return self.distance.bottleneck_distance(dgm1, dgm2)
        else:
            raise ValueError(f"Unknown metric: {metric}")

    def add_fingerprint(self, fingerprint: TopologicalFingerprint):
        """Add fingerprint to database."""
        self.fingerprint_db.append(fingerprint)

    def find_similar_fingerprints(
        self,
        query: TopologicalFingerprint,
        threshold: float = 0.8
    ) -> List[Tuple[TopologicalFingerprint, float]]:
        """Find similar fingerprints in database."""
        matches = []
        for fp in self.fingerprint_db:
            sim = query.similarity(fp)
            if sim >= threshold:
                matches.append((fp, sim))
        return sorted(matches, key=lambda x: -x[1])

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            "fingerprints_stored": len(self.fingerprint_db),
            "capabilities": [
                "zigzag_persistence",
                "attention_topology",
                "topological_fingerprinting",
                "bottleneck_distance",
                "wasserstein_distance"
            ]
        }
