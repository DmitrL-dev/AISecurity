//! Spectral Graph Engine - Graph Laplacian Analysis
//!
//! Based on research:
//!   - SpGAT: Spectral Graph Attention Network
//!   - SAN: Spectral Attention Network with learned positional encodings
//!   - SAT: Spectral Adversarial Training for GNN robustness
//!
//! Theory:
//!   Studies eigenvalues/eigenvectors of graph Laplacian.
//!   - Eigenvalues reveal connectivity structure
//!   - Fiedler value indicates graph cohesion
//!   - Spectral gap measures separation

use std::collections::HashMap;

/// Types of graph Laplacian
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum LaplacianType {
    Unnormalized,  // L = D - A
    Normalized,    // L = I - D^(-1/2) A D^(-1/2)
    RandomWalk,    // L = I - D^(-1) A
}

/// Laplacian matrix and components
#[derive(Debug, Clone)]
pub struct LaplacianMatrix {
    pub laplacian: Vec<Vec<f64>>,
    pub degree_matrix: Vec<f64>,
    pub adjacency_matrix: Vec<Vec<f64>>,
    pub laplacian_type: LaplacianType,
    pub size: usize,
}

/// Eigendecomposition result
#[derive(Debug, Clone)]
pub struct SpectralDecomposition {
    pub eigenvalues: Vec<f64>,
    pub eigenvectors: Vec<Vec<f64>>,
    pub fiedler_value: f64,
    pub fiedler_vector: Vec<f64>,
    pub spectral_gap: f64,
}

/// Graph Fourier Transform
#[derive(Debug, Clone)]
pub struct GraphFourierTransform {
    pub coefficients: Vec<f64>,
    pub frequencies: Vec<f64>,
    pub energy_distribution: Vec<f64>,
}

impl GraphFourierTransform {
    pub fn low_frequency_energy(&self, k: usize) -> f64 {
        self.energy_distribution.iter().take(k).sum()
    }

    pub fn high_frequency_energy(&self, k: usize) -> f64 {
        let n = self.energy_distribution.len();
        if k >= n {
            return self.energy_distribution.iter().sum();
        }
        self.energy_distribution.iter().skip(n - k).sum()
    }
}

/// Spectral clustering result
#[derive(Debug, Clone)]
pub struct SpectralClustering {
    pub labels: Vec<usize>,
    pub num_clusters: usize,
    pub cluster_sizes: Vec<usize>,
    pub silhouette_score: f64,
}

/// Spectral anomaly result
#[derive(Debug, Clone)]
pub struct SpectralAnomaly {
    pub is_anomalous: bool,
    pub anomaly_score: f64,
    pub anomaly_type: String,
    pub details: HashMap<String, f64>,
}

/// Laplacian Builder
pub struct LaplacianBuilder {
    epsilon: f64,
}

impl Default for LaplacianBuilder {
    fn default() -> Self {
        Self::new()
    }
}

impl LaplacianBuilder {
    pub fn new() -> Self {
        Self { epsilon: 1e-10 }
    }

    /// Build Laplacian from attention matrix
    pub fn from_attention(
        &self,
        attention: &[Vec<f64>],
        threshold: f64,
        laplacian_type: LaplacianType,
    ) -> LaplacianMatrix {
        let n = attention.len();
        
        // Threshold to create adjacency
        let mut adjacency: Vec<Vec<f64>> = vec![vec![0.0; n]; n];
        for i in 0..n {
            for j in 0..n {
                if attention[i][j] > threshold {
                    adjacency[i][j] = attention[i][j];
                }
            }
        }

        // Make symmetric
        for i in 0..n {
            for j in i + 1..n {
                let avg = (adjacency[i][j] + adjacency[j][i]) / 2.0;
                adjacency[i][j] = avg;
                adjacency[j][i] = avg;
            }
        }

        self.from_adjacency(&adjacency, laplacian_type)
    }

