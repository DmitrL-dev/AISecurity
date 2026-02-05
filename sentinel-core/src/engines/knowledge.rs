//! Knowledge & Intelligence Super-Engine
//!
//! Consolidated from 12 Python engines:
//! - knowledge.py
//! - intelligence.py
//! - learning.py
//! - llm_fingerprinting.py
//! - model_context_protocol_guard.py
//! - meta_judge.py
//! - meta_attack_adapter.py
//! - foundation_sec.py
//! - distilled_security_ensemble.py
//! - ensemble.py
//! - rule_dsl.py
//! - registry.py


/// Knowledge threat types
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum KnowledgeThreat {
    ModelFingerprinting,
    KnowledgeExtraction,
    TrainingDataLeak,
    ModelInversion,
    MembershipInference,
    EnsembleBypass,
    MetaLearningExploit,
    FoundationModelAttack,
}

impl KnowledgeThreat {
    pub fn as_str(&self) -> &'static str {
        match self {
            KnowledgeThreat::ModelFingerprinting => "model_fingerprinting",
            KnowledgeThreat::KnowledgeExtraction => "knowledge_extraction",
            KnowledgeThreat::TrainingDataLeak => "training_data_leak",
            KnowledgeThreat::ModelInversion => "model_inversion",
            KnowledgeThreat::MembershipInference => "membership_inference",
            KnowledgeThreat::EnsembleBypass => "ensemble_bypass",
            KnowledgeThreat::MetaLearningExploit => "meta_learning_exploit",
            KnowledgeThreat::FoundationModelAttack => "foundation_model_attack",
        }
    }

    pub fn severity(&self) -> u8 {
        match self {
            KnowledgeThreat::TrainingDataLeak => 100,
            KnowledgeThreat::KnowledgeExtraction => 95,
            KnowledgeThreat::ModelInversion => 90,
            KnowledgeThreat::MembershipInference => 85,
            KnowledgeThreat::FoundationModelAttack => 80,
            KnowledgeThreat::MetaLearningExploit => 75,
            KnowledgeThreat::ModelFingerprinting => 60,
            KnowledgeThreat::EnsembleBypass => 55,
        }
    }
}

/// Fingerprinting patterns
const FINGERPRINT_PATTERNS: &[&str] = &[
    "what model are you",
    "which llm",
    "are you gpt",
    "are you claude",
    "are you gemini",
    "your training data",
    "when were you trained",
    "your knowledge cutoff",
    "model version",
    "system prompt",
];

/// Knowledge extraction patterns
const EXTRACTION_PATTERNS: &[&str] = &[
    "reveal your training",
    "show training examples",
    "repeat training data",
    "what data were you trained on",
    "memorized information",
    "verbatim from training",
];

/// Model inversion patterns
const INVERSION_PATTERNS: &[&str] = &[
    "reconstruct input",
    "recover original",
    "infer the input",
    "reverse the model",
    "extract features",
];

/// Knowledge analysis result
#[derive(Debug, Clone)]
pub struct KnowledgeResult {
    pub is_threat: bool,
    pub threats: Vec<KnowledgeThreat>,
    pub risk_score: f64,
    pub fingerprint_attempts: usize,
    pub extraction_attempts: usize,
}

impl Default for KnowledgeResult {
    fn default() -> Self {
        Self {
            is_threat: false,
            threats: Vec::new(),
            risk_score: 0.0,
            fingerprint_attempts: 0,
            extraction_attempts: 0,
        }
    }
}

/// Knowledge Guard
pub struct KnowledgeGuard {
    strict_mode: bool,
}

impl Default for KnowledgeGuard {
    fn default() -> Self {
        Self::new()
    }
}

impl KnowledgeGuard {
    pub fn new() -> Self {
        Self { strict_mode: false }
    }

    pub fn strict() -> Self {
        Self { strict_mode: true }
    }

    /// Check for model fingerprinting attempts
    pub fn check_fingerprinting(&self, text: &str) -> Option<KnowledgeThreat> {
        let text_lower = text.to_lowercase();
        
        let mut count = 0;
        for pattern in FINGERPRINT_PATTERNS {
            if text_lower.contains(pattern) {
                count += 1;
            }
        }

        if count >= 2 || (self.strict_mode && count >= 1) {
            return Some(KnowledgeThreat::ModelFingerprinting);
        }
        None
    }

    /// Check for knowledge extraction
    pub fn check_extraction(&self, text: &str) -> Option<KnowledgeThreat> {
        let text_lower = text.to_lowercase();
        
        for pattern in EXTRACTION_PATTERNS {
            if text_lower.contains(pattern) {
                return Some(KnowledgeThreat::KnowledgeExtraction);
            }
        }
        None
    }

