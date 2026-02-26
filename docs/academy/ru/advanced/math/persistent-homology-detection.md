# Persistent Homology for Attack Обнаружение

> **Урок:** 06.2.2 - Persistent Homology  
> **Время:** 45 минут  
> **Пререквизиты:** TDA Введение

---

## Цели обучения

К концу этого урока, you will be able to:

1. Understand persistent homology fundamentals
2. Apply topological analysis to embedding spaces
3. Detect attacks via topological signatures
4. Implement persistence-based anomaly detection

---

## Что такое Persistent Homology?

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

## Basic Реализация

```rust
use ndarray::{Array1, Array2};
use std::collections::HashMap;

/// Persistent homology for security analysis.
struct PersistenceAnalyzer {
    max_dim: usize,
}

impl PersistenceAnalyzer {
    fn new(max_dimension: usize) -> Self {
        Self { max_dim: max_dimension }
    }

    /// Compute persistence diagrams.
    fn compute_persistence(&self, points: &Array2<f64>) -> HashMap<String, PersistenceDgm> {
        // Compute pairwise distances
        let distances = pairwise_distances(points);

        // Compute persistent homology
        let result = ripser(&distances, self.max_dim, true);

        let mut diagrams = HashMap::new();
        for dim in 0..=self.max_dim {
            let dgm = &result.dgms[dim];
            let birth: Vec<f64> = dgm.iter().map(|p| p.0).collect();
            let death: Vec<f64> = dgm.iter().map(|p| p.1).collect();
            let persistence: Vec<f64> = dgm.iter().map(|p| p.1 - p.0).collect();
            diagrams.insert(
                format!("H{}", dim),
                PersistenceDgm { birth, death, persistence },
            );
        }

        diagrams
    }

    /// Extract statistical features from persistence diagrams.
    fn extract_features(&self, diagrams: &HashMap<String, PersistenceDgm>) -> Vec<f64> {
        let mut features = Vec::new();

        for (_dim_name, dgm) in diagrams.iter() {
            let persistence = &dgm.persistence;

            if persistence.is_empty() {
                features.extend_from_slice(&[0.0, 0.0, 0.0, 0.0, 0.0]);
            } else {
                let n = persistence.len() as f64;
                let mean = persistence.iter().sum::<f64>() / n;
                let max = persistence.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
                let sum: f64 = persistence.iter().sum();
                let std = (persistence.iter().map(|p| (p - mean).powi(2)).sum::<f64>() / n).sqrt();
                features.extend_from_slice(&[n, mean, max, std, sum]);
            }
        }

        features
    }
}
```

---

## Embedding Space Topology

```rust
use ndarray::Array2;
use std::collections::HashMap;

/// Analyze topology of embedding space for security.
struct EmbeddingTopologyAnalyzer {
    embed: Box<dyn Fn(&str) -> Vec<f64>>,
    persistence: PersistenceAnalyzer,
    baseline_features: Option<Vec<f64>>,
}

impl EmbeddingTopologyAnalyzer {
    fn new(embedding_model: Box<dyn Fn(&str) -> Vec<f64>>) -> Self {
        Self {
            embed: embedding_model,
            persistence: PersistenceAnalyzer::new(1),
            baseline_features: None,
        }
    }

    /// Establish baseline topology from normal inputs.
    fn fit_baseline(&mut self, normal_texts: &[&str]) {
        let vecs: Vec<Vec<f64>> = normal_texts.iter()
            .map(|t| (self.embed)(t)).collect();
        let embeddings = vecs_to_array2(&vecs);

        let diagrams = self.persistence.compute_persistence(&embeddings);
        self.baseline_features = Some(self.persistence.extract_features(&diagrams));
    }

    /// Detect topological anomalies in input set.
    fn detect_anomaly(&self, texts: &[&str], threshold: f64) -> HashMap<String, f64> {
        let mut result = HashMap::new();

        if texts.len() < 5 {
            result.insert("error".into(), f64::NAN);
            return result;
        }

        let vecs: Vec<Vec<f64>> = texts.iter()
            .map(|t| (self.embed)(t)).collect();
        let embeddings = vecs_to_array2(&vecs);

        let diagrams = self.persistence.compute_persistence(&embeddings);
        let features = self.persistence.extract_features(&diagrams);

        // Compare to baseline
        let relative_deviation = if let Some(ref baseline) = self.baseline_features {
            let deviation: f64 = features.iter().zip(baseline.iter())
                .map(|(a, b)| (a - b).powi(2)).sum::<f64>().sqrt();
            let baseline_norm: f64 = baseline.iter()
                .map(|x| x.powi(2)).sum::<f64>().sqrt();
            deviation / (baseline_norm + 1e-8)
        } else {
            0.0
        };

        result.insert("deviation".into(), relative_deviation);
        result.insert("is_anomalous".into(), if relative_deviation > threshold { 1.0 } else { 0.0 });
        result
    }
}
```

