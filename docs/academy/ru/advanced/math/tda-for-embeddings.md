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

```rust
use ndarray::{Array2, Axis};

/// Various metrics for embedding space
struct EmbeddingMetrics;

impl EmbeddingMetrics {
    /// Standard Euclidean distance
    fn euclidean_distance_matrix(embeddings: &Array2<f64>) -> Array2<f64> {
        let n = embeddings.nrows();
        let mut dist = Array2::<f64>::zeros((n, n));
        for i in 0..n {
            for j in (i + 1)..n {
                let d: f64 = embeddings.row(i).iter()
                    .zip(embeddings.row(j).iter())
                    .map(|(a, b)| (a - b).powi(2))
                    .sum::<f64>().sqrt();
                dist[[i, j]] = d;
                dist[[j, i]] = d;
            }
        }
        dist
    }

    /// Cosine distance — more suitable for embeddings,
    /// as directions matter, not magnitude.
    fn cosine_distance_matrix(embeddings: &Array2<f64>) -> Array2<f64> {
        let n = embeddings.nrows();
        let mut dist = Array2::<f64>::zeros((n, n));
        for i in 0..n {
            for j in (i + 1)..n {
                let dot: f64 = embeddings.row(i).iter()
                    .zip(embeddings.row(j).iter())
                    .map(|(a, b)| a * b).sum();
                let norm_i: f64 = embeddings.row(i).iter()
                    .map(|x| x.powi(2)).sum::<f64>().sqrt();
                let norm_j: f64 = embeddings.row(j).iter()
                    .map(|x| x.powi(2)).sum::<f64>().sqrt();
                let cos_sim = dot / (norm_i * norm_j + 1e-10);
                let d = 1.0 - cos_sim;
                dist[[i, j]] = d;
                dist[[j, i]] = d;
            }
        }
        dist
    }

    /// Euclidean metric after L2 normalization
    fn normalized_euclidean(embeddings: &Array2<f64>) -> Array2<f64> {
        let norms = embeddings.map_axis(Axis(1), |row| {
            row.iter().map(|x| x.powi(2)).sum::<f64>().sqrt()
        });
        let mut normalized = embeddings.clone();
        for (mut row, &norm) in normalized.rows_mut().into_iter()
            .zip(norms.iter()) {
            row.mapv_inplace(|x| x / (norm + 1e-10));
        }
        Self::euclidean_distance_matrix(&normalized)
    }

    /// Angular distance — arccos of cosine similarity.
    /// Metric (satisfies triangle inequality).
    fn angular_distance(embeddings: &Array2<f64>) -> Array2<f64> {
        let n = embeddings.nrows();
        let mut dist = Array2::<f64>::zeros((n, n));
        for i in 0..n {
            for j in (i + 1)..n {
                let dot: f64 = embeddings.row(i).iter()
                    .zip(embeddings.row(j).iter())
                    .map(|(a, b)| a * b).sum();
                let norm_i: f64 = embeddings.row(i).iter()
                    .map(|x| x.powi(2)).sum::<f64>().sqrt();
                let norm_j: f64 = embeddings.row(j).iter()
                    .map(|x| x.powi(2)).sum::<f64>().sqrt();
                let cos_sim = (dot / (norm_i * norm_j + 1e-10))
                    .clamp(-1.0, 1.0); // Numerical stability
                let d = cos_sim.acos() / std::f64::consts::PI; // Normalize to [0, 1]
                dist[[i, j]] = d;
                dist[[j, i]] = d;
            }
        }
        dist
    }
}
```

---

## 2. Persistence Homology for Embeddings

### 2.1 Vietoris-Rips Complex

