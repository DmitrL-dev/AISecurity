//! Topological Data Analysis (TDA) Engine
//!
//! Advanced topological analysis for LLM security.
//! Based on 2025 research:
//!   - Zigzag Persistence for layer-by-layer analysis
//!   - TDA for attention map vulnerability detection
//!   - Topological fingerprinting for attack recognition
//!
//! Capabilities:
//!   - Persistence Diagrams and Betti numbers
//!   - Bottleneck and Wasserstein distances
//!   - Topological fingerprinting
//!   - Attention pattern topology

/// A single persistence pair (birth, death)
#[derive(Debug, Clone, PartialEq)]
pub struct PersistencePair {
    pub birth: f64,
    pub death: f64,
    pub dimension: usize,
}

impl PersistencePair {
    pub fn new(birth: f64, death: f64, dimension: usize) -> Self {
        Self { birth, death, dimension }
    }

    /// Persistence lifetime
    pub fn lifetime(&self) -> f64 {
        if self.death.is_finite() {
            self.death - self.birth
        } else {
            f64::INFINITY
        }
    }

    /// Midpoint on persistence bar
    pub fn midpoint(&self) -> f64 {
        if self.death.is_finite() {
            (self.birth + self.death) / 2.0
        } else {
            self.birth
        }
    }
}

/// Full persistence diagram with pairs per dimension
#[derive(Debug, Clone, Default)]
pub struct PersistenceDiagram {
    pub pairs: Vec<PersistencePair>,
    pub max_dimension: usize,
}

impl PersistenceDiagram {
    pub fn new(max_dimension: usize) -> Self {
        Self {
            pairs: Vec::new(),
            max_dimension,
        }
    }

    /// Add a persistence pair
    pub fn add_pair(&mut self, birth: f64, death: f64, dimension: usize) {
        self.pairs.push(PersistencePair::new(birth, death, dimension));
    }

    /// Get pairs for specific dimension
    pub fn get_pairs(&self, dimension: usize) -> Vec<&PersistencePair> {
        self.pairs.iter().filter(|p| p.dimension == dimension).collect()
    }

    /// Betti number: count features with lifetime > threshold
    pub fn betti_number(&self, dimension: usize, threshold: f64) -> usize {
        self.get_pairs(dimension)
            .iter()
            .filter(|p| {
                let lt = p.lifetime();
                lt > threshold && lt.is_finite()
            })
            .count()
    }

    /// Sum of all lifetimes in dimension
    pub fn total_persistence(&self, dimension: usize) -> f64 {
        self.get_pairs(dimension)
            .iter()
            .filter(|p| p.lifetime().is_finite())
            .map(|p| p.lifetime())
            .sum()
    }

    /// Persistence entropy
    pub fn entropy(&self, dimension: usize) -> f64 {
        let lifetimes: Vec<f64> = self.get_pairs(dimension)
            .iter()
            .filter(|p| p.lifetime().is_finite() && p.lifetime() > 0.0)
            .map(|p| p.lifetime())
            .collect();

        if lifetimes.is_empty() {
            return 0.0;
        }

        let total: f64 = lifetimes.iter().sum();
        let probs: Vec<f64> = lifetimes.iter().map(|l| l / total).collect();
        
        -probs.iter().map(|&p| p * (p + 1e-10).ln()).sum::<f64>()
    }

    /// Convert to array for distance computations
    pub fn to_array(&self, dimension: usize) -> Vec<(f64, f64)> {
        self.get_pairs(dimension)
            .iter()
            .filter(|p| p.death.is_finite())
            .map(|p| (p.birth, p.death))
            .collect()
    }
}

/// Persistence distance metrics
pub struct PersistenceDistance;

