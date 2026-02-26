# 🌪️ Урок 2.5: Chaos Theory

> **Время: 45 минут** | Expert Module 2 — Strange Math™

---

## Introduction

**Chaos Theory** studies systems sensitive to initial conditions. Injections create "chaos" in otherwise stable text dynamics.

---

## Lyapunov Exponents

Measure how fast nearby trajectories diverge:

```rust
use ndarray::Array1;

fn lyapunov_exponent(sequence: &[f64]) -> f64 {
    /// Compute Lyapunov exponent of sequence.
    let n = sequence.len();
    let mut lyap = 0.0;

    for i in 0..n - 1 {
        let diff = (sequence[i + 1] - sequence[i]).abs();
        if diff > 0.0 {
            lyap += diff.ln();
        }
    }

    lyap / n as f64
}
```

---

## Detection via Stability

```rust
struct ChaosDetector {
    /// Detect injections via chaotic dynamics.
    chaos_threshold: f64,
}

impl ChaosDetector {
    fn scan(&self, text: &str) -> ScanResult {
        // Convert text to time series (embedding trajectory)
        let chunks = self.split_text(text);
        let embeddings: Vec<_> = chunks.iter().map(|c| self.embed(c)).collect();

        // Project to 1D for Lyapunov analysis
        let trajectory: Vec<f64> = embeddings.iter().map(|e| e.mean()).collect();

        // Compute Lyapunov exponent
        let lyap = lyapunov_exponent(&trajectory);

        // High positive Lyapunov = chaotic = injection
        if lyap > self.chaos_threshold {
            return ScanResult {
                is_threat: true,
                confidence: lyap.min(1.0),
                details: format!("Lyapunov exponent: {}", lyap),
                ..Default::default()
            };
        }

        ScanResult { is_threat: false, ..Default::default() }
    }
}
```

---

## Phase Space Reconstruction

```rust
use ndarray::Array2;

fn reconstruct_phase_space(series: &[f64], dim: usize, tau: usize) -> Array2<f64> {
    /// Takens embedding for phase space reconstruction.
    let n = series.len() - (dim - 1) * tau;
    let mut result = Array2::zeros((n, dim));
    for i in 0..n {
        for j in 0..dim {
            result[[i, j]] = series[i + j * tau];
        }
    }
    result
}
```

---

## Следующий урок

→ [3.1: Adversarial ML](./10-adversarial-ml.md)
