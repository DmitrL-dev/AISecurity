# 🔮 Lesson 2.1: Topological Data Analysis

> **Time: 50 minutes** | Expert Module 2 — Strange Math™

---

## Introduction

**Topological Data Analysis (TDA)** studies the "shape" of data. Normal text has consistent topology; injections create anomalies.

---

## Key Concepts

| Concept | Meaning | Detection Use |
|---------|---------|---------------|
| **Persistence** | Features that survive across scales | Stable patterns |
| **Betti Numbers** | Holes in different dimensions | Structural anomalies |
| **Simplicial Complex** | Network of relationships | Semantic consistency |

---

## Persistent Homology

```python
import gudhi
import numpy as np

def compute_persistence(embeddings: np.ndarray):
    """Compute persistence diagram from text embeddings."""
    rips = gudhi.RipsComplex(points=embeddings, max_edge_length=2.0)
    simplex_tree = rips.create_simplex_tree(max_dimension=2)
    persistence = simplex_tree.persistence()
    
    return persistence
```

---

## Injection Detection via TDA

```python
class TDADetector(BaseEngine):
    name = "tda_detector"
    tier = 3
    
    def scan(self, text: str) -> ScanResult:
        chunks = self.split_into_chunks(text)
        embeddings = np.array([self.embed(c) for c in chunks])
        
        persistence = compute_persistence(embeddings)
        anomaly_score = self.compute_anomaly(persistence)
        
        if anomaly_score > self.threshold:
            return ScanResult(is_threat=True, confidence=anomaly_score)
        return ScanResult(is_threat=False)
```

---

## Why TDA Works

Normal text: embeddings form smooth manifold (few holes)
Injection: sudden semantic shifts create "holes" in topology

---

## Next Lesson

→ [2.2: Sheaf Coherence](./06-sheaf-coherence.md)