---

## Attack Signature Обнаружение

```rust
use std::collections::HashMap;

/// Detect attacks via topological signatures.
struct TopologicalAttackDetector {
    embed: Box<dyn Fn(&str) -> Vec<f64>>,
    persistence: PersistenceAnalyzer,
    attack_signatures: HashMap<String, AttackSignature>,
}

struct AttackSignature {
    mean: Vec<f64>,
    std: Vec<f64>,
}

impl TopologicalAttackDetector {
    fn new(embedding_model: Box<dyn Fn(&str) -> Vec<f64>>) -> Self {
        Self {
            embed: embedding_model,
            persistence: PersistenceAnalyzer::new(1),
            attack_signatures: HashMap::new(),
        }
    }

    /// Learn topological signature of attack type.
    fn learn_attack_signature(&mut self, attack_type: &str, examples: &[&str]) {
        let vecs: Vec<Vec<f64>> = examples.iter()
            .map(|ex| (self.embed)(ex)).collect();
        let embeddings = vecs_to_array2(&vecs);
        let diagrams = self.persistence.compute_persistence(&embeddings);
        let features = self.persistence.extract_features(&diagrams);

        // Bootstrap for variance estimation
        let feature_std = if examples.len() > 10 {
            let mut feature_samples: Vec<Vec<f64>> = Vec::new();
            let mut rng = rand::thread_rng();
            for _ in 0..10 {
                let half = examples.len() / 2;
                let indices: Vec<usize> = (0..half)
                    .map(|_| rng.gen_range(0..examples.len())).collect();
                let subset: Vec<Vec<f64>> = indices.iter()
                    .map(|&i| vecs[i].clone()).collect();
                let subset_emb = vecs_to_array2(&subset);
                let subset_dgm = self.persistence.compute_persistence(&subset_emb);
                feature_samples.push(self.persistence.extract_features(&subset_dgm));
            }
            compute_std_across(&feature_samples)
        } else {
            vec![1.0; features.len()]
        };

        self.attack_signatures.insert(attack_type.to_string(), AttackSignature {
            mean: features,
            std: feature_std,
        });
    }

    /// Detect if texts match attack signature.
    fn detect(&self, texts: &[&str]) -> DetectionResult {
        if texts.len() < 5 {
            return DetectionResult { matches: vec![], top_match: None, is_attack: false };
        }

        let vecs: Vec<Vec<f64>> = texts.iter()
            .map(|t| (self.embed)(t)).collect();
        let embeddings = vecs_to_array2(&vecs);
        let diagrams = self.persistence.compute_persistence(&embeddings);
        let features = self.persistence.extract_features(&diagrams);

        let mut matches: Vec<AttackMatch> = Vec::new();

        for (attack_type, signature) in &self.attack_signatures {
            // Mahalanobis-like distance
            let normalized_dist: f64 = features.iter()
                .zip(signature.mean.iter())
                .zip(signature.std.iter())
                .map(|((f, m), s)| ((f - m) / (s + 1e-8)).powi(2))
                .sum::<f64>().sqrt();

            // Lower distance = closer match
            let match_score = 1.0 / (1.0 + normalized_dist);

            if match_score > 0.5 {
                matches.push(AttackMatch {
                    attack_type: attack_type.clone(),
                    match_score,
                });
            }
        }

        matches.sort_by(|a, b| b.match_score.partial_cmp(&a.match_score).unwrap());

        let top_match = matches.first().cloned();
        DetectionResult { is_attack: !matches.is_empty(), matches, top_match }
    }
}
```

---

## Streaming Обнаружение

