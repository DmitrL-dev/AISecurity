# 🌀 Урок 2.3: Hyperbolic Geometry

> **Время: 45 минут** | Expert Module 2 — Strange Math™

---

## Introduction

**Hyperbolic space** naturally encodes hierarchical structures. Text has hierarchy (words → sentences → paragraphs).

---

## Poincaré Embeddings

```rust
use candle_core::Tensor;

struct PoincareBall;

struct HyperbolicEmbedder {
    manifold: PoincareBall,
    dim: usize,
}

impl HyperbolicEmbedder {
    fn new(dim: usize) -> Self {
        Self {
            manifold: PoincareBall,
            dim,
        }
    }

    /// Embed text in hyperbolic space.
    fn embed(&self, text: &str) -> Tensor {
        let euclidean = self.base_embed(text);
        let hyperbolic = self.manifold.expmap0(&euclidean);
        hyperbolic
    }

    /// Hyperbolic distance.
    fn distance(&self, x: &Tensor, y: &Tensor) -> f64 {
        self.manifold.dist(x, y)
    }
}
```

---

## Detection via Curvature

```rust
struct HyperbolicDetector {
    manifold: PoincareBall,
    threshold: f64,
}

impl HyperbolicDetector {
    /// Detect anomalies via hyperbolic geometry.

    fn scan(&self, text: &str) -> ScanResult {
        let chunks = self.split(text);
        let embeddings: Vec<_> = chunks.iter().map(|c| self.embed(c)).collect();

        // Normal text: embeddings form smooth path
        // Injection: sudden jumps in hyperbolic distance

        for i in 0..embeddings.len() - 1 {
            let dist = self.manifold.dist(&embeddings[i], &embeddings[i + 1]);
            if dist > self.threshold {
                return ScanResult { is_threat: true, ..Default::default() };
            }
        }

        ScanResult { is_threat: false, ..Default::default() }
    }
}
```

---

## Why Hyperbolic?

| Property | Euclidean | Hyperbolic |
|----------|-----------|------------|
| Hierarchy | Poor | Excellent |
| Distance scaling | Linear | Exponential |
| Boundary detection | Hard | Natural |

---

## Следующий урок

→ [2.4: Optimal Transport](./08-optimal-transport.md)
