//! Anomaly Detection Engine (VAE-style)
//!
//! Provides anomaly detection using latent space analysis.
//! When built without the `ml` feature, uses statistical methods.

use super::embedding::{CharFreqEmbedder, EmbeddingProvider, cosine_similarity, euclidean_distance};
use std::collections::VecDeque;

/// Anomaly detection result
#[derive(Debug, Clone)]
pub struct AnomalyResult {
    pub is_anomaly: bool,
    pub anomaly_score: f64,
    pub reconstruction_error: f64,
    pub latent_distance: f64,
}

impl Default for AnomalyResult {
    fn default() -> Self {
        Self {
            is_anomaly: false,
            anomaly_score: 0.0,
            reconstruction_error: 0.0,
            latent_distance: 0.0,
        }
    }
}

/// Statistical baseline for anomaly detection
pub struct BaselineStats {
    mean: Vec<f64>,
    std: Vec<f64>,
    count: usize,
}

impl BaselineStats {
    pub fn new(dimension: usize) -> Self {
        Self {
            mean: vec![0.0; dimension],
            std: vec![1.0; dimension],
            count: 0,
        }
    }

    /// Update baseline with new sample
    pub fn update(&mut self, sample: &[f64]) {
        if sample.len() != self.mean.len() {
            return;
        }

        self.count += 1;
        let n = self.count as f64;

        for (i, &value) in sample.iter().enumerate() {
            let delta = value - self.mean[i];
            self.mean[i] += delta / n;
            // Running variance using Welford's algorithm
            if self.count > 1 {
                let delta2 = value - self.mean[i];
                let variance = ((self.std[i].powi(2) * (n - 1.0)) + delta * delta2) / n;
                self.std[i] = variance.sqrt().max(0.001);
            }
        }
    }

    /// Compute z-score for a sample
    pub fn z_score(&self, sample: &[f64]) -> f64 {
        if sample.len() != self.mean.len() || self.count < 2 {
            return 0.0;
        }

        let mut sum_squared: f64 = 0.0;
        for (i, &value) in sample.iter().enumerate() {
            let z = (value - self.mean[i]) / self.std[i].max(0.001);
            sum_squared += z.powi(2);
        }

        (sum_squared / sample.len() as f64).sqrt()
    }
}

/// VAE-style Anomaly Detector
pub struct AnomalyGuard {
    embedder: Box<dyn EmbeddingProvider>,
    baseline: BaselineStats,
    history: VecDeque<Vec<f64>>,
    max_history: usize,
    threshold: f64,
}

impl Default for AnomalyGuard {
    fn default() -> Self {
        Self::new()
    }
}

impl AnomalyGuard {
    pub fn new() -> Self {
        let embedder = Box::new(CharFreqEmbedder::new());
        let dimension = embedder.dimension();
        
        Self {
            embedder,
            baseline: BaselineStats::new(dimension),
            history: VecDeque::new(),
            max_history: 1000,
            threshold: 3.0, // z-score threshold
        }
    }

    /// Add sample to baseline
    pub fn add_baseline_sample(&mut self, text: &str) {
        let embedding = self.embedder.embed(text);
        self.baseline.update(&embedding.vector);
        
        if self.history.len() >= self.max_history {
            self.history.pop_front();
        }
        self.history.push_back(embedding.vector);
    }

    /// Compute local density (average distance to k nearest neighbors)
    fn local_density(&self, embedding: &[f64], k: usize) -> f64 {
        if self.history.is_empty() {
            return 0.0;
        }

        let mut distances: Vec<f64> = self.history.iter()
            .map(|h| euclidean_distance(embedding, h))
            .collect();
        distances.sort_by(|a, b| a.partial_cmp(b).unwrap());

        let k = k.min(distances.len());
        distances[..k].iter().sum::<f64>() / k as f64
    }

    /// Compute reconstruction-style error (distance from mean)
    fn reconstruction_error(&self, embedding: &[f64]) -> f64 {
        euclidean_distance(embedding, &self.baseline.mean)
    }

