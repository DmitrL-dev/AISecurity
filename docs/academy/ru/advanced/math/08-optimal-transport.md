# 🚚 Урок 2.4: Optimal Transport

> **Время: 45 минут** | Expert Module 2 — Strange Math™

---

## Introduction

**Optimal Transport** measures the "cost" to transform one distribution into another. Used to detect if text has been "transported" from safe to malicious.

---

## Wasserstein Distance

```rust
use ndarray::Array1;

fn wasserstein_text_distance(text1: &str, text2: &str) -> f64 {
    /// Compute Wasserstein distance between texts.
    let emb1 = embed(text1);  // Distribution of embeddings
    let emb2 = embed(text2);

    wasserstein_distance(&emb1, &emb2)
}
```

---

## Detection via Transport Cost

```rust
struct OptimalTransportDetector {
    /// Detect injections via transport cost.
    safe_distribution: Array1<f64>,
    threshold: f64,
}

impl OptimalTransportDetector {
    fn new() -> Self {
        Self {
            safe_distribution: Self::load_safe_baseline(),
            threshold: 1.0,
        }
    }

    fn scan(&self, text: &str) -> ScanResult {
        let text_dist = self.extract_distribution(text);

        // Cost to transport text to "safe" baseline
        let transport_cost = self.wasserstein(&text_dist, &self.safe_distribution);

        if transport_cost > self.threshold {
            return ScanResult {
                is_threat: true,
                confidence: (transport_cost / 2.0).min(1.0),
                details: format!("Transport cost: {}", transport_cost),
                ..Default::default()
            };
        }

        ScanResult { is_threat: false, ..Default::default() }
    }
}
```

---

## Sinkhorn Algorithm

```rust
use ndarray::{Array1, Array2};

fn sinkhorn(cost_matrix: &Array2<f64>, reg: f64, num_iters: usize) -> Array2<f64> {
    /// Fast approximation of optimal transport.
    let k = cost_matrix.mapv(|x| (-x / reg).exp());

    let mut u = Array1::ones(k.nrows());
    let mut v = Array1::ones(k.ncols());

    for _ in 0..num_iters {
        u = 1.0 / &k.dot(&v);
        v = 1.0 / &k.t().dot(&u);
    }

    let u_diag = Array2::from_diag(&u);
    let v_diag = Array2::from_diag(&v);
    u_diag.dot(&k).dot(&v_diag)
}
```

---

## Следующий урок

→ [2.5: Chaos Theory](./09-chaos-theory.md)
