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

```rust
use std::collections::{HashMap, HashSet};

/// Representation of simplicial complex
struct SimplicialComplex {
    simplices: HashMap<usize, HashSet<Vec<usize>>>,  // dimension -> list of simplices
}

impl SimplicialComplex {
    fn new() -> Self {
        Self { simplices: HashMap::new() }
    }

    /// Add 0-simplex (vertex)
    fn add_vertex(&mut self, vertex_id: usize) {
        self.simplices.entry(0).or_insert_with(HashSet::new)
            .insert(vec![vertex_id]);
    }

    /// Add 1-simplex (edge)
    fn add_edge(&mut self, v1: usize, v2: usize) {
        let mut edge = vec![v1, v2];
        edge.sort();
        self.simplices.entry(1).or_insert_with(HashSet::new)
            .insert(edge);
    }

    /// Add 2-simplex (triangle)
    fn add_triangle(&mut self, v1: usize, v2: usize, v3: usize) {
        let mut tri = vec![v1, v2, v3];
        tri.sort();
        self.simplices.entry(2).or_insert_with(HashSet::new)
            .insert(tri);
    }

    /// Compute boundary of simplex
    fn boundary(&self, simplex: &[usize]) -> Vec<Vec<usize>> {
        if simplex.len() == 1 {
            return vec![];
        }
        (0..simplex.len())
            .map(|i| {
                let mut face = simplex.to_vec();
                face.remove(i);
                face
            })
            .collect()
    }
}
```

### 2.2 Vietoris-Rips Complex

```rust
use ndarray::Array2;

/// Build Vietoris-Rips complex from point cloud
struct VietorisRipsComplex {
    points: Array2<f64>,
    max_dim: usize,
    distances: Array2<f64>,
}

impl VietorisRipsComplex {
    fn new(points: Array2<f64>, max_dim: usize) -> Self {
        let distances = pairwise_distances(&points);
        Self { points, max_dim, distances }
    }

    /// Build complex at scale epsilon
    fn build_complex(&self, epsilon: f64) -> SimplicialComplex {
        let n = self.points.nrows();
        let mut complex = SimplicialComplex::new();

        // Add vertices
        for i in 0..n {
            complex.add_vertex(i);
        }

        // Add edges
        for i in 0..n {
            for j in (i + 1)..n {
                if self.distances[[i, j]] <= epsilon {
                    complex.add_edge(i, j);
                }
            }
        }

        // Add triangles (if max_dim >= 2)
        if self.max_dim >= 2 {
            for i in 0..n {
                for j in (i + 1)..n {
                    for k in (j + 1)..n {
                        if self.distances[[i, j]] <= epsilon
                            && self.distances[[j, k]] <= epsilon
                            && self.distances[[i, k]] <= epsilon
                        {
                            complex.add_triangle(i, j, k);
                        }
                    }
                }
            }
        }

        complex
    }

    /// Build filtration (sequence of complexes)
    fn filtration(&self, epsilons: &[f64]) -> Vec<SimplicialComplex> {
        epsilons.iter().map(|&eps| self.build_complex(eps)).collect()
    }
}
```

### 2.3 Persistence Diagram

```rust
struct PersistenceInterval {
    dimension: usize,  // H₀, H₁, H₂
    birth: f64,
    death: f64,  // f64::INFINITY for features that never die
}

impl PersistenceInterval {
    fn persistence(&self) -> f64 {
        self.death - self.birth
    }
}

struct PersistenceDiagram {
    intervals: Vec<PersistenceInterval>,
}

impl PersistenceDiagram {
    fn new(intervals: Vec<PersistenceInterval>) -> Self {
        Self { intervals }
    }

    fn get_by_dimension(&self, dim: usize) -> Vec<&PersistenceInterval> {
        self.intervals.iter().filter(|i| i.dimension == dim).collect()
    }

    /// Count features alive at threshold
    fn betti_number(&self, dim: usize, threshold: f64) -> usize {
        self.intervals.iter()
            .filter(|i| i.dimension == dim && i.birth <= threshold && threshold < i.death)
            .count()
    }

    /// Convert to (birth, death) array for dim
    fn to_array(&self, dim: usize) -> Vec<[f64; 2]> {
        self.get_by_dimension(dim)
            .iter()
            .map(|i| [i.birth, i.death])
            .collect()
    }
}
```

---

## 3. Computing Persistent Homology

### 3.1 Using Ripser (Fast Реализация)

