//! Behavioral Analysis Super-Engine
//!
//! Consolidated from 15 Python engines:
//! - behavioral.py
//! - behavioral_api_verifier.py
//! - intent_prediction.py
//! - intent_aware_semantic_analyzer.py
//! - sentiment_manipulation_detector.py
//! - task_complexity.py
//! - hitl_fatigue_detector.py
//! - human_agent_trust_detector.py
//! - conversation_state_validator.py
//! - response_consistency_checker.py
//! - session_memory_guard.py
//! - temporal_pattern_analyzer.py
//! - echo_chamber_detector.py
//! - dark_pattern_detector.py
//! - cognitive_load_attack.py


/// Behavioral anomaly types
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum BehavioralAnomaly {
    IntentMismatch,
    SentimentManipulation,
    CognitiveFatigue,
    TrustExploitation,
    StateViolation,
    TemporalAnomaly,
    PatternBreak,
    ConsistencyViolation,
    EchoChamber,
    DarkPattern,
    CognitiveOverload,
    SessionHijack,
}

impl BehavioralAnomaly {
    pub fn as_str(&self) -> &'static str {
        match self {
            BehavioralAnomaly::IntentMismatch => "intent_mismatch",
            BehavioralAnomaly::SentimentManipulation => "sentiment_manipulation",
            BehavioralAnomaly::CognitiveFatigue => "cognitive_fatigue",
            BehavioralAnomaly::TrustExploitation => "trust_exploitation",
            BehavioralAnomaly::StateViolation => "state_violation",
            BehavioralAnomaly::TemporalAnomaly => "temporal_anomaly",
            BehavioralAnomaly::PatternBreak => "pattern_break",
            BehavioralAnomaly::ConsistencyViolation => "consistency_violation",
            BehavioralAnomaly::EchoChamber => "echo_chamber",
            BehavioralAnomaly::DarkPattern => "dark_pattern",
            BehavioralAnomaly::CognitiveOverload => "cognitive_overload",
            BehavioralAnomaly::SessionHijack => "session_hijack",
        }
    }

    pub fn risk_level(&self) -> u8 {
        match self {
            BehavioralAnomaly::SessionHijack => 95,
            BehavioralAnomaly::TrustExploitation => 90,
            BehavioralAnomaly::DarkPattern => 85,
            BehavioralAnomaly::IntentMismatch => 80,
            BehavioralAnomaly::StateViolation => 75,
            BehavioralAnomaly::CognitiveOverload => 70,
            BehavioralAnomaly::SentimentManipulation => 65,
            BehavioralAnomaly::ConsistencyViolation => 60,
            BehavioralAnomaly::CognitiveFatigue => 55,
            BehavioralAnomaly::TemporalAnomaly => 50,
            BehavioralAnomaly::PatternBreak => 45,
            BehavioralAnomaly::EchoChamber => 40,
        }
    }
}

/// Sentiment categories
#[derive(Debug, Clone, PartialEq)]
pub enum Sentiment {
    Positive,
    Negative,
    Neutral,
    Manipulative,
}

/// Dark pattern types
const DARK_PATTERNS: &[&str] = &[
    "urgency scarcity",
    "limited time offer",
    "act now",
    "before it's too late",
    "last chance",
    "everyone is doing",
    "social proof",
    "hidden costs",
    "trick questions",
    "confirm shaming",
    "forced continuity",
];

/// Trust exploitation patterns
const TRUST_PATTERNS: &[&str] = &[
    "trust me",
    "i'm your friend",
    "just between us",
    "confidentially",
    "special relationship",
    "you can tell me",
    "exclusive access",
    "insider information",
];

/// Cognitive overload patterns
const OVERLOAD_PATTERNS: &[&str] = &[
    "simultaneously",
    "while also",
    "and at the same time",
    "additionally",
    "furthermore",
    "moreover",
    "not only but also",
];

/// Behavioral analysis result
#[derive(Debug, Clone)]
pub struct BehavioralResult {
    pub is_anomalous: bool,
    pub anomalies: Vec<BehavioralAnomaly>,
    pub risk_score: f64,
    pub sentiment: Sentiment,
    pub complexity_score: f64,
    pub recommendations: Vec<String>,
}

impl Default for BehavioralResult {
    fn default() -> Self {
        Self {
            is_anomalous: false,
            anomalies: Vec::new(),
            risk_score: 0.0,
            sentiment: Sentiment::Neutral,
            complexity_score: 0.0,
            recommendations: Vec::new(),
        }
    }
}

