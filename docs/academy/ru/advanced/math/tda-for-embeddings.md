# TDA for Embedding Analysis

> **Level:** Expert  
> **Время:** 55 минут  
> **Track:** 06 — Mathematical Foundations  
> **Module:** 06.1 — TDA (Topological Data Analysis)  
> **Version:** 1.0

---

## Цели обучения

- [ ] Understand topological properties of embedding spaces
- [ ] Apply TDA methods to LLM embedding analysis
- [ ] Integrate TDA-based detection in security pipeline
- [ ] Use persistence diagrams for distribution comparison

---

## 1. Embeddings and Topology

### 1.1 Why TDA for Embeddings?

LLM embeddings form complex manifolds in high-dimensional space. TDA allows analyzing their structure.

```
┌────────────────────────────────────────────────────────────────────┐
│              EMBEDDINGS AS TOPOLOGICAL OBJECT                       │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  Text → [LLM Encoder] → Embedding ∈ ℝⁿ (n = 384, 768, 1536...)    │
│                                                                    │
│  Collection of embeddings = Point Cloud in ℝⁿ                      │
│                                                                    │
│  TDA extracts:                                                     │
│  ├── H₀: Connected components (meaning clusters)                  │
│  ├── H₁: Cycles/holes (semantic loops)                            │
│  └── H₂: Voids (complex semantic structures)                      │
│                                                                    │
│  Security Application:                                             │
│  ├── Normal embeddings → stable topology                          │
│  ├── Attack embeddings → new/changed features                     │
│  └── Обнаружение = comparing persistence diagrams                   │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

### 1.2 Metrics in Embedding Space

```python
import numpy as np
from scipy.spatial.distance import pdist, squareform
from sklearn.metrics.pairwise import cosine_distances

class EmbeddingMetrics:
    """Various metrics for embedding space"""
    
    @staticmethod
    def euclidean_distance_matrix(embeddings: np.ndarray) -> np.ndarray:
        """Standard Euclidean distance"""
        return squareform(pdist(embeddings, metric='euclidean'))
    
    @staticmethod
    def cosine_distance_matrix(embeddings: np.ndarray) -> np.ndarray:
        """
        Cosine distance — more suitable for embeddings,
        as directions matter, not magnitude.
        """
        return cosine_distances(embeddings)
    
    @staticmethod
    def normalized_euclidean(embeddings: np.ndarray) -> np.ndarray:
        """Euclidean metric after L2 normalization"""
        normalized = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
        return squareform(pdist(normalized, metric='euclidean'))
    
    @staticmethod
    def angular_distance(embeddings: np.ndarray) -> np.ndarray:
        """
        Angular distance — arccos of cosine similarity.
        Metric (satisfies triangle inequality).
        """
        cos_sim = np.dot(embeddings, embeddings.T)
        norms = np.linalg.norm(embeddings, axis=1)
        cos_sim = cos_sim / np.outer(norms, norms)
        cos_sim = np.clip(cos_sim, -1, 1)  # Numerical stability
        return np.arccos(cos_sim) / np.pi  # Normalize to [0, 1]
```

---

## 2. Persistence Homology for Embeddings

### 2.1 Vietoris-Rips Complex

```python
from ripser import ripser
from persim import plot_diagrams, wasserstein, bottleneck
import matplotlib.pyplot as plt

