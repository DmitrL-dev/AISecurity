# Persistent Homology for Attack Detection

> **Lesson:** 06.2.2 - Persistent Homology  
> **Time:** 45 minutes  
> **Prerequisites:** TDA Introduction

---

## Learning Objectives

By the end of this lesson, you will be able to:

1. Understand persistent homology fundamentals
2. Apply topological analysis to embedding spaces
3. Detect attacks via topological signatures
4. Implement persistence-based anomaly detection

---

## What is Persistent Homology?

Persistent homology tracks topological features (holes, voids) across multiple scales:

```
Scale 0: Individual points (0-dim holes = components)
Scale ε: Points connect at distance ε (1-dim holes = loops)
Scale ∞: All points connected (features vanish)

Persistence = how long a feature survives across scales
```

| Dimension | Feature | Security Application |
|-----------|---------|---------------------|
| H₀ | Connected components | Cluster structure |
| H₁ | Loops/cycles | Circular attack patterns |
| H₂ | Voids | Complex topological anomalies |

---

## Basic Implementation

```python
import numpy as np
from ripser import ripser
from scipy.spatial.distance import pdist, squareform

class PersistenceAnalyzer:
    """Persistent homology for security analysis."""
    
    def __init__(self, max_dimension: int = 1):
        self.max_dim = max_dimension
    
    def compute_persistence(self, points: np.ndarray) -> dict:
        """Compute persistence diagrams."""
        
        # Compute pairwise distances
        distances = squareform(pdist(points))
        
        # Compute persistent homology
        result = ripser(distances, maxdim=self.max_dim, distance_matrix=True)
        
        diagrams = {}
        for dim in range(self.max_dim + 1):
            dgm = result['dgms'][dim]
            diagrams[f"H{dim}"] = {
                "birth": dgm[:, 0].tolist(),
                "death": dgm[:, 1].tolist(),
                "persistence": (dgm[:, 1] - dgm[:, 0]).tolist()
            }
        
        return diagrams
    
    def extract_features(self, diagrams: dict) -> np.ndarray:
        """Extract statistical features from persistence diagrams."""
        
        features = []
        
        for dim_name, dgm in diagrams.items():
            persistence = np.array(dgm["persistence"])
            
            if len(persistence) == 0:
                features.extend([0, 0, 0, 0, 0])
            else:
                features.extend([
                    len(persistence),          # Number of features
                    np.mean(persistence),      # Mean persistence
                    np.max(persistence),       # Max persistence
                    np.std(persistence),       # Std of persistence
                    np.sum(persistence),       # Total persistence
                ])
        
        return np.array(features)
```

---

## Embedding Space Topology

```python
class EmbeddingTopologyAnalyzer:
    """Analyze topology of embedding space for security."""
    
    def __init__(self, embedding_model):
        self.embed = embedding_model
        self.persistence = PersistenceAnalyzer(max_dimension=1)
        
        # Baseline topology
        self.baseline_features = None
    
    def fit_baseline(self, normal_texts: list):
        """Establish baseline topology from normal inputs."""
        
        embeddings = np.array([self.embed(t) for t in normal_texts])
        
        diagrams = self.persistence.compute_persistence(embeddings)
        self.baseline_features = self.persistence.extract_features(diagrams)
    
    def detect_anomaly(self, texts: list, threshold: float = 2.0) -> dict:
        """Detect topological anomalies in input set."""
        
        if len(texts) < 5:
            return {"error": "Need at least 5 samples for topology"}
        
        embeddings = np.array([self.embed(t) for t in texts])
        
        diagrams = self.persistence.compute_persistence(embeddings)
        features = self.persistence.extract_features(diagrams)
        
        # Compare to baseline
        if self.baseline_features is not None:
            deviation = np.linalg.norm(features - self.baseline_features)
            baseline_norm = np.linalg.norm(self.baseline_features)
            relative_deviation = deviation / (baseline_norm + 1e-8)
        else:
            relative_deviation = 0.0
        
        return {
            "diagrams": diagrams,
            "features": features.tolist(),
            "deviation": float(relative_deviation),
            "is_anomalous": relative_deviation > threshold
        }
```

---

## Attack Signature Detection