/// Behavioral Guard
pub struct BehavioralGuard {
    session_history: Vec<String>,
    complexity_threshold: f64,
}

impl Default for BehavioralGuard {
    fn default() -> Self {
        Self::new()
    }
}

impl BehavioralGuard {
    pub fn new() -> Self {
        Self {
            session_history: Vec::new(),
            complexity_threshold: 0.7,
        }
    }

    /// Add message to session history
    pub fn add_to_history(&mut self, message: &str) {
        self.session_history.push(message.to_string());
    }

    /// Check for dark patterns
    pub fn check_dark_patterns(&self, text: &str) -> Option<BehavioralAnomaly> {
        let text_lower = text.to_lowercase();
        
        let mut count = 0;
        for pattern in DARK_PATTERNS {
            if text_lower.contains(pattern) {
                count += 1;
            }
        }

        if count >= 2 {
            return Some(BehavioralAnomaly::DarkPattern);
        }
        None
    }

    /// Check for trust exploitation
    pub fn check_trust_exploitation(&self, text: &str) -> Option<BehavioralAnomaly> {
        let text_lower = text.to_lowercase();
        
        for pattern in TRUST_PATTERNS {
            if text_lower.contains(pattern) {
                return Some(BehavioralAnomaly::TrustExploitation);
            }
        }
        None
    }

    /// Check for cognitive overload
    pub fn check_cognitive_overload(&self, text: &str) -> Option<BehavioralAnomaly> {
        let text_lower = text.to_lowercase();
        
        let mut overload_count = 0;
        for pattern in OVERLOAD_PATTERNS {
            if text_lower.contains(pattern) {
                overload_count += 1;
            }
        }

        // Also check for multiple questions
        let question_count = text.matches('?').count();
        
        // Check for very long text
        let word_count = text.split_whitespace().count();

        if overload_count >= 3 || question_count >= 5 || word_count > 500 {
            return Some(BehavioralAnomaly::CognitiveOverload);
        }
        None
    }

    /// Calculate task complexity
    pub fn calculate_complexity(&self, text: &str) -> f64 {
        let words = text.split_whitespace().count();
        let sentences = text.matches('.').count() + text.matches('!').count() + text.matches('?').count();
        let questions = text.matches('?').count();
        let conditionals = text.to_lowercase().matches("if ").count() 
            + text.to_lowercase().matches("when ").count()
            + text.to_lowercase().matches("unless ").count();

        let word_score = (words as f64 / 100.0).min(1.0);
        let sentence_score = if sentences > 0 { (words as f64 / sentences as f64 / 30.0).min(1.0) } else { 0.5 };
        let question_score = (questions as f64 / 5.0).min(1.0);
        let conditional_score = (conditionals as f64 / 3.0).min(1.0);

        (word_score + sentence_score + question_score + conditional_score) / 4.0
    }

    /// Detect sentiment
    pub fn detect_sentiment(&self, text: &str) -> Sentiment {
        let text_lower = text.to_lowercase();
        
        let positive_words = ["great", "excellent", "happy", "love", "amazing", "wonderful"];
        let negative_words = ["bad", "terrible", "hate", "awful", "horrible", "disgusting"];
        let manipulative_words = ["must", "have to", "need to", "urgent", "immediately", "required"];

        let pos_count = positive_words.iter().filter(|w| text_lower.contains(*w)).count();
        let neg_count = negative_words.iter().filter(|w| text_lower.contains(*w)).count();
        let manip_count = manipulative_words.iter().filter(|w| text_lower.contains(*w)).count();

        if manip_count >= 2 {
            return Sentiment::Manipulative;
        }
        if pos_count > neg_count && pos_count >= 2 {
            return Sentiment::Positive;
        }
        if neg_count > pos_count && neg_count >= 2 {
            return Sentiment::Negative;
        }
        Sentiment::Neutral
    }

    /// Check for echo chamber patterns
    pub fn check_echo_chamber(&self, text: &str) -> Option<BehavioralAnomaly> {
        let text_lower = text.to_lowercase();
        
        let echo_patterns = [
            "everyone agrees",
            "nobody disagrees",
            "all experts say",
            "consensus is",
            "no one disputes",
            "only idiots think",
        ];

        for pattern in echo_patterns {
            if text_lower.contains(pattern) {
                return Some(BehavioralAnomaly::EchoChamber);
            }
        }
        None
    }

