# 🛡️ Урок 3.2: Robustness

> **Время: 45 минут** | Expert Module 3

---

## Certified Defenses

Provable robustness guarantees:

```rust
struct CertifiedDefense {
    model: Box<dyn Model>,
}

impl CertifiedDefense {
    /// Certify that prediction is stable within radius.
    fn certify(&self, x: &Tensor, radius: f64) -> bool {
        let base_pred = self.model.forward(x);

        // Sample perturbations
        let samples: Vec<Tensor> = self.sample_noise(radius)
            .iter()
            .map(|noise| x.add(noise).unwrap())
            .collect();
        let preds: Vec<Tensor> = samples.iter()
            .map(|s| self.model.forward(s))
            .collect();

        // Check all match
        preds.iter().all(|p| p == &base_pred)
    }
}
```

---

## Randomized Smoothing

```rust
use std::collections::HashMap;
use rand::distributions::{Distribution, Normal};

fn smooth_classify(
    model: &dyn Model,
    x: &Tensor,
    sigma: f64,
    n_samples: usize,
) -> usize {
    /// Smoothed classifier via noise injection.
    let mut predictions = Vec::new();
    let normal = Normal::new(0.0, sigma).unwrap();
    let mut rng = rand::thread_rng();

    for _ in 0..n_samples {
        let noise: Vec<f64> = (0..x.elem_count())
            .map(|_| normal.sample(&mut rng))
            .collect();
        let noisy_x = x.add(&Tensor::from_vec(noise, x.shape())).unwrap();
        let pred = model.forward(&noisy_x);
        predictions.push(pred);
    }

    // Majority vote
    let mut counts: HashMap<usize, usize> = HashMap::new();
    for p in &predictions {
        *counts.entry(*p).or_insert(0) += 1;
    }
    *counts.iter().max_by_key(|(_, v)| *v).unwrap().0
}
```

---

## SENTINEL Robustness

```rust
use sentinel_core::engines::{BaseEngine, ScanResult};

struct RobustEngine {
    preprocessors: Vec<Box<dyn Fn(&str) -> String>>,
}

impl RobustEngine {
    fn scan(&self, text: &str) -> ScanResult {
        // Multi-representation voting
        let mut results = Vec::new();

        for preprocessor in &self.preprocessors {
            let processed = preprocessor(text);
            let result = self.base_scan(&processed);
            results.push(result);
        }

        // Conservative: threat if ANY detects
        let is_threat = results.iter().any(|r| r.is_threat);
        let confidence = results.iter()
            .map(|r| r.confidence)
            .fold(0.0_f64, f64::max);

        ScanResult { is_threat, confidence }
    }
}
```

---

## Следующий урок

→ [3.3: Interpretability](./12-interpretability.md)