class EmbeddingPersistence:
    """
    Persistent Homology for embedding space analysis.
    Uses Vietoris-Rips filtration.
    """
    
    def __init__(self, max_dim: int = 1, max_edge_length: float = np.inf):
        """
        Args:
            max_dim: Maximum homology dimension (0, 1, 2)
            max_edge_length: Maximum edge length in filtration
        """
        self.max_dim = max_dim
        self.max_edge_length = max_edge_length
        self.diagrams = None
        self.distance_matrix = None
    
    def compute(self, embeddings: np.ndarray, 
                metric: str = 'cosine') -> dict:
        """
        Computes persistent homology for embeddings.
        
        Args:
            embeddings: Embedding matrix (n_samples, n_features)
            metric: 'euclidean', 'cosine', or 'angular'
        
        Returns:
            Dictionary with diagrams and statistics
        """
        # Compute distance matrix
        if metric == 'euclidean':
            self.distance_matrix = EmbeddingMetrics.euclidean_distance_matrix(embeddings)
        elif metric == 'cosine':
            self.distance_matrix = EmbeddingMetrics.cosine_distance_matrix(embeddings)
        elif metric == 'angular':
            self.distance_matrix = EmbeddingMetrics.angular_distance(embeddings)
        else:
            raise ValueError(f"Unknown metric: {metric}")
        
        # Ripser for persistent homology
        result = ripser(
            self.distance_matrix,
            maxdim=self.max_dim,
            thresh=self.max_edge_length,
            distance_matrix=True
        )
        
        self.diagrams = result['dgms']
        
        return {
            'diagrams': self.diagrams,
            'h0_features': len(self.diagrams[0]),
            'h1_features': len(self.diagrams[1]) if self.max_dim >= 1 else 0,
            'statistics': self._compute_statistics()
        }
    
    def _compute_statistics(self) -> dict:
        """Computes persistence diagram statistics"""
        stats = {}
        
        for dim, dgm in enumerate(self.diagrams):
            if len(dgm) == 0:
                continue
            
            # Lifetime = death - birth
            lifetimes = dgm[:, 1] - dgm[:, 0]
            # Filter inf
            finite_lifetimes = lifetimes[np.isfinite(lifetimes)]
            
            if len(finite_lifetimes) > 0:
                stats[f'H{dim}_count'] = len(dgm)
                stats[f'H{dim}_mean_lifetime'] = np.mean(finite_lifetimes)
                stats[f'H{dim}_max_lifetime'] = np.max(finite_lifetimes)
                stats[f'H{dim}_std_lifetime'] = np.std(finite_lifetimes)
                stats[f'H{dim}_total_persistence'] = np.sum(finite_lifetimes)
        
        return stats
    
    def get_persistent_features(self, min_persistence: float = 0.1) -> dict:
        """
        Returns only persistent features (with large lifetime).
        
        Args:
            min_persistence: Minimum lifetime for feature
        
        Returns:
            Stable features by dimension
        """
        persistent = {}
        
        for dim, dgm in enumerate(self.diagrams):
            lifetimes = dgm[:, 1] - dgm[:, 0]
            mask = (lifetimes >= min_persistence) & np.isfinite(lifetimes)
            persistent[f'H{dim}'] = dgm[mask]
        
        return persistent
    
    def plot(self, save_path: str = None):
        """Visualize persistence diagrams"""
        if self.diagrams is None:
            raise ValueError("Call compute() first")
        
        fig, axes = plt.subplots(1, self.max_dim + 1, figsize=(5 * (self.max_dim + 1), 4))
        
        if self.max_dim == 0:
            axes = [axes]
        
        plot_diagrams(self.diagrams, ax=axes[0], show=False)
        
        for i, ax in enumerate(axes):
            ax.set_title(f'H{i} Persistence Diagram')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path)
        
        return fig
```

### 2.2 Comparing Persistence Diagrams

```python
class PersistenceComparator:
    """
    Comparison of persistence diagrams for detection.
    Uses Wasserstein and Bottleneck distances.
    """
    
    def __init__(self):
        self.baseline_diagrams = None
    
    def set_baseline(self, diagrams: list):
        """Sets baseline diagrams"""
        self.baseline_diagrams = diagrams
    
    def compare(self, target_diagrams: list) -> dict:
        """
        Compares target diagrams with baseline.
        
        Args:
            target_diagrams: Diagrams to compare
        
        Returns:
            Distances by dimension
        """
        if self.baseline_diagrams is None:
            raise ValueError("Set baseline first")
        
        results = {}
        
        for dim in range(min(len(self.baseline_diagrams), len(target_diagrams))):
            baseline_dgm = self.baseline_diagrams[dim]
            target_dgm = target_diagrams[dim]
            
            # Wasserstein distance (p=2)
            try:
                w_dist = wasserstein(baseline_dgm, target_dgm, matching=False)
            except:
                w_dist = float('inf')
            
            # Bottleneck distance
            try:
                b_dist = bottleneck(baseline_dgm, target_dgm, matching=False)
            except:
                b_dist = float('inf')
            
            results[f'H{dim}_wasserstein'] = w_dist
            results[f'H{dim}_bottleneck'] = b_dist
        
        return results
    
    def is_anomaly(self, target_diagrams: list, 
                   wasserstein_threshold: float = 0.5,
                   bottleneck_threshold: float = 0.3) -> dict:
        """
        Determines if target is anomalous.
        
        Args:
            target_diagrams: Diagrams to check
            wasserstein_threshold: Threshold for Wasserstein
            bottleneck_threshold: Threshold for Bottleneck
        
        Returns:
            Anomaly detection result
        """
        distances = self.compare(target_diagrams)
        
        anomalies = []
        for key, value in distances.items():
            if 'wasserstein' in key and value > wasserstein_threshold:
                anomalies.append({
                    'metric': key,
                    'value': value,
                    'threshold': wasserstein_threshold
                })
            elif 'bottleneck' in key and value > bottleneck_threshold:
                anomalies.append({
                    'metric': key,
                    'value': value,
                    'threshold': bottleneck_threshold
                })
        
        return {
            'is_anomaly': len(anomalies) > 0,
            'distances': distances,
            'violations': anomalies
        }