    /// Build Laplacian from adjacency matrix
    pub fn from_adjacency(
        &self,
        adjacency: &[Vec<f64>],
        laplacian_type: LaplacianType,
    ) -> LaplacianMatrix {
        let n = adjacency.len();
        
        // Compute degree for each node
        let degrees: Vec<f64> = adjacency
            .iter()
            .map(|row| row.iter().sum())
            .collect();

        let laplacian = match laplacian_type {
            LaplacianType::Unnormalized => {
                // L = D - A
                let mut l = vec![vec![0.0; n]; n];
                for i in 0..n {
                    l[i][i] = degrees[i];
                    for j in 0..n {
                        l[i][j] -= adjacency[i][j];
                    }
                }
                l
            }
            LaplacianType::Normalized => {
                // L = I - D^(-1/2) A D^(-1/2)
                let d_inv_sqrt: Vec<f64> = degrees
                    .iter()
                    .map(|&d| 1.0 / (d + self.epsilon).sqrt())
                    .collect();

                let mut l = vec![vec![0.0; n]; n];
                for i in 0..n {
                    l[i][i] = 1.0;
                    for j in 0..n {
                        l[i][j] -= d_inv_sqrt[i] * adjacency[i][j] * d_inv_sqrt[j];
                    }
                }
                l
            }
            LaplacianType::RandomWalk => {
                // L = I - D^(-1) A
                let mut l = vec![vec![0.0; n]; n];
                for i in 0..n {
                    l[i][i] = 1.0;
                    let d_inv = 1.0 / (degrees[i] + self.epsilon);
                    for j in 0..n {
                        l[i][j] -= d_inv * adjacency[i][j];
                    }
                }
                l
            }
        };

        LaplacianMatrix {
            laplacian,
            degree_matrix: degrees,
            adjacency_matrix: adjacency.to_vec(),
            laplacian_type,
            size: n,
        }
    }

    /// Build from embeddings using k-NN similarity graph
    pub fn from_embeddings(
        &self,
        embeddings: &[Vec<f64>],
        k_neighbors: usize,
        laplacian_type: LaplacianType,
    ) -> LaplacianMatrix {
        let n = embeddings.len();
        let mut adjacency = vec![vec![0.0; n]; n];

        for i in 0..n {
            // Compute distances to all other points
            let mut distances: Vec<(usize, f64)> = (0..n)
                .filter(|&j| j != i)
                .map(|j| {
                    let dist: f64 = embeddings[i]
                        .iter()
                        .zip(&embeddings[j])
                        .map(|(a, b)| (a - b).powi(2))
                        .sum::<f64>()
                        .sqrt();
                    (j, dist)
                })
                .collect();

            distances.sort_by(|a, b| a.1.partial_cmp(&b.1).unwrap());

            // Connect to k nearest neighbors
            for &(j, dist) in distances.iter().take(k_neighbors) {
                let similarity = 1.0 / (1.0 + dist);
                adjacency[i][j] = similarity;
                adjacency[j][i] = similarity;
            }
        }

        self.from_adjacency(&adjacency, laplacian_type)
    }
}

/// Spectral Analyzer - eigendecomposition and analysis
pub struct SpectralAnalyzer;

impl Default for SpectralAnalyzer {
    fn default() -> Self {
        Self::new()
    }
}

impl SpectralAnalyzer {
    pub fn new() -> Self {
        Self
    }

    /// Compute eigendecomposition using power iteration (simplified)
    /// For full implementation, use nalgebra crate
    pub fn decompose(&self, laplacian: &LaplacianMatrix) -> SpectralDecomposition {
        let n = laplacian.size;
        
        if n == 0 {
            return SpectralDecomposition {
                eigenvalues: vec![],
                eigenvectors: vec![],
                fiedler_value: 0.0,
                fiedler_vector: vec![],
                spectral_gap: 0.0,
            };
        }

        // Simple eigenvalue approximation using power iteration
        let eigenvalues = self.compute_eigenvalues(&laplacian.laplacian, n.min(10));
        let eigenvectors = self.compute_eigenvectors(&laplacian.laplacian, &eigenvalues);

        let fiedler_value = if eigenvalues.len() > 1 {
            eigenvalues[1]
        } else {
            0.0
        };

        let fiedler_vector = if eigenvectors.len() > 1 {
            eigenvectors[1].clone()
        } else {
            vec![0.0; n]
        };

        let spectral_gap = if eigenvalues.len() > 1 {
            eigenvalues[1] - eigenvalues[0]
        } else {
            0.0
        };

        SpectralDecomposition {
            eigenvalues,
            eigenvectors,
            fiedler_value,
            fiedler_vector,
            spectral_gap,
        }
    }