```rust
use ndarray::Array2;
use std::collections::HashMap;
use plotters::prelude::*;

/// Persistent Homology for embedding space analysis.
/// Uses Vietoris-Rips filtration.
struct EmbeddingPersistence {
    /// Maximum homology dimension (0, 1, 2)
    max_dim: usize,
    /// Maximum edge length in filtration
    max_edge_length: f64,
    diagrams: Option<Vec<Vec<(f64, f64)>>>,
    distance_matrix: Option<Array2<f64>>,
}

impl EmbeddingPersistence {
    fn new(max_dim: usize, max_edge_length: f64) -> Self {
        Self {
            max_dim,
            max_edge_length,
            diagrams: None,
            distance_matrix: None,
        }
    }

    /// Computes persistent homology for embeddings.
    ///
    /// # Arguments
    /// * `embeddings` - Embedding matrix (n_samples, n_features)
    /// * `metric` - "euclidean", "cosine", or "angular"
    ///
    /// # Returns
    /// HashMap with diagrams and statistics
    fn compute(&mut self, embeddings: &Array2<f64>,
               metric: &str) -> Result<HashMap<String, serde_json::Value>, String> {
        // Compute distance matrix
        self.distance_matrix = Some(match metric {
            "euclidean" => EmbeddingMetrics::euclidean_distance_matrix(embeddings),
            "cosine" => EmbeddingMetrics::cosine_distance_matrix(embeddings),
            "angular" => EmbeddingMetrics::angular_distance(embeddings),
            _ => return Err(format!("Unknown metric: {}", metric)),
        });

        // Ripser for persistent homology
        let dist = self.distance_matrix.as_ref().unwrap();
        let result = ripser(dist, self.max_dim, self.max_edge_length, true);

        self.diagrams = Some(result.dgms.clone());
        let dgms = self.diagrams.as_ref().unwrap();

        let h1_features = if self.max_dim >= 1 { dgms[1].len() } else { 0 };

        let mut output = HashMap::new();
        output.insert("diagrams".into(), serde_json::json!(dgms));
        output.insert("h0_features".into(), serde_json::json!(dgms[0].len()));
        output.insert("h1_features".into(), serde_json::json!(h1_features));
        output.insert("statistics".into(), serde_json::json!(self.compute_statistics()));
        Ok(output)
    }

    /// Computes persistence diagram statistics
    fn compute_statistics(&self) -> HashMap<String, f64> {
        let mut stats = HashMap::new();
        let dgms = match &self.diagrams {
            Some(d) => d,
            None => return stats,
        };

        for (dim, dgm) in dgms.iter().enumerate() {
            if dgm.is_empty() { continue; }

            // Lifetime = death - birth
            let lifetimes: Vec<f64> = dgm.iter()
                .map(|(b, d)| d - b)
                .filter(|l| l.is_finite())
                .collect();

            if !lifetimes.is_empty() {
                let n = lifetimes.len() as f64;
                let sum: f64 = lifetimes.iter().sum();
                let mean = sum / n;
                let max = lifetimes.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
                let std = (lifetimes.iter().map(|l| (l - mean).powi(2)).sum::<f64>() / n).sqrt();

                stats.insert(format!("H{}_count", dim), dgm.len() as f64);
                stats.insert(format!("H{}_mean_lifetime", dim), mean);
                stats.insert(format!("H{}_max_lifetime", dim), max);
                stats.insert(format!("H{}_std_lifetime", dim), std);
                stats.insert(format!("H{}_total_persistence", dim), sum);
            }
        }
        stats
    }

    /// Returns only persistent features (with large lifetime).
    ///
    /// # Arguments
    /// * `min_persistence` - Minimum lifetime for feature
    fn get_persistent_features(&self, min_persistence: f64) -> HashMap<String, Vec<(f64, f64)>> {
        let mut persistent = HashMap::new();
        let dgms = match &self.diagrams {
            Some(d) => d,
            None => return persistent,
        };

        for (dim, dgm) in dgms.iter().enumerate() {
            let filtered: Vec<(f64, f64)> = dgm.iter()
                .filter(|(b, d)| {
                    let lifetime = d - b;
                    lifetime >= min_persistence && lifetime.is_finite()
                })
                .cloned()
                .collect();
            persistent.insert(format!("H{}", dim), filtered);
        }
        persistent
    }

    /// Visualize persistence diagrams
    fn plot(&self, save_path: Option<&str>) -> Result<(), Box<dyn std::error::Error>> {
        let dgms = self.diagrams.as_ref()
            .ok_or("Call compute() first")?;

        let n_plots = self.max_dim + 1;
        let path = save_path.unwrap_or("persistence.png");
        let root = BitMapBackend::new(path, (500 * n_plots as u32, 400))
            .into_drawing_area();
        root.fill(&WHITE)?;

        let areas = root.split_evenly((1, n_plots));

        for (i, area) in areas.iter().enumerate() {
            if i >= dgms.len() { break; }
            let max_val = dgms[i].iter()
                .map(|(_, d)| *d)
                .filter(|d| d.is_finite())
                .fold(1.0_f64, f64::max);

            let mut chart = ChartBuilder::on(area)
                .caption(format!("H{} Persistence Diagram", i), ("sans-serif", 18))
                .x_label_area_size(30).y_label_area_size(30)
                .build_cartesian_2d(0.0..max_val, 0.0..max_val)?;

            chart.configure_mesh().draw()?;
            chart.draw_series(dgms[i].iter()
                .filter(|(_, d)| d.is_finite())
                .map(|(b, d)| Circle::new((*b, *d), 3, BLUE.mix(0.6).filled())))?;
            chart.draw_series(LineSeries::new(
                vec![(0.0, 0.0), (max_val, max_val)],
                BLACK.mix(0.3),
            ))?;
        }
        root.present()?;
        Ok(())
    }
}
```

### 2.2 Comparing Persistence Diagrams

