//! Hyperbolic Geometry Engine - Non-Euclidean Embedding Analysis
//!
//! Based on:
//!   - Nickel & Kiela 2017: Poincaré embeddings
//!   - MERU 2023: Hyperbolic vision-language models
//!   - HiM 2025: Poincaré + state space models
//!
//! Theory:
//!   Hyperbolic space has constant negative curvature, allowing
//!   exponential growth - perfect for hierarchical structures.
//!   In the Poincaré ball model:
//!   - Center = root of hierarchy
//!   - Boundary = leaves
//!   - Norm = depth in hierarchy
//!   - Distance = semantic similarity

use std::collections::HashMap;

/// Poincaré ball operations for hyperbolic geometry
#[derive(Debug, Clone)]
pub struct PoincareBall {
    /// Curvature constant (positive value, actual curvature is -c)
    pub c: f64,
    /// Numerical epsilon for stability
    epsilon: f64,
}

impl Default for PoincareBall {
    fn default() -> Self {
        Self::new(1.0)
    }
}

impl PoincareBall {
    /// Create new Poincaré ball with given curvature
    pub fn new(curvature: f64) -> Self {
        Self {
            c: curvature.abs(),
            epsilon: 1e-7,
        }
    }

    /// Compute dot product of two vectors
    #[inline]
    fn dot(x: &[f64], y: &[f64]) -> f64 {
        x.iter().zip(y.iter()).map(|(a, b)| a * b).sum()
    }

    /// Compute Euclidean norm
    #[inline]
    fn norm(x: &[f64]) -> f64 {
        Self::dot(x, x).sqrt()
    }

    /// Compute squared norm
    #[inline]
    fn norm_sq(x: &[f64]) -> f64 {
        Self::dot(x, x)
    }

    /// Project point into Poincaré ball (ensure norm < max_norm)
    pub fn project(&self, x: &[f64], max_norm: f64) -> Vec<f64> {
        let norm = Self::norm(x);
        if norm >= max_norm {
            x.iter().map(|&v| v / norm * max_norm).collect()
        } else {
            x.to_vec()
        }
    }

    /// Möbius addition in Poincaré ball
    ///
    /// x ⊕ y = ((1 + 2c⟨x,y⟩ + c||y||²)x + (1 - c||x||²)y) /
    ///         (1 + 2c⟨x,y⟩ + c²||x||²||y||²)
    pub fn mobius_add(&self, x: &[f64], y: &[f64]) -> Vec<f64> {
        let c = self.c;

        let x_norm_sq = Self::norm_sq(x);
        let y_norm_sq = Self::norm_sq(y);
        let xy_dot = Self::dot(x, y);

        let num_coeff_x = 1.0 + 2.0 * c * xy_dot + c * y_norm_sq;
        let num_coeff_y = 1.0 - c * x_norm_sq;
        let denom = 1.0 + 2.0 * c * xy_dot + c * c * x_norm_sq * y_norm_sq + self.epsilon;

        let result: Vec<f64> = x
            .iter()
            .zip(y.iter())
            .map(|(&xi, &yi)| (num_coeff_x * xi + num_coeff_y * yi) / denom)
            .collect();

        self.project(&result, 0.99)
    }

    /// Geodesic distance in Poincaré ball
    ///
    /// d(x,y) = (2/√c) arctanh(√c ||−x ⊕ y||)
    pub fn distance(&self, x: &[f64], y: &[f64]) -> f64 {
        let c = self.c;
        let sqrt_c = c.sqrt();

        // -x ⊕ y
        let neg_x: Vec<f64> = x.iter().map(|&v| -v).collect();
        let diff = self.mobius_add(&neg_x, y);
        let diff_norm = Self::norm(&diff);

        // Clamp to avoid numerical issues
        let scaled = (sqrt_c * diff_norm).min(1.0 - self.epsilon);

        (2.0 / sqrt_c) * scaled.atanh()
    }

    /// Exponential map: project tangent vector onto manifold
    ///
    /// exp_x(v) = x ⊕ (tanh(√c λ_x ||v|| / 2) * v / (√c ||v||))
    pub fn exp_map(&self, x: &[f64], v: &[f64]) -> Vec<f64> {
        let c = self.c;
        let sqrt_c = c.sqrt();

        let x_norm_sq = Self::norm_sq(x);
        let lambda_x = 2.0 / (1.0 - c * x_norm_sq + self.epsilon);

        let v_norm = Self::norm(v) + self.epsilon;

        let factor = (sqrt_c * lambda_x * v_norm / 2.0).tanh() / (sqrt_c * v_norm);

        let second_term: Vec<f64> = v.iter().map(|&vi| factor * vi).collect();

        self.mobius_add(x, &second_term)
    }