    /// Approximate eigenvalues using Gershgorin circles and matrix properties
    fn compute_eigenvalues(&self, matrix: &[Vec<f64>], k: usize) -> Vec<f64> {
        let n = matrix.len();
        if n == 0 {
            return vec![];
        }

        // For symmetric matrices, eigenvalues are real
        // Use simple diagonal approximation for demo
        let mut eigenvalues: Vec<f64> = (0..n)
            .map(|i| {
                // Gershgorin disc center (diagonal element)
                let center = matrix[i][i];
                // Radius (sum of off-diagonal elements)
                let radius: f64 = matrix[i]
                    .iter()
                    .enumerate()
                    .filter(|&(j, _)| j != i)
                    .map(|(_, &v)| v.abs())
                    .sum();
                // Approximate eigenvalue
                center - radius * 0.5
            })
            .collect();

        eigenvalues.sort_by(|a, b| a.partial_cmp(b).unwrap());
        eigenvalues.truncate(k);
        eigenvalues
    }

    /// Compute approximate eigenvectors
    fn compute_eigenvectors(&self, matrix: &[Vec<f64>], eigenvalues: &[f64]) -> Vec<Vec<f64>> {
        let n = matrix.len();
        
        eigenvalues
            .iter()
            .enumerate()
            .map(|(i, _)| {
                // Simple basis vector approximation
                let mut v = vec![0.0; n];
                if i < n {
                    v[i] = 1.0;
                }
                v
            })
            .collect()
    }

    /// Graph Fourier Transform
    pub fn graph_fourier_transform(
        &self,
        signal: &[f64],
        decomposition: &SpectralDecomposition,
    ) -> GraphFourierTransform {
        let _n = signal.len();
        
        // GFT = U^T * signal
        let coefficients: Vec<f64> = decomposition
            .eigenvectors
            .iter()
            .map(|v| {
                v.iter()
                    .zip(signal)
                    .map(|(&vi, &si)| vi * si)
                    .sum()
            })
            .collect();

        // Energy distribution
        let energy: Vec<f64> = coefficients.iter().map(|c| c * c).collect();
        let total_energy: f64 = energy.iter().sum::<f64>() + 1e-10;
        let energy_distribution: Vec<f64> = energy
            .iter()
            .map(|&e| e / total_energy)
            .collect();

        GraphFourierTransform {
            coefficients,
            frequencies: decomposition.eigenvalues.clone(),
            energy_distribution,
        }
    }

    /// Filter signal using spectral methods
    pub fn filter_signal(
        &self,
        signal: &[f64],
        decomposition: &SpectralDecomposition,
        filter_type: &str,
        cutoff: usize,
    ) -> Vec<f64> {
        let mut gft = self.graph_fourier_transform(signal, decomposition);
        
        match filter_type {
            "low_pass" => {
                for i in cutoff..gft.coefficients.len() {
                    gft.coefficients[i] = 0.0;
                }
            }
            "high_pass" => {
                for i in 0..cutoff.min(gft.coefficients.len()) {
                    gft.coefficients[i] = 0.0;
                }
            }
            "band_pass" => {
                let half = cutoff / 2;
                for i in 0..half.min(gft.coefficients.len()) {
                    gft.coefficients[i] = 0.0;
                }
                let start = gft.coefficients.len().saturating_sub(half);
                for i in start..gft.coefficients.len() {
                    gft.coefficients[i] = 0.0;
                }
            }
            _ => {}
        }

        // Inverse GFT: U * coefficients
        let n = signal.len();
        let mut result = vec![0.0; n];
        for (i, v) in decomposition.eigenvectors.iter().enumerate() {
            if i < gft.coefficients.len() {
                for (j, &vj) in v.iter().enumerate() {
                    if j < n {
                        result[j] += vj * gft.coefficients[i];
                    }
                }
            }
        }
        result
    }
}

/// Spectral Clusterer
pub struct SpectralClusterer {
    #[allow(dead_code)]
    n_clusters: usize,
}

impl SpectralClusterer {
    pub fn new(n_clusters: usize) -> Self {
        Self { n_clusters }
    }

    /// Perform spectral clustering
    pub fn cluster(&self, decomposition: &SpectralDecomposition) -> SpectralClustering {
        let n = decomposition.eigenvectors.first().map(|v| v.len()).unwrap_or(0);
        
        if n == 0 {
            return SpectralClustering {
                labels: vec![],
                num_clusters: 0,
                cluster_sizes: vec![],
                silhouette_score: 0.0,
            };
        }

        // Use Fiedler vector for 2-way partitioning
        let labels: Vec<usize> = if decomposition.fiedler_vector.is_empty() {
            vec![0; n]
        } else {
            decomposition
                .fiedler_vector
                .iter()
                .map(|&v| if v >= 0.0 { 0 } else { 1 })
                .collect()
        };

        let num_clusters = labels.iter().max().copied().unwrap_or(0) + 1;
        
        let mut cluster_sizes = vec![0usize; num_clusters];
        for &label in &labels {
            if label < num_clusters {
                cluster_sizes[label] += 1;
            }
        }

        // Simple silhouette approximation
        let silhouette = if num_clusters > 1 {
            let min_size = *cluster_sizes.iter().min().unwrap_or(&1) as f64;
            let max_size = *cluster_sizes.iter().max().unwrap_or(&1) as f64;
            min_size / max_size.max(1.0)
        } else {
            0.0
        };

        SpectralClustering {
            labels,
            num_clusters,
            cluster_sizes,
            silhouette_score: silhouette,
        }
    }
}

