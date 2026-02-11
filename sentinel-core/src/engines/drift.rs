//! Semantic Drift Detector - Embedding-Based Attack Detection
//!
//! Detects semantic manipulation through embedding analysis:
//! - Embedding distance monitoring
//! - Semantic shift detection  
//! - Context drift analysis
//! - Adversarial perturbation detection

use std::collections::{HashMap, VecDeque};
use std::time::{SystemTime, UNIX_EPOCH};

/// Types of semantic drift
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum DriftType {
    IntentShift,
    TopicDrift,
    SentimentFlip,
    AdversarialPerturbation,
    MeeaDrift,
}

impl DriftType {
    pub fn as_str(&self) -> &'static str {
        match self {
            DriftType::IntentShift => "intent_shift",
            DriftType::TopicDrift => "topic_drift",
            DriftType::SentimentFlip => "sentiment_flip",
            DriftType::AdversarialPerturbation => "adversarial_perturbation",
            DriftType::MeeaDrift => "meea_drift",
        }
    }
}

/// Point in embedding space
#[derive(Debug, Clone)]
pub struct EmbeddingPoint {
    pub vector: Vec<f64>,
    pub text: String,
    pub timestamp: f64,
    pub label: String,
}

impl EmbeddingPoint {
    pub fn new(vector: Vec<f64>, text: &str) -> Self {
        let timestamp = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|d| d.as_secs_f64())
            .unwrap_or(0.0);
        
        Self {
            vector,
            text: text.to_string(),
            timestamp,
            label: String::new(),
        }
    }

    pub fn with_label(mut self, label: &str) -> Self {
        self.label = label.to_string();
        self
    }
}

/// Result from drift detection
#[derive(Debug, Clone)]
pub struct DriftResult {
    pub is_safe: bool,
    pub drift_detected: bool,
    pub drift_type: Option<DriftType>,
    pub drift_score: f64,
    pub distance: f64,
    pub explanation: String,
    pub latency_ms: f64,
}

impl Default for DriftResult {
    fn default() -> Self {
        Self {
            is_safe: true,
            drift_detected: false,
            drift_type: None,
            drift_score: 0.0,
            distance: 0.0,
            explanation: String::new(),
            latency_ms: 0.0,
        }
    }
}

/// Embedding vector analyzer
pub struct EmbeddingAnalyzer;

impl EmbeddingAnalyzer {
    /// Compute cosine similarity between two vectors
    pub fn cosine_similarity(v1: &[f64], v2: &[f64]) -> f64 {
        if v1.len() != v2.len() || v1.is_empty() {
            return 0.0;
        }

        let dot: f64 = v1.iter().zip(v2.iter()).map(|(a, b)| a * b).sum();
        let mag1 = Self::magnitude(v1);
        let mag2 = Self::magnitude(v2);

        if mag1 == 0.0 || mag2 == 0.0 {
            return 0.0;
        }

        dot / (mag1 * mag2)
    }

    /// Compute Euclidean distance
    pub fn euclidean_distance(v1: &[f64], v2: &[f64]) -> f64 {
        if v1.len() != v2.len() {
            return f64::INFINITY;
        }

        v1.iter()
            .zip(v2.iter())
            .map(|(a, b)| (a - b).powi(2))
            .sum::<f64>()
            .sqrt()
    }

    /// Compute vector magnitude
    pub fn magnitude(v: &[f64]) -> f64 {
        v.iter().map(|x| x.powi(2)).sum::<f64>().sqrt()
    }

    /// Normalize vector to unit length
    pub fn normalize(v: &[f64]) -> Vec<f64> {
        let mag = Self::magnitude(v);
        if mag == 0.0 {
            return v.to_vec();
        }
        v.iter().map(|x| x / mag).collect()
    }
}

/// Manages baseline embeddings for comparison
pub struct BaselineManager {
    baselines: HashMap<String, EmbeddingPoint>,
    history: HashMap<String, VecDeque<EmbeddingPoint>>,
    window_size: usize,
}

impl Default for BaselineManager {
    fn default() -> Self {
        Self::new(10)
    }
}

impl BaselineManager {
    pub fn new(window_size: usize) -> Self {
        Self {
            baselines: HashMap::new(),
            history: HashMap::new(),
            window_size,
        }
    }

    /// Set baseline for a key
    pub fn set_baseline(&mut self, key: &str, point: EmbeddingPoint) {
        self.baselines.insert(key.to_string(), point);
    }

    /// Get baseline for key
    pub fn get_baseline(&self, key: &str) -> Option<&EmbeddingPoint> {
        self.baselines.get(key)
    }

    /// Add point to history
    pub fn add_to_history(&mut self, key: &str, point: EmbeddingPoint) {
        let history = self.history.entry(key.to_string()).or_insert_with(VecDeque::new);
        history.push_back(point);
        while history.len() > self.window_size {
            history.pop_front();
        }
    }

    /// Get history for key
    pub fn get_history(&self, key: &str) -> Option<&VecDeque<EmbeddingPoint>> {
        self.history.get(key)
    }