```

---

## 3. Topological Signatures for Texts

### 3.1 Embedding Topology Signature

```python
from sentence_transformers import SentenceTransformer
from typing import List
import hashlib

class TopologicalSignature:
    """
    Topological signature of text corpus.
    Used for comparison and change detection.
    """
    
    def __init__(self, embedding_model: str = "all-MiniLM-L6-v2"):
        self.encoder = SentenceTransformer(embedding_model)
        self.persistence = EmbeddingPersistence(max_dim=1)
    
    def compute_signature(self, texts: List[str], 
                         metric: str = 'cosine') -> dict:
        """
        Computes topological signature for texts.
        
        Args:
            texts: List of texts
            metric: Metric for embeddings
        
        Returns:
            Topological signature
        """
        # Embeddings
        embeddings = self.encoder.encode(texts)
        
        # Persistent homology
        result = self.persistence.compute(embeddings, metric=metric)
        
        # Extract key features
        signature = {
            'n_texts': len(texts),
            'embedding_dim': embeddings.shape[1],
            'metric': metric,
            
            # H0 features
            'h0_count': result['statistics'].get('H0_count', 0),
            'h0_mean_lifetime': result['statistics'].get('H0_mean_lifetime', 0),
            'h0_max_lifetime': result['statistics'].get('H0_max_lifetime', 0),
            
            # H1 features
            'h1_count': result['statistics'].get('H1_count', 0),
            'h1_mean_lifetime': result['statistics'].get('H1_mean_lifetime', 0),
            'h1_total_persistence': result['statistics'].get('H1_total_persistence', 0),
            
            # Diagrams
            'diagrams': result['diagrams']
        }
        
        # Signature hash
        signature['hash'] = self._compute_hash(signature)
        
        return signature
    
    def _compute_hash(self, signature: dict) -> str:
        """Computes hash of signature for quick comparison"""
        key_values = [
            signature['h0_count'],
            round(signature['h0_mean_lifetime'], 3),
            signature['h1_count'],
            round(signature['h1_mean_lifetime'], 3)
        ]
        return hashlib.md5(str(key_values).encode()).hexdigest()[:16]
    
    def compare_signatures(self, sig1: dict, sig2: dict) -> dict:
        """
        Compares two topological signatures.
        
        Args:
            sig1: First signature
            sig2: Second signature
        
        Returns:
            Comparison result
        """
        # Compare basic statistics
        stat_diffs = {}
        for key in ['h0_count', 'h0_mean_lifetime', 'h1_count', 'h1_mean_lifetime']:
            diff = sig2.get(key, 0) - sig1.get(key, 0)
            rel_diff = diff / (sig1.get(key, 1) + 1e-10)
            stat_diffs[key] = {
                'absolute': diff,
                'relative': rel_diff
            }
        
        # Diagram distances
        comparator = PersistenceComparator()
        comparator.set_baseline(sig1['diagrams'])
        diagram_dists = comparator.compare(sig2['diagrams'])
        
        return {
            'hash_match': sig1['hash'] == sig2['hash'],
            'statistic_differences': stat_diffs,
            'diagram_distances': diagram_dists,
            'is_similar': self._assess_similarity(stat_diffs, diagram_dists)
        }
    
    def _assess_similarity(self, stat_diffs: dict, diagram_dists: dict) -> bool:
        """Assesses overall signature similarity"""
        # Relative changes < 50%
        for key, diff in stat_diffs.items():
            if abs(diff['relative']) > 0.5:
                return False
        
        # Diagram distances reasonable
        for key, dist in diagram_dists.items():
            if 'wasserstein' in key and dist > 0.5:
                return False
        
        return True