```rust
use std::collections::HashMap;

/// Comparison of persistence diagrams for detection.
/// Uses Wasserstein and Bottleneck distances.
struct PersistenceComparator {
    baseline_diagrams: Option<Vec<Vec<(f64, f64)>>>,
}

impl PersistenceComparator {
    fn new() -> Self {
        Self { baseline_diagrams: None }
    }

    /// Sets baseline diagrams
    fn set_baseline(&mut self, diagrams: Vec<Vec<(f64, f64)>>) {
        self.baseline_diagrams = Some(diagrams);
    }

    /// Compares target diagrams with baseline.
    ///
    /// # Arguments
    /// * `target_diagrams` - Diagrams to compare
    ///
    /// # Returns
    /// Distances by dimension
    fn compare(&self, target_diagrams: &[Vec<(f64, f64)>])
        -> Result<HashMap<String, f64>, String>
    {
        let baseline = self.baseline_diagrams.as_ref()
            .ok_or("Set baseline first")?;

        let mut results = HashMap::new();
        let n_dims = baseline.len().min(target_diagrams.len());

        for dim in 0..n_dims {
            let baseline_dgm = &baseline[dim];
            let target_dgm = &target_diagrams[dim];

            // Wasserstein distance (p=2)
            let w_dist = wasserstein_distance(baseline_dgm, target_dgm)
                .unwrap_or(f64::INFINITY);

            // Bottleneck distance
            let b_dist = bottleneck_distance(baseline_dgm, target_dgm)
                .unwrap_or(f64::INFINITY);

            results.insert(format!("H{}_wasserstein", dim), w_dist);
            results.insert(format!("H{}_bottleneck", dim), b_dist);
        }

        Ok(results)
    }

    /// Determines if target is anomalous.
    ///
    /// # Arguments
    /// * `target_diagrams` - Diagrams to check
    /// * `wasserstein_threshold` - Threshold for Wasserstein
    /// * `bottleneck_threshold` - Threshold for Bottleneck
    ///
    /// # Returns
    /// Anomaly detection result
    fn is_anomaly(&self, target_diagrams: &[Vec<(f64, f64)>],
                  wasserstein_threshold: f64,
                  bottleneck_threshold: f64)
        -> HashMap<String, serde_json::Value>
    {
        let distances = self.compare(target_diagrams).unwrap_or_default();

        let mut anomalies: Vec<HashMap<String, serde_json::Value>> = Vec::new();
        for (key, &value) in &distances {
            if key.contains("wasserstein") && value > wasserstein_threshold {
                let mut a = HashMap::new();
                a.insert("metric".into(), json!(key));
                a.insert("value".into(), json!(value));
                a.insert("threshold".into(), json!(wasserstein_threshold));
                anomalies.push(a);
            } else if key.contains("bottleneck") && value > bottleneck_threshold {
                let mut a = HashMap::new();
                a.insert("metric".into(), json!(key));
                a.insert("value".into(), json!(value));
                a.insert("threshold".into(), json!(bottleneck_threshold));
                anomalies.push(a);
            }
        }

        let mut result = HashMap::new();
        result.insert("is_anomaly".into(), json!(!anomalies.is_empty()));
        result.insert("distances".into(), json!(distances));
        result.insert("violations".into(), json!(anomalies));
        result
    }
}
```

---

## 3. Topological Signatures for Texts

### 3.1 Embedding Topology Signature