```rust
use std::collections::VecDeque;

/// Monitor embedding topology in real-time.
struct StreamingTopologyMonitor {
    embed: Box<dyn Fn(&str) -> Vec<f64>>,
    persistence: PersistenceAnalyzer,
    window_size: usize,
    embedding_window: VecDeque<Vec<f64>>,
    feature_history: VecDeque<Vec<f64>>,
    baseline_mean: Option<Vec<f64>>,
    baseline_std: Option<Vec<f64>>,
}

impl StreamingTopologyMonitor {
    fn new(embedding_model: Box<dyn Fn(&str) -> Vec<f64>>, window_size: usize) -> Self {
        Self {
            embed: embedding_model,
            persistence: PersistenceAnalyzer::new(1),
            window_size,
            embedding_window: VecDeque::with_capacity(window_size),
            feature_history: VecDeque::with_capacity(100),
            baseline_mean: None,
            baseline_std: None,
        }
    }

    /// Add sample and check for topology changes.
    fn add_sample(&mut self, text: &str) -> HashMap<String, serde_json::Value> {
        let embedding = (self.embed)(text);
        if self.embedding_window.len() >= self.window_size {
            self.embedding_window.pop_front();
        }
        self.embedding_window.push_back(embedding);

        if self.embedding_window.len() < 10 {
            let mut r = HashMap::new();
            r.insert("status".into(), json!("warming_up"));
            return r;
        }

        // Compute current topology
        let vecs: Vec<Vec<f64>> = self.embedding_window.iter().cloned().collect();
        let embeddings = vecs_to_array2(&vecs);
        let diagrams = self.persistence.compute_persistence(&embeddings);
        let features = self.persistence.extract_features(&diagrams);

        if self.feature_history.len() >= 100 {
            self.feature_history.pop_front();
        }
        self.feature_history.push_back(features.clone());

        // Update baseline (exponential moving average)
        let alpha = 0.1;
        match (&mut self.baseline_mean, &mut self.baseline_std) {
            (Some(mean), Some(std)) => {
                for i in 0..features.len() {
                    mean[i] = alpha * features[i] + (1.0 - alpha) * mean[i];
                    let diff = (features[i] - mean[i]).abs();
                    std[i] = alpha * diff + (1.0 - alpha) * std[i];
                }
            }
            _ => {
                self.baseline_mean = Some(features.clone());
                self.baseline_std = Some(vec![1.0; features.len()]);
            }
        }

        // Detect deviation
        let mean = self.baseline_mean.as_ref().unwrap();
        let std = self.baseline_std.as_ref().unwrap();
        let max_z: f64 = features.iter().zip(mean.iter()).zip(std.iter())
            .map(|((f, m), s)| (f - m).abs() / (s + 1e-8))
            .fold(f64::NEG_INFINITY, f64::max);

        let mut result = HashMap::new();
        result.insert("status".into(), json!(if max_z < 3.0 { "normal" } else { "anomaly" }));
        result.insert("max_z_score".into(), json!(max_z));
        result
    }
}
```

---

## Visualization

```rust
use plotters::prelude::*;

/// Visualize persistence diagram.
fn plot_persistence_diagram(
    diagrams: &HashMap<String, PersistenceDgm>,
    title: &str,
    output_path: &str,
) -> Result<(), Box<dyn std::error::Error>> {
    let n_dims = diagrams.len();
    let root = BitMapBackend::new(output_path, (500 * n_dims as u32, 500))
        .into_drawing_area();
    root.fill(&WHITE)?;

    let areas = root.split_evenly((1, n_dims));

    for (area, (dim, dgm)) in areas.iter().zip(diagrams.iter()) {
        let max_val = dgm.death.iter().cloned()
            .fold(1.0_f64, f64::max);

        let mut chart = ChartBuilder::on(area)
            .caption(dim, ("sans-serif", 20))
            .x_label_area_size(30)
            .y_label_area_size(30)
            .build_cartesian_2d(0.0..max_val, 0.0..max_val)?;

        chart.configure_mesh()
            .x_desc("Birth")
            .y_desc("Death")
            .draw()?;

        // Plot points
        chart.draw_series(
            dgm.birth.iter().zip(dgm.death.iter())
                .map(|(&b, &d)| Circle::new((b, d), 3, BLUE.mix(0.6).filled()))
        )?;

        // Diagonal line
        chart.draw_series(LineSeries::new(
            vec![(0.0, 0.0), (max_val, max_val)],
            BLACK.mix(0.3).stroke_width(1),
        ))?;
    }

    root.present()?;
    println!("{}", title);
    Ok(())
}
```

---

## SENTINEL Интеграция

```rust
use sentinel_core::config::configure;
use sentinel_core::guards::TopologyGuard;

fn main() {
    configure(|cfg| {
        cfg.topological_analysis(true)
           .persistence_detection(true)
           .streaming_topology(true);
    });

    let topology_guard = TopologyGuard::builder()
        .embedding_model("all-MiniLM-L6-v2")
        .window_size(50)
        .anomaly_threshold(3.0)
        .build();

    // Topology monitored automatically
    let results = topology_guard.monitor(|texts: &[&str]| {
        texts.iter().map(|t| llm.generate(t)).collect::<Vec<_>>()
    });
}
```

---

## Ключевые выводы

1. **Topology captures structure** - Beyond point-wise analysis
2. **Persistence = importance** - Long-lived features matter
3. **Learn attack signatures** - Each attack type has topology
4. **Monitor in real-time** - Detect topology changes
5. **Combine with other methods** - Part of defense-in-depth

---

*AI Security Academy (RU) | Lesson 06.2.2*