```

### 3.2 Sliding Window TDA

```python
class SlidingWindowTDA:
    """
    TDA analysis with sliding window for streaming data.
    Tracks topology changes over time.
    """
    
    def __init__(self, 
                 window_size: int = 100,
                 step_size: int = 20,
                 embedding_model: str = "all-MiniLM-L6-v2"):
        self.window_size = window_size
        self.step_size = step_size
        self.encoder = SentenceTransformer(embedding_model)
        self.persistence = EmbeddingPersistence(max_dim=1)
        
        self.history = []
        self.current_window = []
    
    def add_text(self, text: str) -> dict:
        """
        Adds text and updates analysis.
        
        Args:
            text: New text
        
        Returns:
            Window analysis result (if step_size reached)
        """
        self.current_window.append(text)
        
        if len(self.current_window) >= self.window_size:
            # Analyze window
            result = self._analyze_window()
            
            # Compare with previous
            if self.history:
                change = self._detect_change(result)
                result['change_detected'] = change
            
            self.history.append(result)
            
            # Shift window
            self.current_window = self.current_window[self.step_size:]
            
            return result
        
        return None
    
    def _analyze_window(self) -> dict:
        """Analyzes current window"""
        embeddings = self.encoder.encode(self.current_window)
        result = self.persistence.compute(embeddings, metric='cosine')
        
        return {
            'window_start': len(self.history) * self.step_size,
            'window_texts': len(self.current_window),
            'statistics': result['statistics'],
            'diagrams': result['diagrams']
        }
    
    def _detect_change(self, current: dict) -> dict:
        """Detects changes relative to previous window"""
        prev = self.history[-1]
        
        comparator = PersistenceComparator()
        comparator.set_baseline(prev['diagrams'])
        distances = comparator.compare(current['diagrams'])
        
        # Check for anomaly
        anomaly = comparator.is_anomaly(
            current['diagrams'],
            wasserstein_threshold=0.3,
            bottleneck_threshold=0.2
        )
        
        return {
            'distances': distances,
            'is_anomaly': anomaly['is_anomaly'],
            'violations': anomaly['violations']
        }
    
    def get_trend(self) -> dict:
        """Returns topology change trend"""
        if len(self.history) < 2:
            return {'status': 'insufficient_data'}
        
        h0_counts = [h['statistics'].get('H0_count', 0) for h in self.history]
        h1_counts = [h['statistics'].get('H1_count', 0) for h in self.history]
        
        return {
            'n_windows': len(self.history),
            'h0_trend': np.polyfit(range(len(h0_counts)), h0_counts, 1)[0],
            'h1_trend': np.polyfit(range(len(h1_counts)), h1_counts, 1)[0],
            'h0_variance': np.var(h0_counts),
            'h1_variance': np.var(h1_counts)
        }