```rust
use std::collections::HashMap;
use md5;

/// Topological signature of text corpus.
/// Used for comparison and change detection.
struct TopologicalSignature {
    encoder: SentenceEncoder,
    persistence: EmbeddingPersistence,
}

impl TopologicalSignature {
    fn new(embedding_model: &str) -> Self {
        Self {
            encoder: SentenceEncoder::new(embedding_model),
            persistence: EmbeddingPersistence::new(1, f64::INFINITY),
        }
    }

    /// Computes topological signature for texts.
    ///
    /// # Arguments
    /// * `texts` - List of texts
    /// * `metric` - Metric for embeddings
    ///
    /// # Returns
    /// Topological signature
    fn compute_signature(&mut self, texts: &[&str],
                         metric: &str) -> HashMap<String, serde_json::Value> {
        // Embeddings
        let embeddings = self.encoder.encode(texts);

        // Persistent homology
        let result = self.persistence.compute(&embeddings, metric).unwrap();

        let stats = result.get("statistics").unwrap();

        // Extract key features
        let h0_count = stats.get("H0_count").and_then(|v| v.as_f64()).unwrap_or(0.0);
        let h0_mean = stats.get("H0_mean_lifetime").and_then(|v| v.as_f64()).unwrap_or(0.0);
        let h0_max = stats.get("H0_max_lifetime").and_then(|v| v.as_f64()).unwrap_or(0.0);
        let h1_count = stats.get("H1_count").and_then(|v| v.as_f64()).unwrap_or(0.0);
        let h1_mean = stats.get("H1_mean_lifetime").and_then(|v| v.as_f64()).unwrap_or(0.0);
        let h1_total = stats.get("H1_total_persistence").and_then(|v| v.as_f64()).unwrap_or(0.0);

        let mut signature = HashMap::new();
        signature.insert("n_texts".into(), json!(texts.len()));
        signature.insert("embedding_dim".into(), json!(embeddings.ncols()));
        signature.insert("metric".into(), json!(metric));

        // H0 features
        signature.insert("h0_count".into(), json!(h0_count));
        signature.insert("h0_mean_lifetime".into(), json!(h0_mean));
        signature.insert("h0_max_lifetime".into(), json!(h0_max));

        // H1 features
        signature.insert("h1_count".into(), json!(h1_count));
        signature.insert("h1_mean_lifetime".into(), json!(h1_mean));
        signature.insert("h1_total_persistence".into(), json!(h1_total));

        // Diagrams
        signature.insert("diagrams".into(), result["diagrams"].clone());

        // Signature hash
        let hash = Self::compute_hash(h0_count, h0_mean, h1_count, h1_mean);
        signature.insert("hash".into(), json!(hash));

        signature
    }

    /// Computes hash of signature for quick comparison
    fn compute_hash(h0_count: f64, h0_mean: f64,
                    h1_count: f64, h1_mean: f64) -> String {
        let key_values = format!("[{}, {:.3}, {}, {:.3}]",
            h0_count, h0_mean, h1_count, h1_mean);
        let digest = md5::compute(key_values.as_bytes());
        format!("{:x}", digest)[..16].to_string()
    }

    /// Compares two topological signatures.
    ///
    /// # Arguments
    /// * `sig1` - First signature
    /// * `sig2` - Second signature
    ///
    /// # Returns
    /// Comparison result
    fn compare_signatures(&self,
                          sig1: &HashMap<String, serde_json::Value>,
                          sig2: &HashMap<String, serde_json::Value>)
        -> HashMap<String, serde_json::Value>
    {
        // Compare basic statistics
        let keys = ["h0_count", "h0_mean_lifetime", "h1_count", "h1_mean_lifetime"];
        let mut stat_diffs = HashMap::new();
        for &key in &keys {
            let v1 = sig1.get(key).and_then(|v| v.as_f64()).unwrap_or(0.0);
            let v2 = sig2.get(key).and_then(|v| v.as_f64()).unwrap_or(0.0);
            let diff = v2 - v1;
            let rel_diff = diff / (v1 + 1e-10);
            stat_diffs.insert(key.to_string(), json!({
                "absolute": diff,
                "relative": rel_diff,
            }));
        }

        // Diagram distances
        let mut comparator = PersistenceComparator::new();
        let d1: Vec<Vec<(f64, f64)>> = serde_json::from_value(
            sig1["diagrams"].clone()).unwrap_or_default();
        let d2: Vec<Vec<(f64, f64)>> = serde_json::from_value(
            sig2["diagrams"].clone()).unwrap_or_default();
        comparator.set_baseline(d1);
        let diagram_dists = comparator.compare(&d2).unwrap_or_default();

        let is_similar = self.assess_similarity(&stat_diffs, &diagram_dists);

        let hash1 = sig1.get("hash").and_then(|v| v.as_str()).unwrap_or("");
        let hash2 = sig2.get("hash").and_then(|v| v.as_str()).unwrap_or("");

        let mut result = HashMap::new();
        result.insert("hash_match".into(), json!(hash1 == hash2));
        result.insert("statistic_differences".into(), json!(stat_diffs));
        result.insert("diagram_distances".into(), json!(diagram_dists));
        result.insert("is_similar".into(), json!(is_similar));
        result
    }

    /// Assesses overall signature similarity
    fn assess_similarity(&self,
                         stat_diffs: &HashMap<String, serde_json::Value>,
                         diagram_dists: &HashMap<String, f64>) -> bool {
        // Relative changes < 50%
        for (_key, diff) in stat_diffs {
            if let Some(rel) = diff.get("relative").and_then(|v| v.as_f64()) {
                if rel.abs() > 0.5 {
                    return false;
                }
            }
        }

        // Diagram distances reasonable
        for (key, &dist) in diagram_dists {
            if key.contains("wasserstein") && dist > 0.5 {
                return false;
            }
        }

        true
    }
}
```

### 3.2 Sliding Window TDA

