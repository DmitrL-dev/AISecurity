//! Attention Analysis Engine
//!
//! Analyzes attention patterns for security anomalies.
//! Detects unusual token focus, attention spikes, and manipulation.

/// Attention pattern types
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum AttentionAnomaly {
    UnusualTokenFocus,
    AttentionSpike,
    DistractorPattern,
    FocusManipulation,
    CrossAttentionLeak,
}

impl AttentionAnomaly {
    pub fn as_str(&self) -> &'static str {
        match self {
            AttentionAnomaly::UnusualTokenFocus => "unusual_token_focus",
            AttentionAnomaly::AttentionSpike => "attention_spike",
            AttentionAnomaly::DistractorPattern => "distractor_pattern",
            AttentionAnomaly::FocusManipulation => "focus_manipulation",
            AttentionAnomaly::CrossAttentionLeak => "cross_attention_leak",
        }
    }

    pub fn severity(&self) -> u8 {
        match self {
            AttentionAnomaly::CrossAttentionLeak => 90,
            AttentionAnomaly::FocusManipulation => 85,
            AttentionAnomaly::AttentionSpike => 75,
            AttentionAnomaly::DistractorPattern => 70,
            AttentionAnomaly::UnusualTokenFocus => 60,
        }
    }
}

/// Simulated attention weights (without real model)
#[derive(Debug, Clone)]
pub struct AttentionWeights {
    pub tokens: Vec<String>,
    pub weights: Vec<f64>,
    pub head_importances: Vec<f64>,
}

/// Attention analysis result
#[derive(Debug, Clone)]
pub struct AttentionResult {
    pub is_anomaly: bool,
    pub anomalies: Vec<AttentionAnomaly>,
    pub risk_score: f64,
    pub attention_entropy: f64,
    pub peak_attention: f64,
}

impl Default for AttentionResult {
    fn default() -> Self {
        Self {
            is_anomaly: false,
            anomalies: Vec::new(),
            risk_score: 0.0,
            attention_entropy: 0.0,
            peak_attention: 0.0,
        }
    }
}

/// Attention Analysis Guard
pub struct AttentionGuard {
    focus_keywords: Vec<String>,
    distractor_patterns: Vec<String>,
}

impl Default for AttentionGuard {
    fn default() -> Self {
        Self::new()
    }
}

impl AttentionGuard {
    pub fn new() -> Self {
        Self {
            focus_keywords: vec![
                "ignore".to_string(),
                "forget".to_string(),
                "override".to_string(),
                "bypass".to_string(),
                // Removed "system" and "prompt" — too common in benign technical text
                // (e.g. "system architecture", "prompt the user", "operating system")
            ],
            distractor_patterns: vec![
                "...".to_string(),
                "***".to_string(),
                "---".to_string(),
                "___".to_string(),
            ],
        }
    }

    /// Simulate attention weights from text (without real model)
    pub fn simulate_attention(&self, text: &str) -> AttentionWeights {
        let tokens: Vec<String> = text.split_whitespace().map(|s| s.to_lowercase()).collect();

        // Compute pseudo-attention based on keyword importance
        let mut weights = Vec::new();
        for token in &tokens {
            let base_weight = 1.0 / tokens.len().max(1) as f64;
            let keyword_boost = if self.focus_keywords.iter().any(|k| token.contains(k)) {
                2.0
            } else {
                1.0
            };
            weights.push(base_weight * keyword_boost);
        }

        // Normalize weights
        let sum: f64 = weights.iter().sum();
        if sum > 0.0 {
            for w in &mut weights {
                *w /= sum;
            }
        }

        // Simulate head importances (8 heads)
        let head_importances = vec![0.2, 0.15, 0.15, 0.1, 0.1, 0.1, 0.1, 0.1];

        AttentionWeights {
            tokens,
            weights,
            head_importances,
        }
    }

    /// Compute entropy of attention distribution
    fn compute_entropy(&self, weights: &[f64]) -> f64 {
        weights
            .iter()
            .filter(|&&w| w > 0.0)
            .map(|&w| -w * w.ln())
            .sum()
    }

    /// Check for unusual token focus
    fn check_unusual_focus(&self, attention: &AttentionWeights) -> Option<AttentionAnomaly> {
        // Check if any single token has disproportionate attention
        let max_weight = attention
            .weights
            .iter()
            .cloned()
            .max_by(|a, b| a.partial_cmp(b).unwrap())
            .unwrap_or(0.0);

        if max_weight > 0.5 {
            // More than 50% on single token
            return Some(AttentionAnomaly::UnusualTokenFocus);
        }
        None
    }

