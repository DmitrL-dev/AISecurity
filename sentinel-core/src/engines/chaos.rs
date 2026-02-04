//! Chaos Theory Engine - Lyapunov Exponents and Attractor Analysis
//!
//! Detects chaotic vs structured behavior in user interactions.
//! Uses:
//! - Lyapunov exponents (sensitivity to initial conditions)
//! - Phase space reconstruction (Takens' embedding)
//! - Correlation dimension for attractor classification

use std::collections::HashMap;

/// Result of Lyapunov exponent calculation
#[derive(Debug, Clone)]
pub struct LyapunovResult {
    pub exponent: f64,
    pub is_chaotic: bool,
    pub stability_score: f64,
    pub classification: String,
}

/// Result of phase space analysis
#[derive(Debug, Clone)]
pub struct PhaseSpaceResult {
    pub embedding_dimension: usize,
    pub correlation_dimension: f64,
    pub attractor_type: String,
    pub predictability: f64,
}

/// User behavior analysis result
#[derive(Debug, Clone)]
pub struct BehaviorAnalysis {
    pub status: String,
    pub data_points: usize,
    pub lyapunov: Option<LyapunovResult>,
    pub phase_space: Option<PhaseSpaceResult>,
    pub behavior_type: String,
    pub risk_modifier: i32,
}

/// Regime change detection result
#[derive(Debug, Clone)]
pub struct RegimeChange {
    pub detected: bool,
    pub early_exponent: f64,
    pub recent_exponent: f64,
    pub change_magnitude: f64,
}

/// Chaos Theory Engine for behavioral analysis
pub struct ChaosTheoryEngine {
    user_time_series: HashMap<String, Vec<Vec<f64>>>,
    buffer_size: usize,
    lyapunov_chaos_threshold: f64,
    lyapunov_stable_threshold: f64,
}

impl Default for ChaosTheoryEngine {
    fn default() -> Self {
        Self::new()
    }
}

impl ChaosTheoryEngine {
    pub fn new() -> Self {
        Self {
            user_time_series: HashMap::new(),
            buffer_size: 100,
            lyapunov_chaos_threshold: 0.1,
            lyapunov_stable_threshold: -0.1,
        }
    }

    /// Record user interaction for time series analysis
    pub fn record_interaction(&mut self, user_id: &str, features: &[f64]) {
        let ts = self.user_time_series
            .entry(user_id.to_string())
            .or_insert_with(Vec::new);
        
        ts.push(features.to_vec());
        
        // Maintain buffer size
        if ts.len() > self.buffer_size {
            ts.remove(0);
        }
    }

    /// Calculate largest Lyapunov exponent from time series
    pub fn calculate_lyapunov(&self, time_series: &[Vec<f64>]) -> LyapunovResult {
        let n_points = time_series.len();
        
        if n_points < 10 {
            return LyapunovResult {
                exponent: 0.0,
                is_chaotic: false,
                stability_score: 50.0,
                classification: "insufficient_data".to_string(),
            };
        }

        let mut lyapunov_sum = 0.0;
        let mut count = 0;

        for i in 0..n_points - 1 {
            // Find nearest neighbor (not itself or adjacent)
            let mut min_dist = f64::MAX;
            let mut min_idx: Option<usize> = None;

            for j in 0..n_points {
                if (i as i32 - j as i32).abs() > 1 {
                    let dist = self.euclidean_distance(&time_series[i], &time_series[j]);
                    if dist > 0.0 && dist < min_dist {
                        min_dist = dist;
                        min_idx = Some(j);
                    }
                }
            }

            if let Some(idx) = min_idx {
                if idx > 0 && idx < n_points - 1 && i < n_points - 1 {
                    // Calculate divergence
                    let next_dist = self.euclidean_distance(
                        &time_series[i + 1],
                        &time_series[idx + 1],
                    );

                    if min_dist > 0.0 && next_dist > 0.0 {
                        lyapunov_sum += (next_dist / min_dist).ln();
                        count += 1;
                    }
                }
            }
        }

        let exponent = if count > 0 {
            lyapunov_sum / count as f64
        } else {
            0.0
        };

        let (classification, is_chaotic, stability_score) = if exponent > self.lyapunov_chaos_threshold {
            ("chaotic".to_string(), true, (50.0 - exponent * 100.0).max(0.0))
        } else if exponent < self.lyapunov_stable_threshold {
            ("stable".to_string(), false, (50.0 - exponent * 100.0).min(100.0))
        } else {
            ("edge_of_chaos".to_string(), false, 50.0)
        };

        LyapunovResult {
            exponent,
            is_chaotic,
            stability_score,
            classification,
        }
    }