    /// Logarithmic map: project point to tangent space
    ///
    /// log_x(y) = (2 / (√c λ_x)) arctanh(√c ||-x ⊕ y||) * (-x ⊕ y) / ||-x ⊕ y||
    pub fn log_map(&self, x: &[f64], y: &[f64]) -> Vec<f64> {
        let c = self.c;
        let sqrt_c = c.sqrt();

        let x_norm_sq = Self::norm_sq(x);
        let lambda_x = 2.0 / (1.0 - c * x_norm_sq + self.epsilon);

        let neg_x: Vec<f64> = x.iter().map(|&v| -v).collect();
        let diff = self.mobius_add(&neg_x, y);
        let diff_norm = Self::norm(&diff) + self.epsilon;

        let scaled = (sqrt_c * diff_norm).min(1.0 - self.epsilon);

        let factor = (2.0 / (sqrt_c * lambda_x)) * scaled.atanh() / diff_norm;

        diff.iter().map(|&d| factor * d).collect()
    }

    /// Compute Fréchet mean (hyperbolic centroid)
    ///
    /// Minimizes sum of squared geodesic distances
    pub fn frechet_mean(&self, points: &[Vec<f64>], max_iter: usize, tol: f64) -> Vec<f64> {
        let n = points.len();
        if n == 0 {
            return vec![];
        }
        if n == 1 {
            return points[0].clone();
        }

        let dim = points[0].len();

        // Initialize with scaled Euclidean mean
        let mut mean: Vec<f64> = vec![0.0; dim];
        for p in points {
            for (i, &v) in p.iter().enumerate() {
                mean[i] += v;
            }
        }
        for v in &mut mean {
            *v = *v / (n as f64) * 0.5;
        }
        mean = self.project(&mean, 0.99);

        for _ in 0..max_iter {
            // Compute gradient: sum of log maps
            let mut gradient: Vec<f64> = vec![0.0; dim];
            for p in points {
                let log = self.log_map(&mean, p);
                for (i, &v) in log.iter().enumerate() {
                    gradient[i] += v / (n as f64);
                }
            }

            // Update using exponential map
            let new_mean = self.exp_map(&mean, &gradient);

            // Check convergence
            let diff: f64 = mean
                .iter()
                .zip(new_mean.iter())
                .map(|(&a, &b)| (a - b).powi(2))
                .sum::<f64>()
                .sqrt();

            mean = new_mean;

            if diff < tol {
                break;
            }
        }

        mean
    }
}

/// Hyperbolic embedding result
#[derive(Debug, Clone)]
pub struct HyperbolicEmbedding {
    pub points: Vec<Vec<f64>>,
    pub curvature: f64,
}

impl HyperbolicEmbedding {
    /// Get norms of all points
    pub fn norms(&self) -> Vec<f64> {
        self.points
            .iter()
            .map(|p| PoincareBall::norm(p))
            .collect()
    }

    /// Estimate hierarchy levels from norms
    pub fn hierarchy_levels(&self) -> Vec<f64> {
        self.norms()
            .iter()
            .map(|&n| n / (1.0 - n + 1e-10))
            .collect()
    }
}

/// Hyperbolic metrics result
#[derive(Debug, Clone)]
pub struct HyperbolicMetrics {
    pub mean_norm: f64,
    pub norm_variance: f64,
    pub hierarchy_depth: f64,
    pub boundary_proximity: f64,
    pub centroid_distance: f64,
    pub distortion_score: f64,
}

/// Hyperbolic anomaly result
#[derive(Debug, Clone)]
pub struct HyperbolicAnomaly {
    pub is_anomalous: bool,
    pub anomaly_score: f64,
    pub anomaly_type: String,
    pub details: HashMap<String, f64>,
}

/// Hierarchy analyzer for hyperbolic embeddings
pub struct HierarchyAnalyzer {
    #[allow(dead_code)]
    ball: PoincareBall,
}

impl HierarchyAnalyzer {
    pub fn new(ball: PoincareBall) -> Self {
        Self { ball }
    }

    /// Estimate depth from norms (arctanh transformation)
    pub fn estimate_depth(&self, embedding: &HyperbolicEmbedding) -> Vec<f64> {
        embedding
            .norms()
            .iter()
            .map(|&n| n.min(0.99).atanh())
            .collect()
    }