    /// Get average embedding from history
    pub fn get_average_embedding(&self, key: &str) -> Option<Vec<f64>> {
        let history = self.history.get(key)?;
        if history.is_empty() {
            return None;
        }

        let dim = history.front()?.vector.len();
        let mut avg = vec![0.0; dim];
        
        for point in history {
            for (i, &v) in point.vector.iter().enumerate() {
                if i < dim {
                    avg[i] += v;
                }
            }
        }

        let n = history.len() as f64;
        for v in &mut avg {
            *v /= n;
        }

        Some(avg)
    }
}

/// Classifies types of semantic drift
pub struct DriftClassifier {
    intent_threshold: f64,
    topic_threshold: f64,
    perturbation_threshold: f64,
}

impl Default for DriftClassifier {
    fn default() -> Self {
        Self::new(0.3, 0.4, 0.1)
    }
}

impl DriftClassifier {
    pub fn new(intent_threshold: f64, topic_threshold: f64, perturbation_threshold: f64) -> Self {
        Self {
            intent_threshold,
            topic_threshold,
            perturbation_threshold,
        }
    }

    /// Classify drift type
    /// Returns (is_drift, drift_type, severity)
    pub fn classify(
        &self,
        baseline: &EmbeddingPoint,
        current: &EmbeddingPoint,
        similarity: f64,
    ) -> (bool, Option<DriftType>, f64) {
        let drift_score = 1.0 - similarity;
        let text_sim = Self::text_similarity(&baseline.text, &current.text);

        // Adversarial perturbation: high text similarity but low embedding similarity
        if text_sim > 0.8 && drift_score > self.perturbation_threshold {
            return (true, Some(DriftType::AdversarialPerturbation), drift_score * 2.0);
        }

        // Intent shift: significant embedding drift with some text overlap
        if drift_score > self.intent_threshold && text_sim > 0.2 && text_sim < 0.8 {
            return (true, Some(DriftType::IntentShift), drift_score);
        }

        // Topic drift: large drift with little text overlap
        if drift_score > self.topic_threshold && text_sim < 0.3 {
            return (true, Some(DriftType::TopicDrift), drift_score);
        }

        // MEEA drift: very high drift
        if drift_score > 0.7 {
            return (true, Some(DriftType::MeeaDrift), drift_score);
        }

        (false, None, drift_score)
    }

    /// Simple text similarity (word overlap / Jaccard)
    fn text_similarity(t1: &str, t2: &str) -> f64 {
        let t1_lower = t1.to_lowercase();
        let t2_lower = t2.to_lowercase();
        
        let words1: std::collections::HashSet<_> = t1_lower
            .split_whitespace()
            .filter(|w| w.len() > 2)
            .collect();
        let words2: std::collections::HashSet<_> = t2_lower
            .split_whitespace()
            .filter(|w| w.len() > 2)
            .collect();

        if words1.is_empty() || words2.is_empty() {
            return 0.0;
        }

        let intersection = words1.intersection(&words2).count();
        let union = words1.union(&words2).count();

        if union == 0 {
            return 0.0;
        }

        intersection as f64 / union as f64
    }
}

/// Main Semantic Drift Detector Engine
pub struct DriftDetector {
    baseline_manager: BaselineManager,
    classifier: DriftClassifier,
    drift_threshold: f64,
    detections_count: usize,
}

impl Default for DriftDetector {
    fn default() -> Self {
        Self::new(0.7)
    }
}

impl DriftDetector {
    pub fn new(drift_threshold: f64) -> Self {
        Self {
            baseline_manager: BaselineManager::default(),
            classifier: DriftClassifier::default(),
            drift_threshold,
            detections_count: 0,
        }
    }

    /// Set baseline embedding for a session/context
    pub fn set_baseline(&mut self, session_id: &str, embedding: Vec<f64>, text: &str) {
        let point = EmbeddingPoint::new(embedding, text);
        self.baseline_manager.set_baseline(session_id, point);
    }

    /// Detect drift from baseline
    pub fn detect(&mut self, session_id: &str, embedding: Vec<f64>, text: &str) -> DriftResult {
        let start = std::time::Instant::now();
        let current = EmbeddingPoint::new(embedding, text);

        // Get baseline
        let baseline = match self.baseline_manager.get_baseline(session_id) {
            Some(b) => b,
            None => {
                // No baseline - set current as baseline and return safe
                self.baseline_manager.set_baseline(session_id, current.clone());
                return DriftResult {
                    is_safe: true,
                    explanation: "No baseline - established current as baseline".to_string(),
                    latency_ms: start.elapsed().as_secs_f64() * 1000.0,
                    ..Default::default()
                };
            }
        };

        // Compute similarity
        let similarity = EmbeddingAnalyzer::cosine_similarity(&baseline.vector, &current.vector);
        let distance = EmbeddingAnalyzer::euclidean_distance(&baseline.vector, &current.vector);

        // Classify drift
        let (is_drift, drift_type, drift_score) = 
            self.classifier.classify(baseline, &current, similarity);

        // Add to history
        self.baseline_manager.add_to_history(session_id, current);

        // Determine if safe
        let is_safe = !is_drift || similarity >= self.drift_threshold;

        if is_drift {
            self.detections_count += 1;
        }

        let explanation = if is_drift {
            format!(
                "Detected {:?} with score {:.3}. Similarity: {:.3}",
                drift_type.as_ref().map(|d| d.as_str()).unwrap_or("unknown"),
                drift_score,
                similarity
            )
        } else {
            format!("No significant drift detected. Similarity: {:.3}", similarity)
        };

        DriftResult {
            is_safe,
            drift_detected: is_drift,
            drift_type,
            drift_score,
            distance,
            explanation,
            latency_ms: start.elapsed().as_secs_f64() * 1000.0,
        }
    }