```

---

## 4. Security Applications

### 4.1 Injection Обнаружение via TDA

```python
class TDAInjectionDetector:
    """
    Prompt injection detector based on TDA.
    Uses topological changes in embedding space.
    """
    
    def __init__(self, embedding_model: str = "all-MiniLM-L6-v2"):
        self.encoder = SentenceTransformer(embedding_model)
        self.persistence = EmbeddingPersistence(max_dim=1)
        self.comparator = PersistenceComparator()
        
        self.baseline_signature = None
        self.thresholds = {
            'wasserstein': 0.4,
            'bottleneck': 0.25,
            'h1_count_change': 3
        }
    
    def train(self, normal_texts: List[str]):
        """
        Training on normal data.
        Builds baseline topological signature.
        """
        embeddings = self.encoder.encode(normal_texts)
        result = self.persistence.compute(embeddings, metric='cosine')
        
        self.baseline_signature = {
            'diagrams': result['diagrams'],
            'statistics': result['statistics'],
            'n_samples': len(normal_texts)
        }
        
        self.comparator.set_baseline(result['diagrams'])
    
    def detect(self, texts: List[str]) -> dict:
        """
        Injection detection in texts.
        
        Args:
            texts: Texts for analysis
        
        Returns:
            Обнаружение result
        """
        if self.baseline_signature is None:
            raise ValueError("Train the detector first")
        
        # Compute embeddings and persistence
        embeddings = self.encoder.encode(texts)
        result = self.persistence.compute(embeddings, metric='cosine')
        
        # Compare with baseline
        anomaly_check = self.comparator.is_anomaly(
            result['diagrams'],
            wasserstein_threshold=self.thresholds['wasserstein'],
            bottleneck_threshold=self.thresholds['bottleneck']
        )
        
        # Additional checks
        h1_baseline = self.baseline_signature['statistics'].get('H1_count', 0)
        h1_current = result['statistics'].get('H1_count', 0)
        h1_change = abs(h1_current - h1_baseline)
        
        # Aggregate detection
        is_injection = anomaly_check['is_anomaly'] or h1_change > self.thresholds['h1_count_change']
        
        # Confidence score
        confidence = self._compute_confidence(anomaly_check['distances'], h1_change)
        
        return {
            'is_injection': is_injection,
            'confidence': confidence,
            'distances': anomaly_check['distances'],
            'violations': anomaly_check['violations'],
            'h1_change': h1_change,
            'current_statistics': result['statistics'],
            'recommendation': self._get_recommendation(is_injection, confidence)
        }
    
    def _compute_confidence(self, distances: dict, h1_change: int) -> float:
        """Computes confidence score"""
        score = 0.0
        
        # Wasserstein contribution
        w_h0 = distances.get('H0_wasserstein', 0)
        w_h1 = distances.get('H1_wasserstein', 0)
        score += min(w_h0 / self.thresholds['wasserstein'], 1.0) * 0.3
        score += min(w_h1 / self.thresholds['wasserstein'], 1.0) * 0.3
        
        # H1 change contribution
        score += min(h1_change / self.thresholds['h1_count_change'], 1.0) * 0.4
        
        return min(score, 1.0)
    
    def _get_recommendation(self, is_injection: bool, confidence: float) -> str:
        """Recommendations based on result"""
        if not is_injection:
            return "SAFE: Topology matches baseline"
        elif confidence < 0.5:
            return "LOW_RISK: Minor topological changes"
        elif confidence < 0.8:
            return "MEDIUM_RISK: Significant changes, review recommended"
        else:
            return "HIGH_RISK: Strong topological anomalies, possible injection"
```

### 4.2 Multi-Modal TDA Обнаружение

```python
class MultiModalTDADetector:
    """
    Multi-modal detector combining TDA features with other methods.
    """
    
    def __init__(self, embedding_model: str = "all-MiniLM-L6-v2"):
        self.encoder = SentenceTransformer(embedding_model)
        self.tda_detector = TDAInjectionDetector(embedding_model)
        
        # Feature weights
        self.weights = {
            'tda': 0.4,
            'semantic': 0.3,
            'structural': 0.3
        }
    
    def train(self, normal_texts: List[str], attack_texts: List[str] = None):
        """
        Training on normal (and optionally attack) data.
        """
        self.tda_detector.train(normal_texts)
        
        # Semantic baseline
        self.normal_embeddings = self.encoder.encode(normal_texts)
        self.normal_centroid = np.mean(self.normal_embeddings, axis=0)
        self.normal_radius = np.max(
            np.linalg.norm(self.normal_embeddings - self.normal_centroid, axis=1)
        )
        
        # Attack patterns (if provided)
        self.attack_embeddings = None
        if attack_texts:
            self.attack_embeddings = self.encoder.encode(attack_texts)
    
    def detect(self, texts: List[str]) -> dict:
        """
        Multi-modal detection.
        
        Returns:
            Combined detection result
        """
        embeddings = self.encoder.encode(texts)
        
        # 1. TDA Обнаружение
        tda_result = self.tda_detector.detect(texts)
        tda_score = tda_result['confidence']
        
        # 2. Semantic Обнаружение (distance from centroid)
        distances = np.linalg.norm(embeddings - self.normal_centroid, axis=1)
        outside_radius = np.mean(distances > self.normal_radius * 1.5)
        semantic_score = outside_radius
        
        # 3. Structural Обнаружение (similarity to known attacks)
        structural_score = 0.0
        if self.attack_embeddings is not None:
            # Max similarity to any attack
            for emb in embeddings:
                sims = np.dot(self.attack_embeddings, emb) / (
                    np.linalg.norm(self.attack_embeddings, axis=1) * np.linalg.norm(emb)
                )
                structural_score = max(structural_score, np.max(sims))
        
        # Combined score
        combined_score = (
            self.weights['tda'] * tda_score +
            self.weights['semantic'] * semantic_score +
            self.weights['structural'] * structural_score
        )
        
        return {
            'is_attack': combined_score > 0.5,
            'combined_score': combined_score,
            'scores': {
                'tda': tda_score,
                'semantic': semantic_score,
                'structural': structural_score
            },
            'tda_details': tda_result,
            'recommendation': self._get_recommendation(combined_score)
        }
    
    def _get_recommendation(self, score: float) -> str:
        if score < 0.3:
            return "SAFE"
        elif score < 0.5:
            return "LOW_RISK: Monitor closely"
        elif score < 0.7:
            return "MEDIUM_RISK: Review required"
        else:
            return "HIGH_RISK: Block and investigate"