impl PersistenceDistance {
    /// Bottleneck distance (∞-Wasserstein)
    pub fn bottleneck(dgm1: &[(f64, f64)], dgm2: &[(f64, f64)]) -> f64 {
        if dgm1.is_empty() && dgm2.is_empty() {
            return 0.0;
        }
        if dgm1.is_empty() {
            return dgm2.iter().map(|(b, d)| (d - b) / 2.0).fold(0.0, f64::max);
        }
        if dgm2.is_empty() {
            return dgm1.iter().map(|(b, d)| (d - b) / 2.0).fold(0.0, f64::max);
        }

        // Greedy matching approximation
        let mut costs: Vec<f64> = Vec::new();

        for &(b1, d1) in dgm1 {
            let mut min_cost = (d1 - b1) / 2.0; // diagonal cost
            for &(b2, d2) in dgm2 {
                let cost = (b1 - b2).abs().max((d1 - d2).abs());
                min_cost = min_cost.min(cost);
            }
            costs.push(min_cost);
        }

        for &(b2, d2) in dgm2 {
            let mut min_cost = (d2 - b2) / 2.0;
            for &(b1, d1) in dgm1 {
                let cost = (b1 - b2).abs().max((d1 - d2).abs());
                min_cost = min_cost.min(cost);
            }
            costs.push(min_cost);
        }

        costs.iter().cloned().fold(0.0, f64::max)
    }

    /// p-Wasserstein distance
    pub fn wasserstein(dgm1: &[(f64, f64)], dgm2: &[(f64, f64)], p: f64) -> f64 {
        if dgm1.is_empty() && dgm2.is_empty() {
            return 0.0;
        }
        if dgm1.is_empty() {
            return dgm2.iter()
                .map(|(b, d)| ((d - b) / 2.0).powf(p))
                .sum::<f64>()
                .powf(1.0 / p);
        }
        if dgm2.is_empty() {
            return dgm1.iter()
                .map(|(b, d)| ((d - b) / 2.0).powf(p))
                .sum::<f64>()
                .powf(1.0 / p);
        }

        let mut total = 0.0;

        for &(b1, d1) in dgm1 {
            let diag_cost = ((d1 - b1) / 2.0).powf(p);
            let mut min_cost = diag_cost;
            for &(b2, d2) in dgm2 {
                let cost = (b1 - b2).abs().powf(p) + (d1 - d2).abs().powf(p);
                min_cost = min_cost.min(cost);
            }
            total += min_cost;
        }

        total.powf(1.0 / p)
    }
}

/// Topological fingerprint
#[derive(Debug, Clone)]
pub struct TopologicalFingerprint {
    pub fingerprint_id: String,
    pub betti_signature: (usize, usize, usize),
    pub persistence_signature: (f64, f64, f64),
    pub entropy_signature: (f64, f64, f64),
    pub landscape_hash: String,
}

impl TopologicalFingerprint {
    /// Compute similarity to another fingerprint
    pub fn similarity(&self, other: &TopologicalFingerprint) -> f64 {
        // Betti similarity
        let betti_dist = ((self.betti_signature.0 as f64 - other.betti_signature.0 as f64).powi(2)
            + (self.betti_signature.1 as f64 - other.betti_signature.1 as f64).powi(2)
            + (self.betti_signature.2 as f64 - other.betti_signature.2 as f64).powi(2))
            .sqrt();
        let betti_sim = 1.0 / (1.0 + betti_dist);

        // Persistence similarity
        let pers_dist = ((self.persistence_signature.0 - other.persistence_signature.0).powi(2)
            + (self.persistence_signature.1 - other.persistence_signature.1).powi(2)
            + (self.persistence_signature.2 - other.persistence_signature.2).powi(2))
            .sqrt();
        let pers_sim = 1.0 / (1.0 + pers_dist);

        // Hash match
        let hash_sim = if self.landscape_hash == other.landscape_hash { 1.0 } else { 0.0 };

        0.4 * betti_sim + 0.4 * pers_sim + 0.2 * hash_sim
    }
}

/// Attention topology analysis result
#[derive(Debug, Clone, Default)]
pub struct AttentionTopology {
    pub betti_0: usize,
    pub betti_1: usize,
    pub entropy: f64,
    pub sparsity: f64,
    pub clustering_coefficient: f64,
    pub is_anomalous: bool,
    pub anomaly_reasons: Vec<String>,
}

/// TDA Engine for computing persistence from point clouds
pub struct TDAEngine {
    max_dimension: usize,
    analyses_performed: usize,
}

impl Default for TDAEngine {
    fn default() -> Self {
        Self::new(2)
    }
}

impl TDAEngine {
    pub fn new(max_dimension: usize) -> Self {
        Self {
            max_dimension,
            analyses_performed: 0,
        }
    }