    /// Get detector statistics
    pub fn get_stats(&self) -> DetectorStats {
        DetectorStats {
            baselines_count: self.baseline_manager.baselines.len(),
            detections_count: self.detections_count,
            drift_threshold: self.drift_threshold,
        }
    }
}

/// Detector statistics
#[derive(Debug, Clone)]
pub struct DetectorStats {
    pub baselines_count: usize,
    pub detections_count: usize,
    pub drift_threshold: f64,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_cosine_similarity_same() {
        let v = vec![1.0, 2.0, 3.0];
        let sim = EmbeddingAnalyzer::cosine_similarity(&v, &v);
        assert!((sim - 1.0).abs() < 0.001);
    }

    #[test]
    fn test_cosine_similarity_orthogonal() {
        let v1 = vec![1.0, 0.0];
        let v2 = vec![0.0, 1.0];
        let sim = EmbeddingAnalyzer::cosine_similarity(&v1, &v2);
        assert!(sim.abs() < 0.001);
    }

    #[test]
    fn test_euclidean_distance() {
        let v1 = vec![0.0, 0.0];
        let v2 = vec![3.0, 4.0];
        let dist = EmbeddingAnalyzer::euclidean_distance(&v1, &v2);
        assert!((dist - 5.0).abs() < 0.001);
    }

    #[test]
    fn test_magnitude() {
        let v = vec![3.0, 4.0];
        let mag = EmbeddingAnalyzer::magnitude(&v);
        assert!((mag - 5.0).abs() < 0.001);
    }

    #[test]
    fn test_normalize() {
        let v = vec![3.0, 4.0];
        let norm = EmbeddingAnalyzer::normalize(&v);
        assert!((EmbeddingAnalyzer::magnitude(&norm) - 1.0).abs() < 0.001);
    }

    #[test]
    fn test_baseline_manager_set_get() {
        let mut manager = BaselineManager::default();
        let point = EmbeddingPoint::new(vec![1.0, 2.0], "test");
        manager.set_baseline("session1", point);
        
        assert!(manager.get_baseline("session1").is_some());
        assert!(manager.get_baseline("session2").is_none());
    }

    #[test]
    fn test_baseline_manager_history() {
        let mut manager = BaselineManager::new(3);
        
        for i in 0..5 {
            let point = EmbeddingPoint::new(vec![i as f64], &format!("text{}", i));
            manager.add_to_history("key", point);
        }

        let history = manager.get_history("key").unwrap();
        assert_eq!(history.len(), 3); // Window size
    }

    #[test]
    fn test_drift_classifier_no_drift() {
        let classifier = DriftClassifier::default();
        let baseline = EmbeddingPoint::new(vec![1.0, 0.0], "hello world");
        let current = EmbeddingPoint::new(vec![0.99, 0.1], "hello world");
        
        let (is_drift, _, _) = classifier.classify(&baseline, &current, 0.99);
        assert!(!is_drift);
    }

    #[test]
    fn test_drift_classifier_intent_shift() {
        let classifier = DriftClassifier::default();
        let baseline = EmbeddingPoint::new(vec![1.0, 0.0], "help me with code");
        let current = EmbeddingPoint::new(vec![0.0, 1.0], "help me bypass safety");
        
        let (is_drift, drift_type, _) = classifier.classify(&baseline, &current, 0.3);
        assert!(is_drift);
        assert!(matches!(drift_type, Some(DriftType::IntentShift) | Some(DriftType::TopicDrift)));
    }

    #[test]
    fn test_detector_no_baseline() {
        let mut detector = DriftDetector::default();
        let result = detector.detect("session1", vec![1.0, 2.0], "test");
        
        assert!(result.is_safe);
        assert!(!result.drift_detected);
    }

    #[test]
    fn test_detector_with_baseline() {
        let mut detector = DriftDetector::default();
        detector.set_baseline("session1", vec![1.0, 0.0], "baseline text");
        
        let result = detector.detect("session1", vec![0.9, 0.1], "similar text");
        assert!(result.is_safe);
    }

    #[test]
    fn test_detector_stats() {
        let mut detector = DriftDetector::default();
        detector.set_baseline("s1", vec![1.0], "test");
        detector.set_baseline("s2", vec![2.0], "test2");
        
        let stats = detector.get_stats();
        assert_eq!(stats.baselines_count, 2);
    }
}
