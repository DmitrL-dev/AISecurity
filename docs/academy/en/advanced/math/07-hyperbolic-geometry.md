# 🌀 Lesson 2.3: Hyperbolic Geometry

> **Time: 45 minutes** | Expert Module 2 — Strange Math™

---

## Introduction

**Hyperbolic space** naturally encodes hierarchical structures. Text has hierarchy (words → sentences → paragraphs).

---

## Poincaré Embeddings

```python
import torch
from geoopt import PoincareBall

manifold = PoincareBall()

class HyperbolicEmbedder:
    def __init__(self, dim=64):
        self.manifold = PoincareBall()
        self.dim = dim
    
    def embed(self, text: str) -> torch.Tensor:
        euclidean = self.base_embed(text)
        hyperbolic = self.manifold.expmap0(euclidean)
        return hyperbolic
    
    def distance(self, x, y):
        return self.manifold.dist(x, y)
```

---

## Detection via Curvature

```python
class HyperbolicDetector(BaseEngine):
    def scan(self, text: str) -> ScanResult:
        chunks = self.split(text)
        embeddings = [self.embed(c) for c in chunks]
        
        # Normal text: smooth path
        # Injection: sudden jumps
        for i in range(len(embeddings) - 1):
            dist = self.manifold.dist(embeddings[i], embeddings[i+1])
            if dist > self.threshold:
                return ScanResult(is_threat=True)
        
        return ScanResult(is_threat=False)
```

---

## Why Hyperbolic?

| Property | Euclidean | Hyperbolic |
|----------|-----------|------------|
| Hierarchy | Poor | Excellent |
| Distance scaling | Linear | Exponential |
| Boundary detection | Hard | Natural |

---

## Next Lesson

→ [2.4: Optimal Transport](./08-optimal-transport.md)