```rust
use std::collections::HashMap;
use ndarray::Array2;

/// TDA analysis with sliding window for streaming data.
/// Tracks topology changes over time.
struct SlidingWindowTDA {
    window_size: usize,
    step_size: usize,
    encoder: SentenceEncoder,
    persistence: EmbeddingPersistence,
    history: Vec<HashMap<String, serde_json::Value>>,
    current_window: Vec<String>,
}

impl SlidingWindowTDA {
    fn new(window_size: usize, step_size: usize, embedding_model: &str) -> Self {
        Self {
            window_size,
            step_size,
            encoder: SentenceEncoder::new(embedding_model),
            persistence: EmbeddingPersistence::new(1, f64::INFINITY),
            history: Vec::new(),
            current_window: Vec::new(),
        }
    }

    /// Adds text and updates analysis.
    ///
    /// # Arguments
    /// * `text` - New text
    ///
    /// # Returns
    /// Window analysis result (if step_size reached)
    fn add_text(&mut self, text: &str) -> Option<HashMap<String, serde_json::Value>> {
        self.current_window.push(text.to_string());

        if self.current_window.len() >= self.window_size {
            // Analyze window
            let mut result = self.analyze_window();

            // Compare with previous
            if !self.history.is_empty() {
                let change = self.detect_change(&result);
                result.insert("change_detected".into(), json!(change));
            }

            self.history.push(result.clone());

            // Shift window
            self.current_window = self.current_window[self.step_size..].to_vec();

            return Some(result);
        }

        None
    }

    /// Analyzes current window
    fn analyze_window(&mut self) -> HashMap<String, serde_json::Value> {
        let refs: Vec<&str> = self.current_window.iter().map(|s| s.as_str()).collect();
        let embeddings = self.encoder.encode(&refs);
        let result = self.persistence.compute(&embeddings, "cosine").unwrap();

        let mut output = HashMap::new();
        output.insert("window_start".into(), json!(self.history.len() * self.step_size));
        output.insert("window_texts".into(), json!(self.current_window.len()));
        output.insert("statistics".into(), result["statistics"].clone());
        output.insert("diagrams".into(), result["diagrams"].clone());
        output
    }

    /// Detects changes relative to previous window
    fn detect_change(&self, current: &HashMap<String, serde_json::Value>)
        -> HashMap<String, serde_json::Value>
    {
        let prev = self.history.last().unwrap();

        let mut comparator = PersistenceComparator::new();
        let prev_dgms: Vec<Vec<(f64, f64)>> = serde_json::from_value(
            prev["diagrams"].clone()).unwrap_or_default();
        let cur_dgms: Vec<Vec<(f64, f64)>> = serde_json::from_value(
            current["diagrams"].clone()).unwrap_or_default();

        comparator.set_baseline(prev_dgms);
        let distances = comparator.compare(&cur_dgms).unwrap_or_default();

        // Check for anomaly
        let anomaly = comparator.is_anomaly(&cur_dgms, 0.3, 0.2);

        let mut result = HashMap::new();
        result.insert("distances".into(), json!(distances));
        result.insert("is_anomaly".into(), anomaly["is_anomaly"].clone());
        result.insert("violations".into(), anomaly["violations"].clone());
        result
    }

    /// Returns topology change trend
    fn get_trend(&self) -> HashMap<String, serde_json::Value> {
        if self.history.len() < 2 {
            let mut r = HashMap::new();
            r.insert("status".into(), json!("insufficient_data"));
            return r;
        }

        let h0_counts: Vec<f64> = self.history.iter()
            .map(|h| h.get("statistics")
                .and_then(|s| s.get("H0_count"))
                .and_then(|v| v.as_f64()).unwrap_or(0.0))
            .collect();
        let h1_counts: Vec<f64> = self.history.iter()
            .map(|h| h.get("statistics")
                .and_then(|s| s.get("H1_count"))
                .and_then(|v| v.as_f64()).unwrap_or(0.0))
            .collect();

        let n = h0_counts.len() as f64;
        let h0_var = variance(&h0_counts);
        let h1_var = variance(&h1_counts);

        let mut result = HashMap::new();
        result.insert("n_windows".into(), json!(self.history.len()));
        result.insert("h0_trend".into(), json!(linear_slope(&h0_counts)));
        result.insert("h1_trend".into(), json!(linear_slope(&h1_counts)));
        result.insert("h0_variance".into(), json!(h0_var));
        result.insert("h1_variance".into(), json!(h1_var));
        result
    }
}

fn variance(data: &[f64]) -> f64 {
    let n = data.len() as f64;
    let mean = data.iter().sum::<f64>() / n;
    data.iter().map(|x| (x - mean).powi(2)).sum::<f64>() / n
}

fn linear_slope(data: &[f64]) -> f64 {
    let n = data.len() as f64;
    let x_mean = (n - 1.0) / 2.0;
    let y_mean = data.iter().sum::<f64>() / n;
    let num: f64 = data.iter().enumerate()
        .map(|(i, y)| (i as f64 - x_mean) * (y - y_mean)).sum();
    let den: f64 = (0..data.len())
        .map(|i| (i as f64 - x_mean).powi(2)).sum();
    if den.abs() < 1e-10 { 0.0 } else { num / den }
}
```

---

## 4. Security Applications

### 4.1 Injection Обнаружение via TDA

