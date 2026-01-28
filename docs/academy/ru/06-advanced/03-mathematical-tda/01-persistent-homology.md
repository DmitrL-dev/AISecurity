# Persistent Homology for LLM Security

> **Level:** Expert  
> **Время:** 60 минут  
> **Track:** 06 — Mathematical Foundations  
> **Module:** 06.1 — TDA (Topological Data Analysis)  
> **Version:** 1.0

---

## Цели обучения

- [ ] Understand persistent homology fundamentals
- [ ] Apply TDA to embedding space analysis
- [ ] Detect anomalies through topological features

---

## 1. Введение to Persistent Homology

### 1.1 Что такое Topology?

**Topology** studies properties of space invariant under continuous deformation.

```
┌────────────────────────────────────────────────────────────────────┐
│                    TOPOLOGICAL FEATURES                             │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  H₀: Connected Components (clusters)                               │
│      • • •   → 3 components                                        │
│      •••     → 1 component                                         │
│                                                                    │
│  H₁: Loops (1-dimensional holes)                                   │
│      ○      → 1 loop                                               │
│      ∞      → 2 loops                                              │
│                                                                    │
│  H₂: Voids (2-dimensional holes)                                   │
│      ◯ (sphere shell) → 1 void                                     │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

### 1.2 Persistent Homology Concept

```
Persistence:
├── Build simplicial complex at different scales
├── Track when features (holes) appear (birth)
├── Track when features disappear (death)
└── Persistence = death - birth
    (longer persistence = more significant feature)
```

---

## 2. Mathematical Foundation

### 2.1 Simplicial Complex

```python
from itertools import combinations
import numpy as np

class SimplicialComplex:
    """Representation of simplicial complex"""
    
    def __init__(self):
        self.simplices = {}  # dimension -> list of simplices
    
    def add_vertex(self, vertex_id: int):
        """Add 0-simplex (vertex)"""
        if 0 not in self.simplices:
            self.simplices[0] = set()
        self.simplices[0].add((vertex_id,))
    
    def add_edge(self, v1: int, v2: int):
        """Add 1-simplex (edge)"""
        if 1 not in self.simplices:
            self.simplices[1] = set()
        self.simplices[1].add(tuple(sorted([v1, v2])))
    
    def add_triangle(self, v1: int, v2: int, v3: int):
        """Add 2-simplex (triangle)"""
        if 2 not in self.simplices:
            self.simplices[2] = set()
        self.simplices[2].add(tuple(sorted([v1, v2, v3])))
    
    def boundary(self, simplex: tuple) -> list:
        """Compute boundary of simplex"""
        if len(simplex) == 1:
            return []
        
        return [
            tuple(simplex[:i] + simplex[i+1:])
            for i in range(len(simplex))
        ]
```

### 2.2 Vietoris-Rips Complex

```python
from scipy.spatial.distance import pdist, squareform

class VietorisRipsComplex:
    """Build Vietoris-Rips complex from point cloud"""
    
    def __init__(self, points: np.ndarray, max_dim: int = 2):
        self.points = points
        self.max_dim = max_dim
        self.distances = squareform(pdist(points))
    
    def build_complex(self, epsilon: float) -> SimplicialComplex:
        """Build complex at scale epsilon"""
        n = len(self.points)
        complex = SimplicialComplex()
        
        # Add vertices
        for i in range(n):
            complex.add_vertex(i)
        
        # Add edges
        for i in range(n):
            for j in range(i + 1, n):
                if self.distances[i, j] <= epsilon:
                    complex.add_edge(i, j)
        
        # Add triangles (if max_dim >= 2)
        if self.max_dim >= 2:
            for i in range(n):
                for j in range(i + 1, n):
                    for k in range(j + 1, n):
                        if (self.distances[i, j] <= epsilon and
                            self.distances[j, k] <= epsilon and
                            self.distances[i, k] <= epsilon):
                            complex.add_triangle(i, j, k)
        
        return complex
    
    def filtration(self, epsilons: list) -> list:
        """Build filtration (sequence of complexes)"""
        return [self.build_complex(eps) for eps in epsilons]
```

### 2.3 Persistence Diagram

```python
from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class PersistenceInterval:
    dimension: int  # H₀, H₁, H₂
    birth: float
    death: float  # np.inf for features that never die
    
    @property
    def persistence(self) -> float:
        return self.death - self.birth