```

---

## 5. SENTINEL Интеграция

```python
from dataclasses import dataclass
from enum import Enum

class RiskLevel(Enum):
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class TDASecurityConfig:
    """TDA Security Engine configuration"""
    embedding_model: str = "all-MiniLM-L6-v2"
    max_homology_dim: int = 1
    wasserstein_threshold: float = 0.4
    bottleneck_threshold: float = 0.25
    metric: str = "cosine"
    use_multimodal: bool = True

class SENTINELTDAEngine:
    """
    TDA Engine for SENTINEL framework.
    Provides topological analysis for security detection.
    """
    
    def __init__(self, config: TDASecurityConfig):
        self.config = config
        
        if config.use_multimodal:
            self.detector = MultiModalTDADetector(config.embedding_model)
        else:
            self.detector = TDAInjectionDetector(config.embedding_model)
        
        self.signature_cache = {}
        self.is_trained = False
    
    def train(self, 
              normal_texts: List[str],
              attack_texts: List[str] = None,
              signature_name: str = "default"):
        """
        Train engine on data.
        
        Args:
            normal_texts: Normal texts
            attack_texts: Attack texts (optional)
            signature_name: Signature name for caching
        """
        if self.config.use_multimodal:
            self.detector.train(normal_texts, attack_texts)
        else:
            self.detector.train(normal_texts)
        
        # Save signature
        sig_computer = TopologicalSignature(self.config.embedding_model)
        self.signature_cache[signature_name] = sig_computer.compute_signature(
            normal_texts, self.config.metric
        )
        
        self.is_trained = True
    
    def analyze(self, texts: List[str]) -> dict:
        """
        Analyze texts.
        
        Returns:
            Full analysis result
        """
        if not self.is_trained:
            raise RuntimeError("Train the engine first")
        
        result = self.detector.detect(texts)
        
        # Determine risk level
        score = result.get('combined_score', result.get('confidence', 0))
        risk_level = self._determine_risk_level(score)
        
        return {
            'risk_level': risk_level.value,
            'is_attack': result.get('is_attack', result.get('is_injection', False)),
            'score': score,
            'details': result,
            'action': self._get_action(risk_level)
        }
    
    def _determine_risk_level(self, score: float) -> RiskLevel:
        if score < 0.2:
            return RiskLevel.SAFE
        elif score < 0.4:
            return RiskLevel.LOW
        elif score < 0.6:
            return RiskLevel.MEDIUM
        elif score < 0.8:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL
    
    def _get_action(self, risk_level: RiskLevel) -> str:
        actions = {
            RiskLevel.SAFE: "ALLOW",
            RiskLevel.LOW: "ALLOW_WITH_LOGGING",
            RiskLevel.MEDIUM: "REQUIRE_REVIEW",
            RiskLevel.HIGH: "BLOCK_PENDING_REVIEW",
            RiskLevel.CRITICAL: "BLOCK_AND_ALERT"
        }
        return actions.get(risk_level, "BLOCK")
```

---

## 6. Summary

| Component | Description |
|-----------|-------------|
| **Persistence Homology** | Extracts H₀, H₁ features from embedding space |
| **Wasserstein/Bottleneck** | Metrics for comparing persistence diagrams |
| **Topological Signature** | Compact representation of corpus topology |
| **Sliding Window TDA** | Real-time topology tracking |
| **Multi-Modal Обнаружение** | Combining TDA with semantics and structure |

---

## Next Lesson

→ [Track 07: Governance](../../07-governance/README.md)

---

*AI Security Academy (RU) | Track 06: Mathematical Foundations | Module 06.1: TDA*