```rust
use std::collections::HashMap;

/// Prompt injection detector based on TDA.
/// Uses topological changes in embedding space.
struct TDAInjectionDetector {
    encoder: SentenceEncoder,
    persistence: EmbeddingPersistence,
    comparator: PersistenceComparator,
    baseline_signature: Option<HashMap<String, serde_json::Value>>,
    thresholds: TDAThresholds,
}

struct TDAThresholds {
    wasserstein: f64,
    bottleneck: f64,
    h1_count_change: f64,
}

impl TDAInjectionDetector {
    fn new(embedding_model: &str) -> Self {
        Self {
            encoder: SentenceEncoder::new(embedding_model),
            persistence: EmbeddingPersistence::new(1, f64::INFINITY),
            comparator: PersistenceComparator::new(),
            baseline_signature: None,
            thresholds: TDAThresholds {
                wasserstein: 0.4,
                bottleneck: 0.25,
                h1_count_change: 3.0,
            },
        }
    }

    /// Training on normal data.
    /// Builds baseline topological signature.
    fn train(&mut self, normal_texts: &[&str]) {
        let embeddings = self.encoder.encode(normal_texts);
        let result = self.persistence.compute(&embeddings, "cosine").unwrap();

        let dgms: Vec<Vec<(f64, f64)>> = serde_json::from_value(
            result["diagrams"].clone()).unwrap_or_default();

        let mut sig = HashMap::new();
        sig.insert("diagrams".into(), result["diagrams"].clone());
        sig.insert("statistics".into(), result["statistics"].clone());
        sig.insert("n_samples".into(), json!(normal_texts.len()));
        self.baseline_signature = Some(sig);

        self.comparator.set_baseline(dgms);
    }

    /// Injection detection in texts.
    ///
    /// # Arguments
    /// * `texts` - Texts for analysis
    ///
    /// # Returns
    /// Обнаружение result
    fn detect(&mut self, texts: &[&str])
        -> Result<HashMap<String, serde_json::Value>, String>
    {
        let baseline = self.baseline_signature.as_ref()
            .ok_or("Train the detector first")?;

        // Compute embeddings and persistence
        let embeddings = self.encoder.encode(texts);
        let result = self.persistence.compute(&embeddings, "cosine")
            .map_err(|e| e.to_string())?;

        // Compare with baseline
        let cur_dgms: Vec<Vec<(f64, f64)>> = serde_json::from_value(
            result["diagrams"].clone()).unwrap_or_default();
        let anomaly_check = self.comparator.is_anomaly(
            &cur_dgms,
            self.thresholds.wasserstein,
            self.thresholds.bottleneck,
        );

        // Additional checks
        let h1_baseline = baseline.get("statistics")
            .and_then(|s| s.get("H1_count"))
            .and_then(|v| v.as_f64()).unwrap_or(0.0);
        let h1_current = result.get("statistics")
            .and_then(|s| s.get("H1_count"))
            .and_then(|v| v.as_f64()).unwrap_or(0.0);
        let h1_change = (h1_current - h1_baseline).abs();

        // Aggregate detection
        let is_anomaly = anomaly_check.get("is_anomaly")
            .and_then(|v| v.as_bool()).unwrap_or(false);
        let is_injection = is_anomaly || h1_change > self.thresholds.h1_count_change;

        // Confidence score
        let distances = anomaly_check.get("distances")
            .and_then(|v| serde_json::from_value::<HashMap<String, f64>>(v.clone()).ok())
            .unwrap_or_default();
        let confidence = self.compute_confidence(&distances, h1_change);

        let mut output = HashMap::new();
        output.insert("is_injection".into(), json!(is_injection));
        output.insert("confidence".into(), json!(confidence));
        output.insert("distances".into(), anomaly_check["distances"].clone());
        output.insert("violations".into(), anomaly_check["violations"].clone());
        output.insert("h1_change".into(), json!(h1_change));
        output.insert("current_statistics".into(), result["statistics"].clone());
        output.insert("recommendation".into(),
            json!(self.get_recommendation(is_injection, confidence)));
        Ok(output)
    }

    /// Computes confidence score
    fn compute_confidence(&self, distances: &HashMap<String, f64>,
                          h1_change: f64) -> f64 {
        let mut score = 0.0;

        // Wasserstein contribution
        let w_h0 = distances.get("H0_wasserstein").copied().unwrap_or(0.0);
        let w_h1 = distances.get("H1_wasserstein").copied().unwrap_or(0.0);
        score += (w_h0 / self.thresholds.wasserstein).min(1.0) * 0.3;
        score += (w_h1 / self.thresholds.wasserstein).min(1.0) * 0.3;

        // H1 change contribution
        score += (h1_change / self.thresholds.h1_count_change).min(1.0) * 0.4;

        score.min(1.0)
    }

    /// Recommendations based on result
    fn get_recommendation(&self, is_injection: bool, confidence: f64) -> String {
        if !is_injection {
            "SAFE: Topology matches baseline".into()
        } else if confidence < 0.5 {
            "LOW_RISK: Minor topological changes".into()
        } else if confidence < 0.8 {
            "MEDIUM_RISK: Significant changes, review recommended".into()
        } else {
            "HIGH_RISK: Strong topological anomalies, possible injection".into()
        }
    }
}
```