    /// Reconstruct phase space using Takens' embedding theorem
    pub fn analyze_phase_space(
        &self,
        time_series: &[f64],
        embedding_dim: usize,
        delay: usize,
    ) -> PhaseSpaceResult {
        let min_length = embedding_dim * delay + 10;
        
        if time_series.len() < min_length {
            return PhaseSpaceResult {
                embedding_dimension: embedding_dim,
                correlation_dimension: 0.0,
                attractor_type: "unknown".to_string(),
                predictability: 0.5,
            };
        }

        // Phase space reconstruction
        let n_vectors = time_series.len() - (embedding_dim - 1) * delay;
        let mut embedded: Vec<Vec<f64>> = Vec::with_capacity(n_vectors);

        for i in 0..n_vectors {
            let mut vec = Vec::with_capacity(embedding_dim);
            for j in 0..embedding_dim {
                vec.push(time_series[i + j * delay]);
            }
            embedded.push(vec);
        }

        // Calculate pairwise distances (limited sample)
        let sample_size = 100.min(embedded.len());
        let mut distances: Vec<f64> = Vec::new();

        for i in 0..sample_size {
            for j in (i + 1)..sample_size {
                let d = self.euclidean_distance(&embedded[i], &embedded[j]);
                if d > 0.0 {
                    distances.push(d);
                }
            }
        }

        if distances.is_empty() {
            return PhaseSpaceResult {
                embedding_dimension: embedding_dim,
                correlation_dimension: 0.0,
                attractor_type: "point".to_string(),
                predictability: 1.0,
            };
        }

        // Estimate correlation dimension using percentiles
        distances.sort_by(|a, b| a.partial_cmp(b).unwrap());
        
        let percentile_indices = [10, 20, 30, 40, 50];
        let r_values: Vec<f64> = percentile_indices
            .iter()
            .map(|&p| {
                let idx = (distances.len() * p / 100).min(distances.len() - 1);
                distances[idx]
            })
            .collect();

        let c_values: Vec<f64> = r_values
            .iter()
            .map(|&r| {
                let count = distances.iter().filter(|&&d| d < r).count();
                count as f64 / distances.len() as f64
            })
            .collect();

        // Simple slope estimation for correlation dimension
        let correlation_dim = if c_values.len() >= 2 
            && c_values[0] > 0.0 
            && c_values.last().unwrap_or(&0.0) > &0.0 
        {
            let log_r: Vec<f64> = r_values.iter().map(|&r| r.ln()).collect();
            let log_c: Vec<f64> = c_values.iter().map(|&c| c.max(1e-10).ln()).collect();
            
            // Linear regression slope
            self.linear_regression_slope(&log_r, &log_c)
        } else {
            0.0
        };

        // Classify attractor
        let (attractor_type, predictability) = if correlation_dim < 0.5 {
            ("point".to_string(), 0.95)
        } else if correlation_dim < 2.0 {
            ("periodic".to_string(), 0.7)
        } else {
            ("strange".to_string(), 0.3)
        };

        PhaseSpaceResult {
            embedding_dimension: embedding_dim,
            correlation_dimension: correlation_dim,
            attractor_type,
            predictability,
        }
    }