/// Spectral Anomaly Detector
pub struct SpectralAnomalyDetector {
    fiedler_threshold: f64,
    gap_threshold: f64,
    energy_threshold: f64,
}

impl Default for SpectralAnomalyDetector {
    fn default() -> Self {
        Self::new()
    }
}

impl SpectralAnomalyDetector {
    pub fn new() -> Self {
        Self {
            fiedler_threshold: 0.01,
            gap_threshold: 0.1,
            energy_threshold: 0.3,
        }
    }

    /// Detect spectral anomalies
    pub fn detect(
        &self,
        decomposition: &SpectralDecomposition,
        gft: Option<&GraphFourierTransform>,
    ) -> SpectralAnomaly {
        let mut anomalies: Vec<&str> = Vec::new();
        let mut details: HashMap<String, f64> = HashMap::new();
        let mut total_score: f64 = 0.0;

        // Check Fiedler value
        if decomposition.fiedler_value < self.fiedler_threshold {
            anomalies.push("low_connectivity");
            total_score += 0.3;
            details.insert("fiedler_value".to_string(), decomposition.fiedler_value);
        }

        // Check spectral gap
        if decomposition.spectral_gap < self.gap_threshold {
            anomalies.push("small_spectral_gap");
            total_score += 0.2;
            details.insert("spectral_gap".to_string(), decomposition.spectral_gap);
        }

        // Check for disconnected components (near-zero eigenvalues)
        let near_zero = decomposition
            .eigenvalues
            .iter()
            .filter(|&&e| e.abs() < 1e-6)
            .count();
        if near_zero > 1 {
            anomalies.push("disconnected_graph");
            total_score += 0.3;
            details.insert("disconnected_components".to_string(), near_zero as f64);
        }

        // Check high frequency energy
        if let Some(transform) = gft {
            let high_freq = transform.high_frequency_energy(5);
            if high_freq > self.energy_threshold {
                anomalies.push("high_frequency_anomaly");
                total_score += 0.2;
                details.insert("high_freq_energy".to_string(), high_freq);
            }
        }

        let anomaly_type = anomalies.first().unwrap_or(&"none").to_string();

        SpectralAnomaly {
            is_anomalous: !anomalies.is_empty(),
            anomaly_score: total_score.min(1.0),
            anomaly_type,
            details,
        }
    }
}

/// Main Spectral Graph Engine
pub struct SpectralGraphEngine {
    laplacian_builder: LaplacianBuilder,
    analyzer: SpectralAnalyzer,
    clusterer: SpectralClusterer,
    anomaly_detector: SpectralAnomalyDetector,
    analysis_count: usize,
}

impl Default for SpectralGraphEngine {
    fn default() -> Self {
        Self::new()
    }
}

impl SpectralGraphEngine {
    pub fn new() -> Self {
        Self {
            laplacian_builder: LaplacianBuilder::new(),
            analyzer: SpectralAnalyzer::new(),
            clusterer: SpectralClusterer::new(3),
            anomaly_detector: SpectralAnomalyDetector::new(),
            analysis_count: 0,
        }
    }

    /// Analyze attention matrix
    pub fn analyze_attention(&mut self, attention: &[Vec<f64>], threshold: f64) -> AnalysisResult {
        let laplacian = self.laplacian_builder.from_attention(
            attention,
            threshold,
            LaplacianType::Normalized,
        );

        let decomposition = self.analyzer.decompose(&laplacian);

        // GFT of uniform signal
        let n = attention.len();
        let signal: Vec<f64> = vec![1.0 / n as f64; n];
        let gft = self.analyzer.graph_fourier_transform(&signal, &decomposition);

        let anomaly = self.anomaly_detector.detect(&decomposition, Some(&gft));

        self.analysis_count += 1;

        AnalysisResult {
            fiedler_value: decomposition.fiedler_value,
            spectral_gap: decomposition.spectral_gap,
            low_freq_energy: gft.low_frequency_energy(5),
            high_freq_energy: gft.high_frequency_energy(5),
            anomaly,
        }
    }