### 4.2 Multi-Modal TDA Обнаружение

```rust
use std::collections::HashMap;
use ndarray::{Array1, Array2, Axis};

/// Multi-modal detector combining TDA features with other methods.
struct MultiModalTDADetector {
    encoder: SentenceEncoder,
    tda_detector: TDAInjectionDetector,

    // Feature weights
    weight_tda: f64,
    weight_semantic: f64,
    weight_structural: f64,

    // Semantic baseline
    normal_centroid: Option<Array1<f64>>,
    normal_radius: f64,

    // Attack patterns (if provided)
    attack_embeddings: Option<Array2<f64>>,
}

impl MultiModalTDADetector {
    fn new(embedding_model: &str) -> Self {
        Self {
            encoder: SentenceEncoder::new(embedding_model),
            tda_detector: TDAInjectionDetector::new(embedding_model),
            weight_tda: 0.4,
            weight_semantic: 0.3,
            weight_structural: 0.3,
            normal_centroid: None,
            normal_radius: 0.0,
            attack_embeddings: None,
        }
    }

    /// Training on normal (and optionally attack) data.
    fn train(&mut self, normal_texts: &[&str], attack_texts: Option<&[&str]>) {
        self.tda_detector.train(normal_texts);

        // Semantic baseline
        let normal_emb = self.encoder.encode(normal_texts);
        let centroid = normal_emb.mean_axis(Axis(0)).unwrap();
        let mut max_dist: f64 = 0.0;
        for row in normal_emb.rows() {
            let dist: f64 = row.iter().zip(centroid.iter())
                .map(|(a, b)| (a - b).powi(2)).sum::<f64>().sqrt();
            if dist > max_dist { max_dist = dist; }
        }
        self.normal_centroid = Some(centroid);
        self.normal_radius = max_dist;

        // Attack patterns (if provided)
        if let Some(attacks) = attack_texts {
            self.attack_embeddings = Some(self.encoder.encode(attacks));
        }
    }

    /// Multi-modal detection.
    ///
    /// # Returns
    /// Combined detection result
    fn detect(&mut self, texts: &[&str]) -> HashMap<String, serde_json::Value> {
        let embeddings = self.encoder.encode(texts);

        // 1. TDA Обнаружение
        let tda_result = self.tda_detector.detect(texts).unwrap_or_default();
        let tda_score = tda_result.get("confidence")
            .and_then(|v| v.as_f64()).unwrap_or(0.0);

        // 2. Semantic Обнаружение (distance from centroid)
        let centroid = self.normal_centroid.as_ref().unwrap();
        let mut outside_count = 0usize;
        for row in embeddings.rows() {
            let dist: f64 = row.iter().zip(centroid.iter())
                .map(|(a, b)| (a - b).powi(2)).sum::<f64>().sqrt();
            if dist > self.normal_radius * 1.5 {
                outside_count += 1;
            }
        }
        let semantic_score = outside_count as f64 / embeddings.nrows() as f64;

        // 3. Structural Обнаружение (similarity to known attacks)
        let mut structural_score: f64 = 0.0;
        if let Some(ref attack_emb) = self.attack_embeddings {
            for emb_row in embeddings.rows() {
                let emb_norm: f64 = emb_row.iter()
                    .map(|x| x.powi(2)).sum::<f64>().sqrt();
                for atk_row in attack_emb.rows() {
                    let atk_norm: f64 = atk_row.iter()
                        .map(|x| x.powi(2)).sum::<f64>().sqrt();
                    let dot: f64 = emb_row.iter().zip(atk_row.iter())
                        .map(|(a, b)| a * b).sum();
                    let sim = dot / (emb_norm * atk_norm + 1e-10);
                    if sim > structural_score { structural_score = sim; }
                }
            }
        }

        // Combined score
        let combined_score =
            self.weight_tda * tda_score +
            self.weight_semantic * semantic_score +
            self.weight_structural * structural_score;

        let mut result = HashMap::new();
        result.insert("is_attack".into(), json!(combined_score > 0.5));
        result.insert("combined_score".into(), json!(combined_score));
        result.insert("scores".into(), json!({
            "tda": tda_score,
            "semantic": semantic_score,
            "structural": structural_score,
        }));
        result.insert("tda_details".into(), json!(tda_result));
        result.insert("recommendation".into(),
            json!(Self::get_recommendation(combined_score)));
        result
    }

    fn get_recommendation(score: f64) -> &'static str {
        if score < 0.3 {
            "SAFE"
        } else if score < 0.5 {
            "LOW_RISK: Monitor closely"
        } else if score < 0.7 {
            "MEDIUM_RISK: Review required"
        } else {
            "HIGH_RISK: Block and investigate"
        }
    }
}
```