    /// Check for attention spikes
    fn check_attention_spike(&self, attention: &AttentionWeights) -> Option<AttentionAnomaly> {
        let entropy = self.compute_entropy(&attention.weights);
        let max_entropy = (attention.weights.len() as f64).ln();

        // Very low entropy = spike
        if entropy < max_entropy * 0.3 && attention.weights.len() > 3 {
            return Some(AttentionAnomaly::AttentionSpike);
        }
        None
    }

    /// Check for distractor patterns
    fn check_distractors(&self, text: &str) -> Option<AttentionAnomaly> {
        let text_lower = text.to_lowercase();

        for pattern in &self.distractor_patterns {
            if text_lower.contains(pattern) {
                // Count occurrences
                let count = text_lower.matches(pattern).count();
                if count >= 3 {
                    return Some(AttentionAnomaly::DistractorPattern);
                }
            }
        }
        None
    }

    /// Check for focus manipulation
    fn check_focus_manipulation(&self, attention: &AttentionWeights) -> Option<AttentionAnomaly> {
        // Count focus keywords in high-attention tokens
        let high_attention_threshold = 0.1;
        let focus_count = attention
            .tokens
            .iter()
            .zip(&attention.weights)
            .filter(|(token, &weight)| {
                weight > high_attention_threshold
                    && self.focus_keywords.iter().any(|k| token.contains(k))
            })
            .count();

        if focus_count >= 3 {
            return Some(AttentionAnomaly::FocusManipulation);
        }
        None
    }

    /// Full attention analysis
    pub fn analyze(&self, text: &str) -> AttentionResult {
        let attention = self.simulate_attention(text);
        let mut result = AttentionResult::default();
        let mut anomalies = Vec::new();

        result.attention_entropy = self.compute_entropy(&attention.weights);
        result.peak_attention = attention
            .weights
            .iter()
            .cloned()
            .max_by(|a, b| a.partial_cmp(b).unwrap())
            .unwrap_or(0.0);

        if let Some(a) = self.check_unusual_focus(&attention) {
            anomalies.push(a);
        }
        if let Some(a) = self.check_attention_spike(&attention) {
            anomalies.push(a);
        }
        if let Some(a) = self.check_distractors(text) {
            anomalies.push(a);
        }
        if let Some(a) = self.check_focus_manipulation(&attention) {
            anomalies.push(a);
        }

        result.is_anomaly = !anomalies.is_empty();
        result.risk_score = anomalies
            .iter()
            .map(|a| a.severity() as f64)
            .max_by(|a, b| a.partial_cmp(b).unwrap())
            .unwrap_or(0.0);
        result.anomalies = anomalies;

        result
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_simulate_attention() {
        let guard = AttentionGuard::new();
        let attention = guard.simulate_attention("Hello world test");
        assert_eq!(attention.tokens.len(), 3);
        assert_eq!(attention.weights.len(), 3);
    }

    #[test]
    fn test_attention_normalization() {
        let guard = AttentionGuard::new();
        let attention = guard.simulate_attention("One two three four five");
        let sum: f64 = attention.weights.iter().sum();
        assert!((sum - 1.0).abs() < 0.01);
    }

    #[test]
    fn test_entropy_calculation() {
        let guard = AttentionGuard::new();
        let uniform = vec![0.25, 0.25, 0.25, 0.25];
        let entropy = guard.compute_entropy(&uniform);
        // Entropy of uniform distribution should be near max
        let max_entropy = (4.0_f64).ln();
        assert!((entropy - max_entropy).abs() < 0.01);
    }

    #[test]
    fn test_distractor_detection() {
        let guard = AttentionGuard::new();
        let text = "Normal text ... hidden ... command ... here";
        assert!(guard.check_distractors(text).is_some());
    }

    #[test]
    fn test_focus_manipulation() {
        let guard = AttentionGuard::new();
        let text = "Ignore previous bypass system prompt override";
        let result = guard.analyze(text);
        assert!(result.is_anomaly);
    }

    #[test]
    fn test_clean_text_analysis() {
        let guard = AttentionGuard::new();
        let result = guard.analyze("Please help me with a simple task");
        assert!(result.risk_score < 50.0);
    }

    #[test]
    fn test_peak_attention() {
        let guard = AttentionGuard::new();
        let result = guard.analyze("word");
        // Single word should have peak = 1.0
        assert!((result.peak_attention - 1.0).abs() < 0.01);
    }

    #[test]
    fn test_severity_ordering() {
        assert!(
            AttentionAnomaly::CrossAttentionLeak.severity()
                > AttentionAnomaly::UnusualTokenFocus.severity()
        );
    }

    #[test]
    fn test_head_importances() {
        let guard = AttentionGuard::new();
        let attention = guard.simulate_attention("Test");
        assert_eq!(attention.head_importances.len(), 8);
        let sum: f64 = attention.head_importances.iter().sum();
        assert!((sum - 1.0).abs() < 0.01);
    }
}