    /// Full chaos analysis of user behavior
    pub fn analyze_user_behavior(&self, user_id: &str) -> BehaviorAnalysis {
        let time_series = match self.user_time_series.get(user_id) {
            Some(ts) => ts,
            None => {
                return BehaviorAnalysis {
                    status: "no_data".to_string(),
                    data_points: 0,
                    lyapunov: None,
                    phase_space: None,
                    behavior_type: "unknown".to_string(),
                    risk_modifier: 0,
                };
            }
        };

        if time_series.len() < 10 {
            return BehaviorAnalysis {
                status: "insufficient_data".to_string(),
                data_points: time_series.len(),
                lyapunov: None,
                phase_space: None,
                behavior_type: "unknown".to_string(),
                risk_modifier: 0,
            };
        }

        // Lyapunov analysis
        let lyapunov = self.calculate_lyapunov(time_series);

        // Phase space analysis (first feature dimension)
        let first_dim: Vec<f64> = time_series.iter().map(|ts| ts.first().copied().unwrap_or(0.0)).collect();
        let phase_space = self.analyze_phase_space(&first_dim, 3, 1);

        // Combined assessment
        let (behavior_type, risk_modifier) = if lyapunov.is_chaotic {
            ("unpredictable".to_string(), 20)
        } else if lyapunov.classification == "edge_of_chaos" {
            ("transitional".to_string(), 10)
        } else {
            ("predictable".to_string(), 0)
        };

        BehaviorAnalysis {
            status: "analyzed".to_string(),
            data_points: time_series.len(),
            lyapunov: Some(lyapunov),
            phase_space: Some(phase_space),
            behavior_type,
            risk_modifier,
        }
    }

    /// Detect regime change in user behavior
    pub fn detect_regime_change(&self, user_id: &str, window_size: usize) -> Option<RegimeChange> {
        let time_series = self.user_time_series.get(user_id)?;
        
        if time_series.len() < window_size * 2 {
            return None;
        }

        let early: Vec<Vec<f64>> = time_series[..window_size].to_vec();
        let recent: Vec<Vec<f64>> = time_series[time_series.len() - window_size..].to_vec();

        let early_lyapunov = self.calculate_lyapunov(&early);
        let recent_lyapunov = self.calculate_lyapunov(&recent);

        let change_magnitude = (recent_lyapunov.exponent - early_lyapunov.exponent).abs();

        Some(RegimeChange {
            detected: change_magnitude > 0.5,
            early_exponent: early_lyapunov.exponent,
            recent_exponent: recent_lyapunov.exponent,
            change_magnitude,
        })
    }

    /// Euclidean distance between two vectors
    fn euclidean_distance(&self, a: &[f64], b: &[f64]) -> f64 {
        a.iter()
            .zip(b.iter())
            .map(|(ai, bi)| (ai - bi).powi(2))
            .sum::<f64>()
            .sqrt()
    }

    /// Simple linear regression slope
    fn linear_regression_slope(&self, x: &[f64], y: &[f64]) -> f64 {
        let n = x.len() as f64;
        if n < 2.0 {
            return 0.0;
        }

        let sum_x: f64 = x.iter().sum();
        let sum_y: f64 = y.iter().sum();
        let sum_xy: f64 = x.iter().zip(y.iter()).map(|(xi, yi)| xi * yi).sum();
        let sum_x2: f64 = x.iter().map(|xi| xi * xi).sum();

        let denominator = n * sum_x2 - sum_x * sum_x;
        if denominator.abs() < 1e-10 {
            return 0.0;
        }

        (n * sum_xy - sum_x * sum_y) / denominator
    }

    /// Get engine statistics
    pub fn get_stats(&self) -> EngineStats {
        EngineStats {
            users_tracked: self.user_time_series.len(),
            total_data_points: self.user_time_series.values().map(|v| v.len()).sum(),
        }
    }
}

/// Engine statistics
#[derive(Debug, Clone)]
pub struct EngineStats {
    pub users_tracked: usize,
    pub total_data_points: usize,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_lyapunov_insufficient_data() {
        let engine = ChaosTheoryEngine::new();
        let ts: Vec<Vec<f64>> = vec![vec![1.0], vec![2.0]];
        
        let result = engine.calculate_lyapunov(&ts);
        assert_eq!(result.classification, "insufficient_data");
    }