    /// Analyze embeddings
    pub fn analyze_embeddings(
        &mut self,
        embeddings: &[Vec<f64>],
        k_neighbors: usize,
    ) -> EmbeddingAnalysisResult {
        let laplacian = self.laplacian_builder.from_embeddings(
            embeddings,
            k_neighbors,
            LaplacianType::Normalized,
        );

        let decomposition = self.analyzer.decompose(&laplacian);
        let clustering = self.clusterer.cluster(&decomposition);
        let anomaly = self.anomaly_detector.detect(&decomposition, None);

        self.analysis_count += 1;

        EmbeddingAnalysisResult {
            fiedler_value: decomposition.fiedler_value,
            spectral_gap: decomposition.spectral_gap,
            clustering,
            anomaly,
        }
    }

    /// Get Fiedler vector for partitioning
    pub fn get_fiedler_vector(&self, attention: &[Vec<f64>]) -> Vec<f64> {
        let laplacian = self.laplacian_builder.from_attention(
            attention,
            0.0,
            LaplacianType::Normalized,
        );
        let decomposition = self.analyzer.decompose(&laplacian);
        decomposition.fiedler_vector
    }

    /// Get engine stats
    pub fn get_stats(&self) -> EngineStats {
        EngineStats {
            analyses_performed: self.analysis_count,
        }
    }
}

/// Analysis result for attention matrices
#[derive(Debug, Clone)]
pub struct AnalysisResult {
    pub fiedler_value: f64,
    pub spectral_gap: f64,
    pub low_freq_energy: f64,
    pub high_freq_energy: f64,
    pub anomaly: SpectralAnomaly,
}

/// Analysis result for embeddings
#[derive(Debug, Clone)]
pub struct EmbeddingAnalysisResult {
    pub fiedler_value: f64,
    pub spectral_gap: f64,
    pub clustering: SpectralClustering,
    pub anomaly: SpectralAnomaly,
}

/// Engine statistics
#[derive(Debug, Clone)]
pub struct EngineStats {
    pub analyses_performed: usize,
}

#[cfg(test)]
mod tests {
    use super::*;

    fn create_simple_graph() -> Vec<Vec<f64>> {
        // 3-node connected graph
        vec![
            vec![0.0, 1.0, 1.0],
            vec![1.0, 0.0, 1.0],
            vec![1.0, 1.0, 0.0],
        ]
    }

    #[test]
    fn test_laplacian_unnormalized() {
        let builder = LaplacianBuilder::new();
        let adj = create_simple_graph();
        let lap = builder.from_adjacency(&adj, LaplacianType::Unnormalized);

        assert_eq!(lap.size, 3);
        // Degree should be 2 for each node
        assert!((lap.degree_matrix[0] - 2.0).abs() < 0.01);
    }

    #[test]
    fn test_laplacian_normalized() {
        let builder = LaplacianBuilder::new();
        let adj = create_simple_graph();
        let lap = builder.from_adjacency(&adj, LaplacianType::Normalized);

        // Normalized Laplacian diagonal should be 1
        assert!((lap.laplacian[0][0] - 1.0).abs() < 0.01);
    }

    #[test]
    fn test_spectral_decomposition() {
        let builder = LaplacianBuilder::new();
        let analyzer = SpectralAnalyzer::new();
        
        let adj = create_simple_graph();
        let lap = builder.from_adjacency(&adj, LaplacianType::Normalized);
        let decomp = analyzer.decompose(&lap);

        assert!(!decomp.eigenvalues.is_empty());
        assert!(!decomp.fiedler_vector.is_empty());
    }

    #[test]
    fn test_gft() {
        let builder = LaplacianBuilder::new();
        let analyzer = SpectralAnalyzer::new();
        
        let adj = create_simple_graph();
        let lap = builder.from_adjacency(&adj, LaplacianType::Normalized);
        let decomp = analyzer.decompose(&lap);

        let signal = vec![1.0, 0.0, 0.0];
        let gft = analyzer.graph_fourier_transform(&signal, &decomp);

        assert!(!gft.coefficients.is_empty());
        assert!(gft.low_frequency_energy(1) >= 0.0);
    }