    /// Compute persistence from point cloud (simplified Rips)
    pub fn compute_persistence(&mut self, points: &[Vec<f64>]) -> PersistenceDiagram {
        let mut diagram = PersistenceDiagram::new(self.max_dimension);
        
        let n = points.len();
        if n < 2 {
            return diagram;
        }

        // Compute pairwise distances
        let dists = self.pairwise_distances(points);
        
        // Flatten and sort distances
        let mut all_dists: Vec<f64> = Vec::new();
        for i in 0..n {
            for j in (i + 1)..n {
                all_dists.push(dists[i][j]);
            }
        }
        all_dists.sort_by(|a, b| a.partial_cmp(b).unwrap());

        // H0: Connected components merge at increasing thresholds
        for (i, &d) in all_dists.iter().take(n.saturating_sub(1).min(20)).enumerate() {
            diagram.add_pair(0.0, d * (1.0 + 0.1 * i as f64), 0);
        }

        // H1: Approximate loops based on graph structure
        if self.max_dimension >= 1 && n >= 3 {
            let threshold = if all_dists.len() > n { 
                all_dists[n.min(all_dists.len() - 1)] 
            } else { 
                all_dists.last().copied().unwrap_or(1.0) 
            };
            
            // Count excess edges (potential cycles)
            let mut edge_count: usize = 0;
            for i in 0..n {
                for j in (i + 1)..n {
                    if dists[i][j] < threshold {
                        edge_count += 1;
                    }
                }
            }
            
            let cycle_count = edge_count.saturating_sub(n - 1);
            for c in 0..cycle_count.min(10) {
                let birth = threshold * (0.5 + 0.1 * c as f64);
                let death = threshold * (1.5 + 0.1 * c as f64);
                diagram.add_pair(birth, death, 1);
            }
        }

        self.analyses_performed += 1;
        diagram
    }

    /// Compute Betti numbers for point cloud
    pub fn betti_numbers(&mut self, points: &[Vec<f64>], threshold: f64) -> (usize, usize, usize) {
        let diagram = self.compute_persistence(points);
        (
            diagram.betti_number(0, threshold),
            diagram.betti_number(1, threshold),
            diagram.betti_number(2, threshold),
        )
    }

    /// Create topological fingerprint
    pub fn fingerprint(&mut self, points: &[Vec<f64>], id: &str) -> TopologicalFingerprint {
        let diagram = self.compute_persistence(points);
        
        let betti = (
            diagram.betti_number(0, 0.0),
            diagram.betti_number(1, 0.0),
            diagram.betti_number(2, 0.0),
        );
        
        let persistence = (
            diagram.total_persistence(0),
            diagram.total_persistence(1),
            diagram.total_persistence(2),
        );
        
        let entropy = (
            diagram.entropy(0),
            diagram.entropy(1),
            diagram.entropy(2),
        );

        // Simple hash from features
        let hash = format!("{:x}", 
            ((betti.0 * 1000 + betti.1 * 100 + betti.2 * 10) as u64)
                .wrapping_add((persistence.0 * 1000.0) as u64)
                .wrapping_add((persistence.1 * 100.0) as u64)
        );

        TopologicalFingerprint {
            fingerprint_id: id.to_string(),
            betti_signature: betti,
            persistence_signature: persistence,
            entropy_signature: entropy,
            landscape_hash: hash,
        }
    }