    #[test]
    fn test_lyapunov_stable_series() {
        let engine = ChaosTheoryEngine::new();
        
        // Stable series with small variations
        let ts: Vec<Vec<f64>> = (0..20)
            .map(|i| vec![1.0 + (i as f64 * 0.01)])
            .collect();
        
        let result = engine.calculate_lyapunov(&ts);
        assert!(result.exponent.is_finite());
    }

    #[test]
    fn test_phase_space_insufficient_data() {
        let engine = ChaosTheoryEngine::new();
        let ts = vec![1.0, 2.0, 3.0];
        
        let result = engine.analyze_phase_space(&ts, 3, 1);
        assert_eq!(result.attractor_type, "unknown");
    }

    #[test]
    fn test_phase_space_point_attractor() {
        let engine = ChaosTheoryEngine::new();
        
        // Constant series -> point attractor
        let ts: Vec<f64> = vec![1.0; 50];
        
        let result = engine.analyze_phase_space(&ts, 3, 1);
        assert_eq!(result.attractor_type, "point");
        assert!(result.predictability > 0.9);
    }

    #[test]
    fn test_record_interaction() {
        let mut engine = ChaosTheoryEngine::new();
        
        for i in 0..5 {
            engine.record_interaction("user1", &[i as f64, i as f64 * 2.0]);
        }
        
        let stats = engine.get_stats();
        assert_eq!(stats.users_tracked, 1);
        assert_eq!(stats.total_data_points, 5);
    }

    #[test]
    fn test_analyze_user_no_data() {
        let engine = ChaosTheoryEngine::new();
        
        let result = engine.analyze_user_behavior("unknown_user");
        assert_eq!(result.status, "no_data");
    }

    #[test]
    fn test_analyze_user_insufficient_data() {
        let mut engine = ChaosTheoryEngine::new();
        engine.record_interaction("user1", &[1.0]);
        
        let result = engine.analyze_user_behavior("user1");
        assert_eq!(result.status, "insufficient_data");
    }

    #[test]
    fn test_analyze_user_full() {
        let mut engine = ChaosTheoryEngine::new();
        
        for i in 0..20 {
            engine.record_interaction("user1", &[i as f64, (i * 2) as f64]);
        }
        
        let result = engine.analyze_user_behavior("user1");
        assert_eq!(result.status, "analyzed");
        assert!(result.lyapunov.is_some());
        assert!(result.phase_space.is_some());
    }

    #[test]
    fn test_regime_change_insufficient() {
        let mut engine = ChaosTheoryEngine::new();
        
        for i in 0..10 {
            engine.record_interaction("user1", &[i as f64]);
        }
        
        let result = engine.detect_regime_change("user1", 20);
        assert!(result.is_none());
    }

    #[test]
    fn test_regime_change_detection() {
        let mut engine = ChaosTheoryEngine::new();
        
        // Stable period
        for i in 0..30 {
            engine.record_interaction("user1", &[(i as f64) * 0.1]);
        }
        // Chaotic period
        for i in 0..30 {
            engine.record_interaction("user1", &[(i as f64).sin() * 10.0]);
        }
        
        let result = engine.detect_regime_change("user1", 20);
        assert!(result.is_some());
    }

    #[test]
    fn test_euclidean_distance() {
        let engine = ChaosTheoryEngine::new();
        
        let a = vec![0.0, 0.0];
        let b = vec![3.0, 4.0];
        
        let dist = engine.euclidean_distance(&a, &b);
        assert!((dist - 5.0).abs() < 0.01);
    }

    #[test]
    fn test_linear_regression_slope() {
        let engine = ChaosTheoryEngine::new();
        
        let x = vec![1.0, 2.0, 3.0, 4.0, 5.0];
        let y = vec![2.0, 4.0, 6.0, 8.0, 10.0];
        
        let slope = engine.linear_regression_slope(&x, &y);
        assert!((slope - 2.0).abs() < 0.01);
    }

    #[test]
    fn test_buffer_size_limit() {
        let mut engine = ChaosTheoryEngine::new();
        
        for i in 0..150 {
            engine.record_interaction("user1", &[i as f64]);
        }
        
        let stats = engine.get_stats();
        assert_eq!(stats.total_data_points, 100); // Buffer limit
    }
}