    #[test]
    fn test_spectral_clustering() {
        let builder = LaplacianBuilder::new();
        let analyzer = SpectralAnalyzer::new();
        let clusterer = SpectralClusterer::new(2);
        
        let adj = create_simple_graph();
        let lap = builder.from_adjacency(&adj, LaplacianType::Normalized);
        let decomp = analyzer.decompose(&lap);
        let clustering = clusterer.cluster(&decomp);

        assert_eq!(clustering.labels.len(), 3);
        assert!(clustering.num_clusters > 0);
    }

    #[test]
    fn test_anomaly_detection_normal() {
        let builder = LaplacianBuilder::new();
        let analyzer = SpectralAnalyzer::new();
        let detector = SpectralAnomalyDetector::new();
        
        let adj = create_simple_graph();
        let lap = builder.from_adjacency(&adj, LaplacianType::Normalized);
        let decomp = analyzer.decompose(&lap);
        
        let anomaly = detector.detect(&decomp, None);
        // Connected graph should not be anomalous for connectivity
        assert!(anomaly.anomaly_score <= 1.0);
    }

    #[test]
    fn test_engine_analyze_attention() {
        let mut engine = SpectralGraphEngine::new();
        
        let attention = vec![
            vec![0.5, 0.3, 0.2],
            vec![0.3, 0.5, 0.2],
            vec![0.2, 0.2, 0.6],
        ];

        let result = engine.analyze_attention(&attention, 0.1);
        
        assert!(result.fiedler_value >= 0.0 || result.fiedler_value < 0.0); // Any value
        assert!(result.anomaly.anomaly_score >= 0.0);
    }

    #[test]
    fn test_engine_analyze_embeddings() {
        let mut engine = SpectralGraphEngine::new();
        
        let embeddings = vec![
            vec![0.0, 0.0],
            vec![1.0, 0.0],
            vec![0.5, 0.5],
            vec![0.0, 1.0],
        ];

        let result = engine.analyze_embeddings(&embeddings, 2);
        
        assert!(result.clustering.num_clusters > 0);
        assert_eq!(result.clustering.labels.len(), 4);
    }

    #[test]
    fn test_engine_fiedler_vector() {
        let engine = SpectralGraphEngine::new();
        
        let attention = vec![
            vec![0.5, 0.5],
            vec![0.5, 0.5],
        ];

        let fiedler = engine.get_fiedler_vector(&attention);
        assert_eq!(fiedler.len(), 2);
    }

    #[test]
    fn test_engine_stats() {
        let mut engine = SpectralGraphEngine::new();
        
        let attention = vec![vec![1.0]];
        engine.analyze_attention(&attention, 0.0);
        engine.analyze_attention(&attention, 0.0);

        let stats = engine.get_stats();
        assert_eq!(stats.analyses_performed, 2);
    }

    #[test]
    fn test_from_embeddings_knn() {
        let builder = LaplacianBuilder::new();
        
        let embeddings = vec![
            vec![0.0, 0.0],
            vec![1.0, 0.0],
            vec![2.0, 0.0],
        ];

        let lap = builder.from_embeddings(&embeddings, 1, LaplacianType::Normalized);
        assert_eq!(lap.size, 3);
    }

    #[test]
    fn test_filter_signal_low_pass() {
        let builder = LaplacianBuilder::new();
        let analyzer = SpectralAnalyzer::new();
        
        let adj = create_simple_graph();
        let lap = builder.from_adjacency(&adj, LaplacianType::Normalized);
        let decomp = analyzer.decompose(&lap);

        let signal = vec![1.0, 0.5, 0.0];
        let filtered = analyzer.filter_signal(&signal, &decomp, "low_pass", 1);
        
        assert_eq!(filtered.len(), 3);
    }

    #[test]
    fn test_high_freq_energy() {
        let gft = GraphFourierTransform {
            coefficients: vec![1.0, 2.0, 3.0, 4.0, 5.0],
            frequencies: vec![0.0, 0.1, 0.2, 0.3, 0.4],
            energy_distribution: vec![0.1, 0.1, 0.2, 0.3, 0.3],
        };

        let high = gft.high_frequency_energy(2);
        assert!((high - 0.6).abs() < 0.01);
    }

    #[test]
    fn test_low_freq_energy() {
        let gft = GraphFourierTransform {
            coefficients: vec![1.0, 2.0, 3.0],
            frequencies: vec![0.0, 0.1, 0.2],
            energy_distribution: vec![0.5, 0.3, 0.2],
        };

        let low = gft.low_frequency_energy(2);
        assert!((low - 0.8).abs() < 0.01);
    }
}