```rust
use ndarray::Array2;

struct PersistentHomologyComputer {
    max_dim: usize,
    max_epsilon: f64,
}

impl PersistentHomologyComputer {
    fn new(max_dim: usize, max_epsilon: f64) -> Self {
        Self { max_dim, max_epsilon }
    }

    /// Compute persistent homology using Ripser
    fn compute(&self, points: &Array2<f64>) -> PersistenceDiagram {
        let result = ripser::compute(
            points,
            self.max_dim,
            self.max_epsilon,
        );

        let mut intervals = Vec::new();
        for (dim, dgm) in result.dgms.iter().enumerate() {
            for &(birth, death) in dgm.iter() {
                intervals.push(PersistenceInterval {
                    dimension: dim,
                    birth,
                    death: if death.is_finite() { death } else { f64::INFINITY },
                });
            }
        }

        PersistenceDiagram::new(intervals)
    }

    /// Compute from precomputed distances
    fn distance_matrix_persistence(&self, dist_matrix: &Array2<f64>) -> PersistenceDiagram {
        let result = ripser::compute_from_distance_matrix(
            dist_matrix,
            self.max_dim,
            self.max_epsilon,
        );

        let mut intervals = Vec::new();
        for (dim, dgm) in result.dgms.iter().enumerate() {
            for &(birth, death) in dgm.iter() {
                intervals.push(PersistenceInterval {
                    dimension: dim,
                    birth,
                    death: if death.is_finite() { death } else { f64::INFINITY },
                });
            }
        }

        PersistenceDiagram::new(intervals)
    }
}
```

### 3.2 Embedding Space Analysis

```rust
struct EmbeddingPersistence {
    encoder: SentenceTransformer,
    ph_computer: PersistentHomologyComputer,
}

impl EmbeddingPersistence {
    fn new(embedding_model: &str) -> Self {
        Self {
            encoder: SentenceTransformer::new(embedding_model),
            ph_computer: PersistentHomologyComputer::new(2, 2.0),
        }
    }

    /// Analyze topological structure of text embeddings
    fn analyze_texts(&self, texts: &[String]) -> PersistenceDiagram {
        let embeddings = self.encoder.encode(texts);
        self.ph_computer.compute(&embeddings)
    }

    /// Compare topological structure of two text sets
    fn compare_distributions(&self, texts1: &[String], texts2: &[String]) -> HashMap<String, f64> {
        let dgm1 = self.analyze_texts(texts1);
        let dgm2 = self.analyze_texts(texts2);

        // Compute Wasserstein distance between diagrams
        let mut distances = HashMap::new();
        for dim in 0..3 {
            let arr1 = dgm1.to_array(dim);
            let arr2 = dgm2.to_array(dim);

            if !arr1.is_empty() && !arr2.is_empty() {
                distances.insert(format!("H{}_wasserstein", dim), wasserstein(&arr1, &arr2));
                distances.insert(format!("H{}_bottleneck", dim), bottleneck(&arr1, &arr2));
            }
        }

        distances
    }
}
```

---

## 4. Application to LLM Security

### 4.1 Anomaly Обнаружение via Topology

```rust
use std::collections::HashMap;

struct TopologicalAnomalyDetector {
    embedding_model: SentenceTransformer,
    ph_computer: PersistentHomologyComputer,
    baseline_dgm: Option<PersistenceDiagram>,
    baseline_features: Option<HashMap<String, f64>>,
}

impl TopologicalAnomalyDetector {
    fn new(embedding_model: SentenceTransformer) -> Self {
        Self {
            embedding_model,
            ph_computer: PersistentHomologyComputer::new(2, 2.0),
            baseline_dgm: None,
            baseline_features: None,
        }
    }

    /// Learn normal topological structure
    fn fit(&mut self, normal_texts: &[String]) {
        let embeddings = self.embedding_model.encode(normal_texts);
        let dgm = self.ph_computer.compute(&embeddings);
        self.baseline_features = Some(self.extract_features(&dgm));
        self.baseline_dgm = Some(dgm);
    }

    /// Detect topological anomalies
    fn detect(&self, texts: &[String]) -> HashMap<String, serde_json::Value> {
        let embeddings = self.embedding_model.encode(texts);
        let new_dgm = self.ph_computer.compute(&embeddings);
        let new_features = self.extract_features(&new_dgm);

        // Compare with baseline
        let anomaly_score = self.compute_anomaly_score(
            self.baseline_features.as_ref().unwrap(),
            &new_features,
        );

        let mut result = HashMap::new();
        result.insert("is_anomaly".into(), json!(anomaly_score > 0.5));
        result.insert("score".into(), json!(anomaly_score));
        result.insert("features".into(), json!(new_features));
        result
    }

    /// Extract statistical features from persistence diagram
    fn extract_features(&self, dgm: &PersistenceDiagram) -> HashMap<String, f64> {
        let mut features = HashMap::new();

        for dim in 0..3 {
            let intervals = dgm.get_by_dimension(dim);
            if !intervals.is_empty() {
                let persistences: Vec<f64> = intervals.iter()
                    .map(|i| i.persistence())
                    .filter(|p| p.is_finite())
                    .collect();
                features.insert(format!("H{}_count", dim), intervals.len() as f64);
                if !persistences.is_empty() {
                    let mean = persistences.iter().sum::<f64>() / persistences.len() as f64;
                    let max = persistences.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
                    let total: f64 = persistences.iter().sum();
                    features.insert(format!("H{}_mean_persistence", dim), mean);
                    features.insert(format!("H{}_max_persistence", dim), max);
                    features.insert(format!("H{}_total_persistence", dim), total);
                }
            }
        }

        features
    }

    /// Compute anomaly score based on feature deviation
    fn compute_anomaly_score(&self, baseline: &HashMap<String, f64>, current: &HashMap<String, f64>) -> f64 {
        let mut score = 0.0;
        let mut count = 0;

        for (key, &val) in baseline.iter() {
            if let Some(&cur) = current.get(key) {
                let diff = (val - cur).abs();
                let normalized = diff / (val + 1e-6);
                score += normalized.min(1.0);
                count += 1;
            }
        }

        if count > 0 { score / count as f64 } else { 0.0 }
    }
}
```