    /// Find root node (closest to center)
    pub fn find_root(&self, embedding: &HyperbolicEmbedding) -> usize {
        embedding
            .norms()
            .iter()
            .enumerate()
            .min_by(|(_, a), (_, b)| a.partial_cmp(b).unwrap())
            .map(|(i, _)| i)
            .unwrap_or(0)
    }

    /// Find leaf nodes (close to boundary)
    pub fn find_leaves(&self, embedding: &HyperbolicEmbedding, threshold: f64) -> Vec<usize> {
        embedding
            .norms()
            .iter()
            .enumerate()
            .filter(|(_, &n)| n > threshold)
            .map(|(i, _)| i)
            .collect()
    }

    /// Measure hierarchy distortion (KS-like statistic)
    pub fn hierarchy_distortion(&self, embedding: &HyperbolicEmbedding) -> f64 {
        let mut norms = embedding.norms();
        norms.sort_by(|a, b| a.partial_cmp(b).unwrap());

        let n = norms.len();
        if n == 0 {
            return 0.0;
        }

        let max_dev = norms
            .iter()
            .enumerate()
            .map(|(i, &norm)| {
                let ideal = (i as f64) / (n as f64) * 0.9;
                (norm - ideal).abs()
            })
            .fold(0.0f64, |a, b| a.max(b));

        max_dev
    }

    /// Parent-child correlation quality
    pub fn parent_child_ratio(&self, embedding: &HyperbolicEmbedding) -> f64 {
        let depths = self.estimate_depth(embedding);
        let n = depths.len();

        if n < 2 {
            return 1.0;
        }

        // Count how many points are "above" each point
        let above_counts: Vec<f64> = depths
            .iter()
            .map(|&d| depths.iter().filter(|&&other| other < d).count() as f64)
            .collect();

        let ideal: Vec<f64> = (0..n).map(|i| i as f64).collect();

        // Compute correlation
        let mean_above = above_counts.iter().sum::<f64>() / n as f64;
        let mean_ideal = ideal.iter().sum::<f64>() / n as f64;

        let mut cov = 0.0;
        let mut var_above = 0.0;
        let mut var_ideal = 0.0;

        for i in 0..n {
            let a = above_counts[i] - mean_above;
            let b = ideal[i] - mean_ideal;
            cov += a * b;
            var_above += a * a;
            var_ideal += b * b;
        }

        if var_above < 1e-10 || var_ideal < 1e-10 {
            return 0.0;
        }

        cov / (var_above.sqrt() * var_ideal.sqrt())
    }
}

/// Hyperbolic anomaly detector
pub struct HyperbolicAnomalyDetector {
    #[allow(dead_code)]
    ball: PoincareBall,
    hierarchy: HierarchyAnalyzer,
    boundary_threshold: f64,
    distortion_threshold: f64,
}

impl HyperbolicAnomalyDetector {
    pub fn new(ball: PoincareBall) -> Self {
        let hierarchy = HierarchyAnalyzer::new(ball.clone());
        Self {
            ball,
            hierarchy,
            boundary_threshold: 0.95,
            distortion_threshold: 0.5,
        }
    }

    /// Detect anomalies in embedding
    pub fn detect(&self, embedding: &HyperbolicEmbedding) -> HyperbolicAnomaly {
        let mut anomalies: Vec<&str> = Vec::new();
        let mut details: HashMap<String, f64> = HashMap::new();
        let mut total_score: f64 = 0.0;

        let norms = embedding.norms();
        let n = norms.len();

        if n == 0 {
            return HyperbolicAnomaly {
                is_anomalous: false,
                anomaly_score: 0.0,
                anomaly_type: "none".to_string(),
                details,
            };
        }

        // 1. Check for points outside ball
        let outside = norms.iter().filter(|&&n| n >= 1.0).count();
        if outside > 0 {
            anomalies.push("invalid_points");
            total_score += 0.3;
            details.insert("outside_ball".to_string(), outside as f64);
        }

        // 2. Check for boundary clustering
        let near_boundary = norms.iter().filter(|&&n| n > self.boundary_threshold).count();
        if near_boundary as f64 > n as f64 * 0.8 {
            anomalies.push("boundary_clustering");
            total_score += 0.2;
            details.insert("near_boundary_ratio".to_string(), near_boundary as f64 / n as f64);
        }

        // 3. Check hierarchy distortion
        let distortion = self.hierarchy.hierarchy_distortion(embedding);
        if distortion > self.distortion_threshold {
            anomalies.push("hierarchy_distortion");
            total_score += 0.3;
            details.insert("distortion".to_string(), distortion);
        }

        // 4. Check for center clustering (flat hierarchy)
        let near_center = norms.iter().filter(|&&n| n < 0.1).count();
        if near_center as f64 > n as f64 * 0.8 {
            anomalies.push("flat_hierarchy");
            total_score += 0.2;
            details.insert("near_center_ratio".to_string(), near_center as f64 / n as f64);
        }

        let anomaly_type = anomalies.first().unwrap_or(&"none").to_string();

        HyperbolicAnomaly {
            is_anomalous: !anomalies.is_empty(),
            anomaly_score: total_score.min(1.0),
            anomaly_type,
            details,
        }
    }
}