class PersistenceDiagram:
    def __init__(self, intervals: List[PersistenceInterval]):
        self.intervals = intervals
    
    def get_by_dimension(self, dim: int) -> List[PersistenceInterval]:
        return [i for i in self.intervals if i.dimension == dim]
    
    def betti_number(self, dim: int, threshold: float) -> int:
        """Count features alive at threshold"""
        return sum(
            1 for i in self.intervals
            if i.dimension == dim and i.birth <= threshold < i.death
        )
    
    def to_array(self, dim: int) -> np.ndarray:
        """Convert to (birth, death) array for dim"""
        intervals = self.get_by_dimension(dim)
        return np.array([[i.birth, i.death] for i in intervals])
```

---

## 3. Computing Persistent Homology

### 3.1 Using Ripser (Fast Реализация)

```python
import ripser
import numpy as np
from persim import plot_diagrams, wasserstein, bottleneck

class PersistentHomologyComputer:
    def __init__(self, max_dim: int = 2, max_epsilon: float = 2.0):
        self.max_dim = max_dim
        self.max_epsilon = max_epsilon
    
    def compute(self, points: np.ndarray) -> PersistenceDiagram:
        """Compute persistent homology using Ripser"""
        result = ripser.ripser(
            points,
            maxdim=self.max_dim,
            thresh=self.max_epsilon
        )
        
        intervals = []
        for dim, dgm in enumerate(result['dgms']):
            for birth, death in dgm:
                intervals.append(PersistenceInterval(
                    dimension=dim,
                    birth=float(birth),
                    death=float(death) if not np.isinf(death) else np.inf
                ))
        
        return PersistenceDiagram(intervals)
    
    def distance_matrix_persistence(self, 
                                   dist_matrix: np.ndarray) -> PersistenceDiagram:
        """Compute from precomputed distances"""
        result = ripser.ripser(
            dist_matrix,
            distance_matrix=True,
            maxdim=self.max_dim,
            thresh=self.max_epsilon
        )
        
        intervals = []
        for dim, dgm in enumerate(result['dgms']):
            for birth, death in dgm:
                intervals.append(PersistenceInterval(
                    dimension=dim,
                    birth=float(birth),
                    death=float(death) if not np.isinf(death) else np.inf
                ))
        
        return PersistenceDiagram(intervals)
```

### 3.2 Embedding Space Analysis

```python
from sentence_transformers import SentenceTransformer

class EmbeddingPersistence:
    def __init__(self, embedding_model: str = "all-MiniLM-L6-v2"):
        self.encoder = SentenceTransformer(embedding_model)
        self.ph_computer = PersistentHomologyComputer()
    
    def analyze_texts(self, texts: List[str]) -> PersistenceDiagram:
        """Analyze topological structure of text embeddings"""
        embeddings = self.encoder.encode(texts)
        return self.ph_computer.compute(embeddings)
    
    def compare_distributions(self, 
                             texts1: List[str], 
                             texts2: List[str]) -> dict:
        """Compare topological structure of two text sets"""
        dgm1 = self.analyze_texts(texts1)
        dgm2 = self.analyze_texts(texts2)
        
        # Compute Wasserstein distance between diagrams
        distances = {}
        for dim in range(3):
            arr1 = dgm1.to_array(dim)
            arr2 = dgm2.to_array(dim)
            
            if len(arr1) > 0 and len(arr2) > 0:
                distances[f"H{dim}_wasserstein"] = wasserstein(arr1, arr2)
                distances[f"H{dim}_bottleneck"] = bottleneck(arr1, arr2)
        
        return distances
```

---

## 4. Application to LLM Security

### 4.1 Anomaly Обнаружение via Topology

```python
class TopologicalAnomalyDetector:
    def __init__(self, embedding_model):
        self.embedding_model = embedding_model
        self.ph_computer = PersistentHomologyComputer()
        self.baseline_dgm = None
        self.baseline_features = None
    
    def fit(self, normal_texts: List[str]):
        """Learn normal topological structure"""
        embeddings = self.embedding_model.encode(normal_texts)
        self.baseline_dgm = self.ph_computer.compute(embeddings)
        self.baseline_features = self._extract_features(self.baseline_dgm)
    
    def detect(self, texts: List[str]) -> dict:
        """Detect topological anomalies"""
        embeddings = self.embedding_model.encode(texts)
        new_dgm = self.ph_computer.compute(embeddings)
        new_features = self._extract_features(new_dgm)
        
        # Compare with baseline
        anomaly_score = self._compute_anomaly_score(
            self.baseline_features, 
            new_features
        )
        
        return {
            "is_anomaly": anomaly_score > 0.5,
            "score": anomaly_score,
            "features": new_features
        }
    
    def _extract_features(self, dgm: PersistenceDiagram) -> dict:
        """Extract statistical features from persistence diagram"""
        features = {}
        
        for dim in range(3):
            intervals = dgm.get_by_dimension(dim)
            if intervals:
                persistences = [i.persistence for i in intervals 
                               if not np.isinf(i.persistence)]
                features[f"H{dim}_count"] = len(intervals)
                features[f"H{dim}_mean_persistence"] = np.mean(persistences) if persistences else 0
                features[f"H{dim}_max_persistence"] = max(persistences) if persistences else 0
                features[f"H{dim}_total_persistence"] = sum(persistences)
        
        return features
    
    def _compute_anomaly_score(self, baseline: dict, current: dict) -> float:
        """Compute anomaly score based on feature deviation"""
        score = 0.0
        count = 0
        
        for key in baseline:
            if key in current:
                diff = abs(baseline[key] - current[key])
                normalized = diff / (baseline[key] + 1e-6)
                score += min(normalized, 1.0)
                count += 1
        
        return score / count if count > 0 else 0.0