### 4.2 Injection Обнаружение via H₁ Features

```rust
/// Hypothesis: Injection attacks create "holes" in embedding space
/// by introducing semantically distant content that bridges
/// normal conversation patterns.
struct H1InjectionDetector {
    embedding_model: SentenceTransformer,
    ph_computer: PersistentHomologyComputer,
    normal_h1_stats: Option<H1Stats>,
}

struct H1Stats {
    mean: f64,
    std: f64,
    max: f64,
}

impl H1InjectionDetector {
    fn new(embedding_model: SentenceTransformer) -> Self {
        Self {
            embedding_model,
            ph_computer: PersistentHomologyComputer::new(1, 2.0),
            normal_h1_stats: None,
        }
    }

    /// Learn H₁ characteristics of normal conversations
    fn fit(&mut self, normal_conversations: &[Vec<String>]) {
        let mut h1_features = Vec::new();

        for conv in normal_conversations.iter() {
            let embeddings = self.embedding_model.encode(conv);
            let dgm = self.ph_computer.compute(&embeddings);
            let h1 = dgm.get_by_dimension(1);

            if !h1.is_empty() {
                let max_persistence = h1.iter()
                    .map(|i| i.persistence())
                    .fold(f64::NEG_INFINITY, f64::max);
                h1_features.push(max_persistence);
            }
        }

        let mean = h1_features.iter().sum::<f64>() / h1_features.len() as f64;
        let std = (h1_features.iter().map(|v| (v - mean).powi(2)).sum::<f64>()
            / h1_features.len() as f64).sqrt();
        let max = h1_features.iter().cloned().fold(f64::NEG_INFINITY, f64::max);

        self.normal_h1_stats = Some(H1Stats { mean, std, max });
    }

    /// Detect injection attempt via H₁ anomaly
    fn detect_injection(&self, conversation: &[String]) -> HashMap<String, serde_json::Value> {
        let embeddings = self.embedding_model.encode(conversation);
        let dgm = self.ph_computer.compute(&embeddings);
        let h1 = dgm.get_by_dimension(1);

        if h1.is_empty() {
            let mut r = HashMap::new();
            r.insert("is_injection".into(), json!(false));
            r.insert("score".into(), json!(0.0));
            return r;
        }

        let max_persistence = h1.iter()
            .map(|i| i.persistence())
            .fold(f64::NEG_INFINITY, f64::max);

        let stats = self.normal_h1_stats.as_ref().unwrap();
        // Z-score
        let z_score = (max_persistence - stats.mean) / (stats.std + 1e-6);
        let is_injection = z_score > 3.0;  // 3 sigma rule

        let mut result = HashMap::new();
        result.insert("is_injection".into(), json!(is_injection));
        result.insert("score".into(), json!((z_score / 5.0).min(1.0)));
        result.insert("h1_max_persistence".into(), json!(max_persistence));
        result.insert("z_score".into(), json!(z_score));
        result
    }
}
```

---

## 5. SENTINEL Интеграция

```rust
use sentinel_core::engines::{TopologicalEngine, PersistenceComputer, EmbeddingAnalyzer};

struct SENTINELTopologicalAnalyzer {
    embedding_model: SentenceTransformer,
    ph_computer: PersistentHomologyComputer,
    baseline: Option<PersistenceDiagram>,
}

impl SENTINELTopologicalAnalyzer {
    fn new(config: &Config) -> Self {
        Self {
            embedding_model: config.embedding_model.clone(),
            ph_computer: PersistentHomologyComputer::new(config.max_homology_dim, 2.0),
            baseline: None,
        }
    }

    /// Train on normal data
    fn train(&mut self, normal_corpus: &[String]) {
        let embeddings = self.embedding_model.encode(normal_corpus);
        self.baseline = Some(self.ph_computer.compute(&embeddings));
    }

    /// Analyze for topological anomalies
    fn analyze(&self, inputs: &[String]) -> HashMap<String, serde_json::Value> {
        let embeddings = self.embedding_model.encode(inputs);
        let current_dgm = self.ph_computer.compute(&embeddings);

        // Compare H₀ (clustering structure)
        let h0_anomaly = self.analyze_h0(&current_dgm);

        // Compare H₁ (loop structure)
        let h1_anomaly = self.analyze_h1(&current_dgm);

        let mut result = HashMap::new();
        result.insert("h0_anomaly".into(), json!(h0_anomaly));
        result.insert("h1_anomaly".into(), json!(h1_anomaly));
        result.insert("is_attack".into(), json!(
            h0_anomaly["score"].as_f64().unwrap() > 0.7
            || h1_anomaly["score"].as_f64().unwrap() > 0.7
        ));
        result
    }
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