```python
class TopologicalAttackDetector:
    """Detect attacks via topological signatures."""
    
    def __init__(self, embedding_model):
        self.embed = embedding_model
        self.persistence = PersistenceAnalyzer(max_dimension=1)
        
        # Known attack topological signatures
        self.attack_signatures = {}
    
    def learn_attack_signature(self, attack_type: str, examples: list):
        """Learn topological signature of attack type."""
        
        embeddings = np.array([self.embed(ex) for ex in examples])
        diagrams = self.persistence.compute_persistence(embeddings)
        features = self.persistence.extract_features(diagrams)
        
        # Also compute variance to understand signature spread
        if len(examples) > 10:
            # Bootstrap for variance estimation
            feature_samples = []
            for _ in range(10):
                indices = np.random.choice(len(examples), len(examples)//2)
                subset_emb = embeddings[indices]
                subset_dgm = self.persistence.compute_persistence(subset_emb)
                subset_feat = self.persistence.extract_features(subset_dgm)
                feature_samples.append(subset_feat)
            
            feature_std = np.std(feature_samples, axis=0)
        else:
            feature_std = np.ones_like(features)
        
        self.attack_signatures[attack_type] = {
            "mean": features,
            "std": feature_std
        }
    
    def detect(self, texts: list) -> dict:
        """Detect if texts match attack signature."""
        
        if len(texts) < 5:
            return {"error": "Need at least 5 samples"}
        
        embeddings = np.array([self.embed(t) for t in texts])
        diagrams = self.persistence.compute_persistence(embeddings)
        features = self.persistence.extract_features(diagrams)
        
        matches = []
        
        for attack_type, signature in self.attack_signatures.items():
            # Mahalanobis-like distance
            diff = features - signature["mean"]
            normalized_dist = np.sqrt(np.sum((diff / (signature["std"] + 1e-8))**2))
            
            # Lower distance = closer match
            match_score = 1 / (1 + normalized_dist)
            
            if match_score > 0.5:
                matches.append({
                    "attack_type": attack_type,
                    "match_score": float(match_score)
                })
        
        matches.sort(key=lambda x: -x["match_score"])
        
        return {
            "matches": matches,
            "top_match": matches[0] if matches else None,
            "is_attack": len(matches) > 0
        }
```

---

## Streaming Detection

```python
from collections import deque

class StreamingTopologyMonitor:
    """Monitor embedding topology in real-time."""
    
    def __init__(self, embedding_model, window_size: int = 50):
        self.embed = embedding_model
        self.persistence = PersistenceAnalyzer()
        self.window_size = window_size
        
        self.embedding_window = deque(maxlen=window_size)
        self.feature_history = deque(maxlen=100)
        
        self.baseline_mean = None
        self.baseline_std = None
    
    def add_sample(self, text: str) -> dict:
        """Add sample and check for topology changes."""
        
        embedding = self.embed(text)
        self.embedding_window.append(embedding)
        
        if len(self.embedding_window) < 10:
            return {"status": "warming_up"}
        
        # Compute current topology
        embeddings = np.array(list(self.embedding_window))
        diagrams = self.persistence.compute_persistence(embeddings)
        features = self.persistence.extract_features(diagrams)
        
        self.feature_history.append(features)
        
        # Update baseline (exponential moving average)
        if self.baseline_mean is None:
            self.baseline_mean = features
            self.baseline_std = np.ones_like(features)
        else:
            alpha = 0.1
            self.baseline_mean = alpha * features + (1 - alpha) * self.baseline_mean
            diff = features - self.baseline_mean
            self.baseline_std = alpha * np.abs(diff) + (1 - alpha) * self.baseline_std
        
        # Detect deviation
        z_score = np.abs(features - self.baseline_mean) / (self.baseline_std + 1e-8)
        max_z = np.max(z_score)
        
        return {
            "status": "normal" if max_z < 3.0 else "anomaly",
            "max_z_score": float(max_z),
            "current_features": features.tolist()
        }
```

---

## Visualization

```python
import matplotlib.pyplot as plt

def plot_persistence_diagram(diagrams: dict, title: str = "Persistence Diagram"):
    """Visualize persistence diagram."""
    
    fig, axes = plt.subplots(1, len(diagrams), figsize=(5*len(diagrams), 5))
    
    if len(diagrams) == 1:
        axes = [axes]
    
    for ax, (dim, dgm) in zip(axes, diagrams.items()):
        births = dgm["birth"]
        deaths = dgm["death"]
        
        # Plot points
        ax.scatter(births, deaths, alpha=0.6)
        
        # Diagonal line
        max_val = max(max(deaths), 1)
        ax.plot([0, max_val], [0, max_val], 'k--', alpha=0.3)
        
        ax.set_xlabel("Birth")
        ax.set_ylabel("Death")
        ax.set_title(f"{dim}")
    
    plt.suptitle(title)
    plt.tight_layout()
    return fig
```

---

## SENTINEL Integration

```python
from sentinel import configure, TopologyGuard

configure(
    topological_analysis=True,
    persistence_detection=True,
    streaming_topology=True
)

topology_guard = TopologyGuard(
    embedding_model="all-MiniLM-L6-v2",
    window_size=50,
    anomaly_threshold=3.0
)

@topology_guard.monitor
def process_batch(texts: list):
    # Topology monitored automatically
    return [llm.generate(t) for t in texts]
```

---

## Key Takeaways

1. **Topology captures structure** - Beyond point-wise analysis
2. **Persistence = importance** - Long-lived features matter
3. **Learn attack signatures** - Each attack type has topology
4. **Monitor in real-time** - Detect topology changes
5. **Combine with other methods** - Part of defense-in-depth

---

*AI Security Academy | Lesson 06.2.2*