/// Euclidean to Hyperbolic projection
pub struct EuclideanToHyperbolic {
    ball: PoincareBall,
}

impl EuclideanToHyperbolic {
    pub fn new(ball: PoincareBall) -> Self {
        Self { ball }
    }

    /// Simple projection via normalization
    pub fn project_simple(&self, embeddings: &[Vec<f64>]) -> HyperbolicEmbedding {
        if embeddings.is_empty() {
            return HyperbolicEmbedding {
                points: vec![],
                curvature: -self.ball.c,
            };
        }

        let max_norm = embeddings
            .iter()
            .map(|e| PoincareBall::norm(e))
            .fold(0.0f64, |a, b| a.max(b))
            + 1e-10;

        let scaled: Vec<Vec<f64>> = embeddings
            .iter()
            .map(|e| e.iter().map(|&v| v / max_norm * 0.9).collect())
            .collect();

        HyperbolicEmbedding {
            points: scaled,
            curvature: -self.ball.c,
        }
    }

    /// Project using exponential map from origin
    pub fn project_exponential(&self, embeddings: &[Vec<f64>], scale: f64) -> HyperbolicEmbedding {
        if embeddings.is_empty() {
            return HyperbolicEmbedding {
                points: vec![],
                curvature: -self.ball.c,
            };
        }

        let dim = embeddings[0].len();
        let origin = vec![0.0; dim];

        let projected: Vec<Vec<f64>> = embeddings
            .iter()
            .map(|e| {
                let v_scaled: Vec<f64> = e.iter().map(|&v| v * scale).collect();
                self.ball.exp_map(&origin, &v_scaled)
            })
            .collect();

        HyperbolicEmbedding {
            points: projected,
            curvature: -self.ball.c,
        }
    }
}

/// Main Hyperbolic Geometry Engine
pub struct HyperbolicGeometryEngine {
    pub ball: PoincareBall,
    hierarchy: HierarchyAnalyzer,
    projector: EuclideanToHyperbolic,
    anomaly_detector: HyperbolicAnomalyDetector,
    analysis_count: usize,
}

impl HyperbolicGeometryEngine {
    pub fn new(curvature: f64) -> Self {
        let ball = PoincareBall::new(curvature);
        let hierarchy = HierarchyAnalyzer::new(ball.clone());
        let projector = EuclideanToHyperbolic::new(ball.clone());
        let anomaly_detector = HyperbolicAnomalyDetector::new(ball.clone());

        Self {
            ball,
            hierarchy,
            projector,
            anomaly_detector,
            analysis_count: 0,
        }
    }

    /// Project Euclidean embeddings to Poincaré ball
    pub fn project_embeddings(&self, embeddings: &[Vec<f64>], method: &str) -> HyperbolicEmbedding {
        if method == "simple" {
            self.projector.project_simple(embeddings)
        } else {
            self.projector.project_exponential(embeddings, 0.1)
        }
    }

    /// Compute hyperbolic distance between points
    pub fn compute_distance(&self, point1: &[f64], point2: &[f64]) -> f64 {
        self.ball.distance(point1, point2)
    }

    /// Compute Fréchet mean of embedding
    pub fn compute_centroid(&self, embedding: &HyperbolicEmbedding) -> Vec<f64> {
        self.ball.frechet_mean(&embedding.points, 100, 1e-6)
    }