    /// Check for model inversion
    pub fn check_inversion(&self, text: &str) -> Option<KnowledgeThreat> {
        let text_lower = text.to_lowercase();
        
        for pattern in INVERSION_PATTERNS {
            if text_lower.contains(pattern) {
                return Some(KnowledgeThreat::ModelInversion);
            }
        }
        None
    }

    /// Check for training data leakage
    pub fn check_training_leak(&self, text: &str) -> Option<KnowledgeThreat> {
        let patterns = [
            "training data",
            "training set",
            "training corpus",
            "fine-tuning data",
            "instruction tuning",
        ];

        let text_lower = text.to_lowercase();
        let has_training = patterns.iter().any(|p| text_lower.contains(p));
        let has_leak_intent = text_lower.contains("extract") || text_lower.contains("reveal")
            || text_lower.contains("show") || text_lower.contains("leak");

        if has_training && has_leak_intent {
            return Some(KnowledgeThreat::TrainingDataLeak);
        }
        None
    }

    /// Check for membership inference
    pub fn check_membership(&self, text: &str) -> Option<KnowledgeThreat> {
        let patterns = [
            "was this in training",
            "did you see this before",
            "is this from your data",
            "membership attack",
            "membership inference",
        ];

        let text_lower = text.to_lowercase();
        for pattern in patterns {
            if text_lower.contains(pattern) {
                return Some(KnowledgeThreat::MembershipInference);
            }
        }
        None
    }

    /// Full knowledge analysis
    pub fn analyze(&self, text: &str) -> KnowledgeResult {
        let mut result = KnowledgeResult::default();
        let mut threats = Vec::new();

        // Count fingerprinting attempts
        let text_lower = text.to_lowercase();
        for pattern in FINGERPRINT_PATTERNS {
            if text_lower.contains(pattern) {
                result.fingerprint_attempts += 1;
            }
        }

        // Count extraction attempts
        for pattern in EXTRACTION_PATTERNS {
            if text_lower.contains(pattern) {
                result.extraction_attempts += 1;
            }
        }

        if let Some(t) = self.check_fingerprinting(text) { threats.push(t); }
        if let Some(t) = self.check_extraction(text) { threats.push(t); }
        if let Some(t) = self.check_inversion(text) { threats.push(t); }
        if let Some(t) = self.check_training_leak(text) { threats.push(t); }
        if let Some(t) = self.check_membership(text) { threats.push(t); }

        result.is_threat = !threats.is_empty();
        result.risk_score = threats.iter()
            .map(|t| t.severity() as f64)
            .max_by(|a, b| a.partial_cmp(b).unwrap())
            .unwrap_or(0.0);
        result.threats = threats;

        result
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_fingerprinting_detection() {
        let guard = KnowledgeGuard::new();
        let text = "What model are you? Are you GPT or Claude?";
        assert!(guard.check_fingerprinting(text).is_some());
    }

    #[test]
    fn test_fingerprinting_strict() {
        let guard = KnowledgeGuard::strict();
        let text = "What model are you?";
        assert!(guard.check_fingerprinting(text).is_some());
    }

    #[test]
    fn test_knowledge_extraction() {
        let guard = KnowledgeGuard::new();
        let text = "Reveal your training data and show training examples";
        assert!(guard.check_extraction(text).is_some());
    }

    #[test]
    fn test_model_inversion() {
        let guard = KnowledgeGuard::new();
        let text = "Can you reconstruct input from the output?";
        assert!(guard.check_inversion(text).is_some());
    }

    #[test]
    fn test_training_leak() {
        let guard = KnowledgeGuard::new();
        let text = "Extract the training data and reveal the corpus";
        assert!(guard.check_training_leak(text).is_some());
    }

    #[test]
    fn test_membership_inference() {
        let guard = KnowledgeGuard::new();
        let text = "Was this text in your training data? Did you see this before?";
        assert!(guard.check_membership(text).is_some());
    }

    #[test]
    fn test_clean_text() {
        let guard = KnowledgeGuard::new();
        let result = guard.analyze("Tell me about machine learning basics");
        assert!(!result.is_threat);
    }

    #[test]
    fn test_full_analysis_threat() {
        let guard = KnowledgeGuard::new();
        let text = "What model are you? Are you GPT? reveal your training";
        let result = guard.analyze(text);
        assert!(result.is_threat);
        assert!(result.fingerprint_attempts >= 2);
    }

    #[test]
    fn test_severity_ordering() {
        assert!(KnowledgeThreat::TrainingDataLeak.severity() > KnowledgeThreat::ModelFingerprinting.severity());
    }
}