    /// Analyze text for anomalies
    pub fn analyze(&self, text: &str) -> AnomalyResult {
        let embedding = self.embedder.embed(text);
        
        let z_score = self.baseline.z_score(&embedding.vector);
        let reconstruction = self.reconstruction_error(&embedding.vector);
        let density = self.local_density(&embedding.vector, 5);

        // Combined anomaly score
        let anomaly_score = (z_score + reconstruction + density) / 3.0;
        let is_anomaly = z_score > self.threshold;

        AnomalyResult {
            is_anomaly,
            anomaly_score,
            reconstruction_error: reconstruction,
            latent_distance: density,
        }
    }

    /// Get baseline statistics
    pub fn baseline_count(&self) -> usize {
        self.baseline.count
    }
}

/// Isolation Forest-style detector (simplified)
pub struct IsolationGuard {
    embedder: Box<dyn EmbeddingProvider>,
    samples: Vec<Vec<f64>>,
    max_samples: usize,
}

impl Default for IsolationGuard {
    fn default() -> Self {
        Self::new()
    }
}

impl IsolationGuard {
    pub fn new() -> Self {
        Self {
            embedder: Box::new(CharFreqEmbedder::new()),
            samples: Vec::new(),
            max_samples: 500,
        }
    }

    /// Add training sample
    pub fn add_sample(&mut self, text: &str) {
        if self.samples.len() >= self.max_samples {
            self.samples.remove(0);
        }
        let embedding = self.embedder.embed(text);
        self.samples.push(embedding.vector);
    }

    /// Compute isolation score (simplified)
    pub fn isolation_score(&self, text: &str) -> f64 {
        if self.samples.is_empty() {
            return 0.5;
        }

        let embedding = self.embedder.embed(text);
        
        // Count how many samples are "close" (within threshold)
        let close_count = self.samples.iter()
            .filter(|s| cosine_similarity(&embedding.vector, s) > 0.8)
            .count();

        // Higher isolation = fewer close neighbors
        1.0 - (close_count as f64 / self.samples.len() as f64)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_baseline_stats_update() {
        let mut stats = BaselineStats::new(3);
        stats.update(&[1.0, 2.0, 3.0]);
        stats.update(&[2.0, 3.0, 4.0]);
        assert_eq!(stats.count, 2);
    }

    #[test]
    fn test_baseline_z_score() {
        let mut stats = BaselineStats::new(2);
        stats.update(&[0.0, 0.0]);
        stats.update(&[1.0, 1.0]);
        stats.update(&[0.5, 0.5]);
        
        let z = stats.z_score(&[0.5, 0.5]);
        assert!(z < 2.0); // Should be close to mean
    }

    #[test]
    fn test_anomaly_guard_creation() {
        let guard = AnomalyGuard::new();
        assert_eq!(guard.baseline_count(), 0);
    }

    #[test]
    fn test_add_baseline() {
        let mut guard = AnomalyGuard::new();
        guard.add_baseline_sample("Normal text sample");
        guard.add_baseline_sample("Another normal sample");
        assert_eq!(guard.baseline_count(), 2);
    }

    #[test]
    fn test_anomaly_analysis() {
        let mut guard = AnomalyGuard::new();
        // Add baseline samples
        for _ in 0..10 {
            guard.add_baseline_sample("This is a normal message");
        }
        
        let result = guard.analyze("This is a normal message too");
        assert!(result.anomaly_score >= 0.0);
    }

    #[test]
    fn test_reconstruction_error() {
        let guard = AnomalyGuard::new();
        let embedding = guard.embedder.embed("Test");
        let error = guard.reconstruction_error(&embedding.vector);
        assert!(error >= 0.0);
    }

    #[test]
    fn test_isolation_guard() {
        let mut guard = IsolationGuard::new();
        guard.add_sample("Normal text");
        guard.add_sample("Another normal text");
        
        let score = guard.isolation_score("Normal text");
        assert!(score >= 0.0 && score <= 1.0);
    }

    #[test]
    fn test_isolation_empty() {
        let guard = IsolationGuard::new();
        let score = guard.isolation_score("Any text");
        assert!((score - 0.5).abs() < 0.01); // Default score
    }

    #[test]
    fn test_local_density() {
        let mut guard = AnomalyGuard::new();
        guard.add_baseline_sample("Sample one");
        guard.add_baseline_sample("Sample two");
        
        let embedding = guard.embedder.embed("Sample three");
        let density = guard.local_density(&embedding.vector, 2);
        assert!(density >= 0.0);
    }
}