    /// Analyze hierarchical structure
    pub fn analyze_hierarchy(&mut self, embedding: &HyperbolicEmbedding) -> HierarchyAnalysis {
        let depths = self.hierarchy.estimate_depth(embedding);
        let root_idx = self.hierarchy.find_root(embedding);
        let leaves = self.hierarchy.find_leaves(embedding, 0.8);
        let distortion = self.hierarchy.hierarchy_distortion(embedding);
        let pc_ratio = self.hierarchy.parent_child_ratio(embedding);

        self.analysis_count += 1;

        HierarchyAnalysis {
            root_index: root_idx,
            num_leaves: leaves.len(),
            mean_depth: depths.iter().sum::<f64>() / depths.len().max(1) as f64,
            max_depth: depths.iter().cloned().fold(0.0f64, |a, b| a.max(b)),
            distortion,
            parent_child_correlation: pc_ratio,
        }
    }

    /// Full hyperbolic analysis
    pub fn analyze_embeddings(&mut self, euclidean_embeddings: &[Vec<f64>]) -> FullAnalysis {
        let hyp_embedding = self.project_embeddings(euclidean_embeddings, "exponential");

        let norms = hyp_embedding.norms();
        let centroid = self.compute_centroid(&hyp_embedding);

        let hierarchy_info = self.analyze_hierarchy(&hyp_embedding);
        let anomaly = self.anomaly_detector.detect(&hyp_embedding);

        let mean_norm = norms.iter().sum::<f64>() / norms.len().max(1) as f64;
        let norm_var = norms.iter().map(|&n| (n - mean_norm).powi(2)).sum::<f64>()
            / norms.len().max(1) as f64;

        let metrics = HyperbolicMetrics {
            mean_norm,
            norm_variance: norm_var,
            hierarchy_depth: hierarchy_info.mean_depth,
            boundary_proximity: norms.iter().cloned().fold(0.0f64, |a, b| a.max(b)),
            centroid_distance: PoincareBall::norm(&centroid),
            distortion_score: hierarchy_info.distortion,
        };

        FullAnalysis {
            metrics,
            hierarchy: hierarchy_info,
            anomaly,
            num_points: hyp_embedding.points.len(),
        }
    }

    /// Get analysis count
    pub fn get_stats(&self) -> EngineStats {
        EngineStats {
            analyses_performed: self.analysis_count,
            curvature: -self.ball.c,
        }
    }
}

/// Hierarchy analysis result
#[derive(Debug, Clone)]
pub struct HierarchyAnalysis {
    pub root_index: usize,
    pub num_leaves: usize,
    pub mean_depth: f64,
    pub max_depth: f64,
    pub distortion: f64,
    pub parent_child_correlation: f64,
}

/// Full analysis result
#[derive(Debug, Clone)]
pub struct FullAnalysis {
    pub metrics: HyperbolicMetrics,
    pub hierarchy: HierarchyAnalysis,
    pub anomaly: HyperbolicAnomaly,
    pub num_points: usize,
}

/// Engine statistics
#[derive(Debug, Clone)]
pub struct EngineStats {
    pub analyses_performed: usize,
    pub curvature: f64,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_poincare_ball_distance() {
        let ball = PoincareBall::new(1.0);

        // Origin to point
        let origin = vec![0.0, 0.0];
        let point = vec![0.5, 0.0];

        let dist = ball.distance(&origin, &point);
        assert!(dist > 0.0);

        // Same point
        let dist_same = ball.distance(&point, &point);
        assert!(dist_same < 0.01);
    }

    #[test]
    fn test_mobius_add_identity() {
        let ball = PoincareBall::new(1.0);

        let origin = vec![0.0, 0.0];
        let point = vec![0.3, 0.4];

        // x ⊕ 0 = x
        let result = ball.mobius_add(&point, &origin);
        assert!((result[0] - point[0]).abs() < 0.01);
        assert!((result[1] - point[1]).abs() < 0.01);
    }

    #[test]
    fn test_exp_log_map_inverse() {
        let ball = PoincareBall::new(1.0);

        let x = vec![0.1, 0.2];
        let y = vec![0.3, 0.1];

        // log_x(y) -> v, then exp_x(v) should ≈ y
        let log_xy = ball.log_map(&x, &y);
        let exp_result = ball.exp_map(&x, &log_xy);

        assert!((exp_result[0] - y[0]).abs() < 0.05);
        assert!((exp_result[1] - y[1]).abs() < 0.05);
    }

    #[test]
    fn test_frechet_mean_single() {
        let ball = PoincareBall::new(1.0);

        let points = vec![vec![0.3, 0.4]];
        let mean = ball.frechet_mean(&points, 100, 1e-6);

        assert_eq!(mean.len(), 2);
        assert!((mean[0] - 0.3).abs() < 0.01);
    }