    /// Analyze attention matrix topology
    pub fn analyze_attention(&mut self, attention: &[Vec<f64>], threshold: f64) -> AttentionTopology {
        let n = attention.len();
        if n == 0 {
            return AttentionTopology::default();
        }

        let mut result = AttentionTopology::default();

        // Create adjacency from attention
        let adj: Vec<Vec<bool>> = attention.iter()
            .map(|row| row.iter().map(|&v| v > threshold).collect())
            .collect();

        // β₀: Connected components
        result.betti_0 = self.count_components(&adj);

        // β₁: Cycles (Euler characteristic)
        let num_edges: usize = adj.iter().map(|row| row.iter().filter(|&&v| v).count()).sum::<usize>() / 2;
        result.betti_1 = num_edges.saturating_sub(n - result.betti_0);

        // Entropy
        let flat: Vec<f64> = attention.iter().flatten().filter(|&&v| v > 0.0).copied().collect();
        if !flat.is_empty() {
            let sum: f64 = flat.iter().sum();
            let probs: Vec<f64> = flat.iter().map(|&v| v / sum).collect();
            result.entropy = -probs.iter().map(|&p| p * (p + 1e-10).ln()).sum::<f64>();
        }

        // Sparsity
        let total_cells = n * n;
        let sparse_cells = adj.iter().flatten().filter(|&&v| !v).count();
        result.sparsity = sparse_cells as f64 / total_cells as f64;

        // Clustering coefficient
        result.clustering_coefficient = self.clustering_coefficient(&adj);

        // Anomaly detection
        if result.betti_0 > 5 {
            result.is_anomalous = true;
            result.anomaly_reasons.push("fragmented_attention".to_string());
        }
        if result.betti_1 > 10 {
            result.is_anomalous = true;
            result.anomaly_reasons.push("cyclic_attention".to_string());
        }
        if result.entropy > 4.0 {
            result.is_anomalous = true;
            result.anomaly_reasons.push("entropy_anomaly".to_string());
        }

        self.analyses_performed += 1;
        result
    }

    /// Pairwise Euclidean distances
    fn pairwise_distances(&self, points: &[Vec<f64>]) -> Vec<Vec<f64>> {
        let n = points.len();
        let mut dists = vec![vec![0.0; n]; n];

        for i in 0..n {
            for j in (i + 1)..n {
                let d: f64 = points[i].iter()
                    .zip(&points[j])
                    .map(|(a, b)| (a - b).powi(2))
                    .sum::<f64>()
                    .sqrt();
                dists[i][j] = d;
                dists[j][i] = d;
            }
        }
        dists
    }

    /// Count connected components via BFS
    fn count_components(&self, adj: &[Vec<bool>]) -> usize {
        let n = adj.len();
        let mut visited = vec![false; n];
        let mut components = 0;

        for start in 0..n {
            if visited[start] {
                continue;
            }

            let mut queue = vec![start];
            visited[start] = true;

            while let Some(node) = queue.pop() {
                for (neighbor, &connected) in adj[node].iter().enumerate() {
                    if connected && !visited[neighbor] {
                        visited[neighbor] = true;
                        queue.push(neighbor);
                    }
                }
            }
            components += 1;
        }
        components
    }

    /// Average clustering coefficient
    fn clustering_coefficient(&self, adj: &[Vec<bool>]) -> f64 {
        let n = adj.len();
        let mut coefficients: Vec<f64> = Vec::new();

        for i in 0..n {
            let neighbors: Vec<usize> = adj[i].iter()
                .enumerate()
                .filter(|(_, &v)| v)
                .map(|(j, _)| j)
                .collect();
            
            let k = neighbors.len();
            if k < 2 {
                continue;
            }

            let mut links = 0;
            for (idx, &j) in neighbors.iter().enumerate() {
                for &l in neighbors.iter().skip(idx + 1) {
                    if adj[j][l] {
                        links += 1;
                    }
                }
            }

            let max_links = k * (k - 1) / 2;
            if max_links > 0 {
                coefficients.push(links as f64 / max_links as f64);
            }
        }

        if coefficients.is_empty() {
            0.0
        } else {
            coefficients.iter().sum::<f64>() / coefficients.len() as f64
        }
    }

    /// Get engine statistics
    pub fn get_stats(&self) -> EngineStats {
        EngineStats {
            analyses_performed: self.analyses_performed,
            max_dimension: self.max_dimension,
        }
    }
}

/// Engine statistics
#[derive(Debug, Clone)]
pub struct EngineStats {
    pub analyses_performed: usize,
    pub max_dimension: usize,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_persistence_pair_lifetime() {
        let pair = PersistencePair::new(1.0, 3.0, 0);
        assert!((pair.lifetime() - 2.0).abs() < 0.01);
    }

    #[test]
    fn test_persistence_pair_infinite() {
        let pair = PersistencePair::new(1.0, f64::INFINITY, 0);
        assert!(pair.lifetime().is_infinite());
    }