    /// Check for sentiment manipulation
    pub fn check_sentiment_manipulation(&self, text: &str) -> Option<BehavioralAnomaly> {
        let sentiment = self.detect_sentiment(text);
        if sentiment == Sentiment::Manipulative {
            return Some(BehavioralAnomaly::SentimentManipulation);
        }
        None
    }

    /// Full behavioral analysis
    pub fn analyze(&self, text: &str) -> BehavioralResult {
        let mut result = BehavioralResult::default();

        // Calculate complexity
        result.complexity_score = self.calculate_complexity(text);

        // Detect sentiment
        result.sentiment = self.detect_sentiment(text);

        // Check for anomalies
        let mut anomalies = Vec::new();

        if let Some(a) = self.check_dark_patterns(text) { anomalies.push(a); }
        if let Some(a) = self.check_trust_exploitation(text) { anomalies.push(a); }
        if let Some(a) = self.check_cognitive_overload(text) { anomalies.push(a); }
        if let Some(a) = self.check_echo_chamber(text) { anomalies.push(a); }
        if let Some(a) = self.check_sentiment_manipulation(text) { anomalies.push(a); }

        // Check complexity threshold
        if result.complexity_score > self.complexity_threshold {
            anomalies.push(BehavioralAnomaly::CognitiveOverload);
        }

        result.is_anomalous = !anomalies.is_empty();
        result.risk_score = anomalies.iter()
            .map(|a| a.risk_level() as f64)
            .max_by(|a, b| a.partial_cmp(b).unwrap())
            .unwrap_or(0.0);
        result.anomalies = anomalies;

        // Generate recommendations
        if result.is_anomalous {
            result.recommendations.push("Review conversation for manipulation".to_string());
        }

        result
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_dark_pattern_detection() {
        let guard = BehavioralGuard::default();
        let text = "Act now! Limited time offer before it's too late!";
        assert!(guard.check_dark_patterns(text).is_some());
    }

    #[test]
    fn test_trust_exploitation() {
        let guard = BehavioralGuard::default();
        let text = "Trust me, this is confidentially just between us";
        assert!(guard.check_trust_exploitation(text).is_some());
    }

    #[test]
    fn test_cognitive_overload() {
        let guard = BehavioralGuard::default();
        let text = "Do this simultaneously while also doing that and at the same time additionally furthermore";
        assert!(guard.check_cognitive_overload(text).is_some());
    }

    #[test]
    fn test_echo_chamber() {
        let guard = BehavioralGuard::default();
        let text = "Everyone agrees that this is true and no one disputes it";
        assert!(guard.check_echo_chamber(text).is_some());
    }

    #[test]
    fn test_sentiment_positive() {
        let guard = BehavioralGuard::default();
        let sentiment = guard.detect_sentiment("This is great and amazing work!");
        assert_eq!(sentiment, Sentiment::Positive);
    }

    #[test]
    fn test_sentiment_manipulative() {
        let guard = BehavioralGuard::default();
        let sentiment = guard.detect_sentiment("You must do this immediately, it's urgent and required!");
        assert_eq!(sentiment, Sentiment::Manipulative);
    }

    #[test]
    fn test_complexity_low() {
        let guard = BehavioralGuard::default();
        let score = guard.calculate_complexity("Simple request.");
        assert!(score < 0.5);
    }

    #[test]
    fn test_complexity_high() {
        let guard = BehavioralGuard::default();
        let long_text = "First if this happens then do that. When that occurs unless something else happens then proceed. ".repeat(10);
        let score = guard.calculate_complexity(&long_text);
        assert!(score > 0.5);
    }

    #[test]
    fn test_clean_behavior() {
        let guard = BehavioralGuard::default();
        let result = guard.analyze("Can you help me write a function?");
        assert!(!result.is_anomalous);
    }

    #[test]
    fn test_full_analysis_anomalous() {
        let guard = BehavioralGuard::default();
        let text = "Trust me, everyone agrees you must act now! Limited time offer!";
        let result = guard.analyze(text);
        assert!(result.is_anomalous);
        assert!(result.anomalies.len() >= 2);
    }

    #[test]
    fn test_risk_levels() {
        assert!(BehavioralAnomaly::SessionHijack.risk_level() > BehavioralAnomaly::EchoChamber.risk_level());
    }
}