    #[test]
    fn test_frechet_mean_symmetric() {
        let ball = PoincareBall::new(1.0);

        // Symmetric points should have mean near origin
        let points = vec![
            vec![0.3, 0.0],
            vec![-0.3, 0.0],
            vec![0.0, 0.3],
            vec![0.0, -0.3],
        ];

        let mean = ball.frechet_mean(&points, 100, 1e-6);
        let mean_norm = PoincareBall::norm(&mean);

        assert!(mean_norm < 0.1);
    }

    #[test]
    fn test_hierarchy_distortion() {
        let ball = PoincareBall::new(1.0);
        let analyzer = HierarchyAnalyzer::new(ball);

        // Well-ordered hierarchy
        let embedding = HyperbolicEmbedding {
            points: vec![
                vec![0.1, 0.0],
                vec![0.3, 0.0],
                vec![0.5, 0.0],
                vec![0.7, 0.0],
                vec![0.9, 0.0],
            ],
            curvature: -1.0,
        };

        let distortion = analyzer.hierarchy_distortion(&embedding);
        assert!(distortion < 0.2);
    }

    #[test]
    fn test_anomaly_detection_normal() {
        let ball = PoincareBall::new(1.0);
        let detector = HyperbolicAnomalyDetector::new(ball);

        let embedding = HyperbolicEmbedding {
            points: vec![
                vec![0.2, 0.1],
                vec![0.4, 0.2],
                vec![0.6, 0.3],
            ],
            curvature: -1.0,
        };

        let anomaly = detector.detect(&embedding);
        assert!(!anomaly.is_anomalous);
    }

    #[test]
    fn test_anomaly_detection_boundary_clustering() {
        let ball = PoincareBall::new(1.0);
        let detector = HyperbolicAnomalyDetector::new(ball);

        // All points near boundary
        let embedding = HyperbolicEmbedding {
            points: vec![
                vec![0.96, 0.0],
                vec![0.97, 0.0],
                vec![0.98, 0.0],
                vec![0.96, 0.1],
                vec![0.95, 0.2],
            ],
            curvature: -1.0,
        };

        let anomaly = detector.detect(&embedding);
        assert!(anomaly.is_anomalous);
        assert!(anomaly.anomaly_score > 0.0);
    }

    #[test]
    fn test_projection_simple() {
        let ball = PoincareBall::new(1.0);
        let projector = EuclideanToHyperbolic::new(ball);

        let euclidean = vec![
            vec![1.0, 2.0],
            vec![3.0, 4.0],
            vec![5.0, 6.0],
        ];

        let hyp = projector.project_simple(&euclidean);

        assert_eq!(hyp.points.len(), 3);
        for p in &hyp.points {
            assert!(PoincareBall::norm(p) < 1.0);
        }
    }

    #[test]
    fn test_projection_exponential() {
        let ball = PoincareBall::new(1.0);
        let projector = EuclideanToHyperbolic::new(ball);

        let euclidean = vec![
            vec![1.0, 0.0],
            vec![0.0, 1.0],
            vec![-1.0, 0.0],
        ];

        let hyp = projector.project_exponential(&euclidean, 0.1);

        assert_eq!(hyp.points.len(), 3);
        for p in &hyp.points {
            assert!(PoincareBall::norm(p) < 1.0);
        }
    }

    #[test]
    fn test_full_engine_analyze() {
        let mut engine = HyperbolicGeometryEngine::new(1.0);

        let embeddings = vec![
            vec![0.1, 0.2, 0.3],
            vec![0.4, 0.5, 0.6],
            vec![0.7, 0.8, 0.9],
            vec![1.0, 1.1, 1.2],
        ];

        let analysis = engine.analyze_embeddings(&embeddings);

        assert_eq!(analysis.num_points, 4);
        assert!(analysis.metrics.mean_norm > 0.0);
        assert!(analysis.hierarchy.root_index < 4);
    }

    #[test]
    fn test_engine_stats() {
        let mut engine = HyperbolicGeometryEngine::new(1.0);

        let embeddings = vec![vec![0.1, 0.2]];
        engine.analyze_embeddings(&embeddings);
        engine.analyze_embeddings(&embeddings);

        let stats = engine.get_stats();
        assert_eq!(stats.analyses_performed, 2);
    }
}