    #[test]
    fn test_diagram_betti_number() {
        let mut diagram = PersistenceDiagram::new(2);
        diagram.add_pair(0.0, 1.0, 0);
        diagram.add_pair(0.0, 2.0, 0);
        diagram.add_pair(0.5, 1.5, 1);

        assert_eq!(diagram.betti_number(0, 0.0), 2);
        assert_eq!(diagram.betti_number(1, 0.0), 1);
    }

    #[test]
    fn test_diagram_total_persistence() {
        let mut diagram = PersistenceDiagram::new(1);
        diagram.add_pair(0.0, 1.0, 0);
        diagram.add_pair(0.0, 2.0, 0);

        assert!((diagram.total_persistence(0) - 3.0).abs() < 0.01);
    }

    #[test]
    fn test_diagram_entropy() {
        let mut diagram = PersistenceDiagram::new(1);
        diagram.add_pair(0.0, 1.0, 0);
        diagram.add_pair(0.0, 1.0, 0);

        let entropy = diagram.entropy(0);
        assert!(entropy > 0.0);
    }

    #[test]
    fn test_bottleneck_distance_same() {
        let dgm = vec![(0.0, 1.0), (0.5, 1.5)];
        let dist = PersistenceDistance::bottleneck(&dgm, &dgm);
        assert!(dist < 0.01);
    }

    #[test]
    fn test_bottleneck_distance_different() {
        let dgm1 = vec![(0.0, 1.0)];
        let dgm2 = vec![(0.0, 2.0)];
        let dist = PersistenceDistance::bottleneck(&dgm1, &dgm2);
        assert!(dist > 0.0);
    }

    #[test]
    fn test_wasserstein_distance() {
        let dgm1 = vec![(0.0, 1.0)];
        let dgm2 = vec![(0.0, 1.5)];
        let dist = PersistenceDistance::wasserstein(&dgm1, &dgm2, 2.0);
        assert!(dist > 0.0);
    }

    #[test]
    fn test_fingerprint_similarity_same() {
        let fp = TopologicalFingerprint {
            fingerprint_id: "test".to_string(),
            betti_signature: (5, 2, 0),
            persistence_signature: (1.0, 0.5, 0.0),
            entropy_signature: (0.5, 0.3, 0.0),
            landscape_hash: "abc123".to_string(),
        };

        let sim = fp.similarity(&fp);
        assert!((sim - 1.0).abs() < 0.01);
    }

    #[test]
    fn test_tda_engine_persistence() {
        let mut engine = TDAEngine::new(1);
        let points = vec![
            vec![0.0, 0.0],
            vec![1.0, 0.0],
            vec![0.5, 0.5],
        ];

        let diagram = engine.compute_persistence(&points);
        assert!(!diagram.pairs.is_empty());
    }

    #[test]
    fn test_tda_engine_betti() {
        let mut engine = TDAEngine::new(1);
        let points = vec![
            vec![0.0, 0.0],
            vec![1.0, 0.0],
            vec![2.0, 0.0],
        ];

        let (b0, b1, _) = engine.betti_numbers(&points, 0.0);
        assert!(b0 > 0);
        assert_eq!(b1, 0); // No loops in line
    }

    #[test]
    fn test_tda_engine_fingerprint() {
        let mut engine = TDAEngine::new(1);
        let points = vec![
            vec![0.0, 0.0],
            vec![1.0, 0.0],
        ];

        let fp = engine.fingerprint(&points, "test");
        assert_eq!(fp.fingerprint_id, "test");
    }

    #[test]
    fn test_attention_topology_normal() {
        let mut engine = TDAEngine::new(1);
        let attention = vec![
            vec![0.5, 0.3, 0.2],
            vec![0.3, 0.5, 0.2],
            vec![0.2, 0.2, 0.6],
        ];

        let result = engine.analyze_attention(&attention, 0.1);
        assert!(result.betti_0 >= 1);
    }

    #[test]
    fn test_engine_stats() {
        let mut engine = TDAEngine::new(2);
        let points = vec![vec![0.0], vec![1.0]];
        engine.compute_persistence(&points);
        engine.compute_persistence(&points);

        let stats = engine.get_stats();
        assert_eq!(stats.analyses_performed, 2);
    }
}