```

### 4.2 Injection Обнаружение via H₁ Features

```python
class H1InjectionDetector:
    """
    Hypothesis: Injection attacks create "holes" in embedding space
    by introducing semantically distant content that bridges
    normal conversation patterns.
    """
    
    def __init__(self, embedding_model):
        self.embedding_model = embedding_model
        self.ph_computer = PersistentHomologyComputer(max_dim=1)
        self.normal_h1_stats = None
    
    def fit(self, normal_conversations: List[List[str]]):
        """Learn H₁ characteristics of normal conversations"""
        h1_features = []
        
        for conv in normal_conversations:
            embeddings = self.embedding_model.encode(conv)
            dgm = self.ph_computer.compute(embeddings)
            h1 = dgm.get_by_dimension(1)
            
            if h1:
                max_persistence = max(i.persistence for i in h1)
                h1_features.append(max_persistence)
        
        self.normal_h1_stats = {
            "mean": np.mean(h1_features),
            "std": np.std(h1_features),
            "max": np.max(h1_features)
        }
    
    def detect_injection(self, conversation: List[str]) -> dict:
        """Detect injection attempt via H₁ anomaly"""
        embeddings = self.embedding_model.encode(conversation)
        dgm = self.ph_computer.compute(embeddings)
        h1 = dgm.get_by_dimension(1)
        
        if not h1:
            return {"is_injection": False, "score": 0.0}
        
        max_persistence = max(i.persistence for i in h1)
        
        # Z-score
        z_score = (max_persistence - self.normal_h1_stats["mean"]) / \
                  (self.normal_h1_stats["std"] + 1e-6)
        
        is_injection = z_score > 3.0  # 3 sigma rule
        
        return {
            "is_injection": is_injection,
            "score": min(z_score / 5.0, 1.0),
            "h1_max_persistence": max_persistence,
            "z_score": z_score
        }
```

---

## 5. SENTINEL Интеграция

```python
from sentinel import scan  # Public API
    TopologicalEngine,
    PersistenceComputer,
    EmbeddingAnalyzer
)

class SENTINELTopologicalAnalyzer:
    def __init__(self, config):
        self.embedding_model = config.embedding_model
        self.ph_computer = PersistentHomologyComputer(
            max_dim=config.max_homology_dim
        )
        self.baseline = None
    
    def train(self, normal_corpus: List[str]):
        """Train on normal data"""
        embeddings = self.embedding_model.encode(normal_corpus)
        self.baseline = self.ph_computer.compute(embeddings)
    
    def analyze(self, inputs: List[str]) -> dict:
        """Analyze for topological anomalies"""
        embeddings = self.embedding_model.encode(inputs)
        current_dgm = self.ph_computer.compute(embeddings)
        
        # Compare H₀ (clustering structure)
        h0_anomaly = self._analyze_h0(current_dgm)
        
        # Compare H₁ (loop structure)
        h1_anomaly = self._analyze_h1(current_dgm)
        
        return {
            "h0_anomaly": h0_anomaly,
            "h1_anomaly": h1_anomaly,
            "is_attack": h0_anomaly["score"] > 0.7 or h1_anomaly["score"] > 0.7,
            "diagram": current_dgm
        }
```

---

## 6. Summary

1. **Persistent Homology:** Track topological features across scales
2. **Features:** H₀ (clusters), H₁ (loops), H₂ (voids)
3. **Application:** Detect anomalies in embedding space
4. **Injection Обнаружение:** Unusual H₁ features indicate injection

---

## Next Lesson

→ [02. Mapper Algorithm](02-mapper-algorithm.md)

---

*AI Security Academy (RU) | Track 06: Mathematical Foundations | Module 06.1: TDA*