---

## 5. SENTINEL Интеграция

```rust
use std::collections::HashMap;

#[derive(Clone, Debug)]
enum RiskLevel {
    Safe,
    Low,
    Medium,
    High,
    Critical,
}

impl RiskLevel {
    fn value(&self) -> &'static str {
        match self {
            RiskLevel::Safe => "safe",
            RiskLevel::Low => "low",
            RiskLevel::Medium => "medium",
            RiskLevel::High => "high",
            RiskLevel::Critical => "critical",
        }
    }
}

/// TDA Security Engine configuration
struct TDASecurityConfig {
    embedding_model: String,
    max_homology_dim: usize,
    wasserstein_threshold: f64,
    bottleneck_threshold: f64,
    metric: String,
    use_multimodal: bool,
}

impl Default for TDASecurityConfig {
    fn default() -> Self {
        Self {
            embedding_model: "all-MiniLM-L6-v2".into(),
            max_homology_dim: 1,
            wasserstein_threshold: 0.4,
            bottleneck_threshold: 0.25,
            metric: "cosine".into(),
            use_multimodal: true,
        }
    }
}

/// TDA Engine for SENTINEL framework.
/// Provides topological analysis for security detection.
struct SENTINELTDAEngine {
    config: TDASecurityConfig,
    multimodal_detector: Option<MultiModalTDADetector>,
    injection_detector: Option<TDAInjectionDetector>,
    signature_cache: HashMap<String, HashMap<String, serde_json::Value>>,
    is_trained: bool,
}

impl SENTINELTDAEngine {
    fn new(config: TDASecurityConfig) -> Self {
        let (mm, inj) = if config.use_multimodal {
            (Some(MultiModalTDADetector::new(&config.embedding_model)), None)
        } else {
            (None, Some(TDAInjectionDetector::new(&config.embedding_model)))
        };

        Self {
            config,
            multimodal_detector: mm,
            injection_detector: inj,
            signature_cache: HashMap::new(),
            is_trained: false,
        }
    }

    /// Train engine on data.
    ///
    /// # Arguments
    /// * `normal_texts` - Normal texts
    /// * `attack_texts` - Attack texts (optional)
    /// * `signature_name` - Signature name for caching
    fn train(&mut self, normal_texts: &[&str],
             attack_texts: Option<&[&str]>,
             signature_name: &str) {
        if let Some(ref mut det) = self.multimodal_detector {
            det.train(normal_texts, attack_texts);
        }
        if let Some(ref mut det) = self.injection_detector {
            det.train(normal_texts);
        }

        // Save signature
        let mut sig_computer = TopologicalSignature::new(&self.config.embedding_model);
        let sig = sig_computer.compute_signature(normal_texts, &self.config.metric);
        self.signature_cache.insert(signature_name.into(), sig);

        self.is_trained = true;
    }

    /// Analyze texts.
    ///
    /// # Returns
    /// Full analysis result
    fn analyze(&mut self, texts: &[&str])
        -> Result<HashMap<String, serde_json::Value>, String>
    {
        if !self.is_trained {
            return Err("Train the engine first".into());
        }

        let result = if let Some(ref mut det) = self.multimodal_detector {
            det.detect(texts)
        } else if let Some(ref mut det) = self.injection_detector {
            det.detect(texts).map_err(|e| e.to_string())?
        } else {
            return Err("No detector configured".into());
        };

        // Determine risk level
        let score = result.get("combined_score")
            .or_else(|| result.get("confidence"))
            .and_then(|v| v.as_f64()).unwrap_or(0.0);
        let risk_level = Self::determine_risk_level(score);

        let is_attack = result.get("is_attack")
            .or_else(|| result.get("is_injection"))
            .and_then(|v| v.as_bool()).unwrap_or(false);

        let mut output = HashMap::new();
        output.insert("risk_level".into(), json!(risk_level.value()));
        output.insert("is_attack".into(), json!(is_attack));
        output.insert("score".into(), json!(score));
        output.insert("details".into(), json!(result));
        output.insert("action".into(), json!(Self::get_action(&risk_level)));
        Ok(output)
    }

    fn determine_risk_level(score: f64) -> RiskLevel {
        if score < 0.2 { RiskLevel::Safe }
        else if score < 0.4 { RiskLevel::Low }
        else if score < 0.6 { RiskLevel::Medium }
        else if score < 0.8 { RiskLevel::High }
        else { RiskLevel::Critical }
    }

    fn get_action(risk_level: &RiskLevel) -> &'static str {
        match risk_level {
            RiskLevel::Safe => "ALLOW",
            RiskLevel::Low => "ALLOW_WITH_LOGGING",
            RiskLevel::Medium => "REQUIRE_REVIEW",
            RiskLevel::High => "BLOCK_PENDING_REVIEW",
            RiskLevel::Critical => "BLOCK_AND_ALERT",
        }
    }
}
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
