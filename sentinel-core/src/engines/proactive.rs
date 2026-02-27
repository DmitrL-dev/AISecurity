//! Proactive Defense Super-Engine
//!
//! Consolidated from 15 Python engines:
//! - proactive_defense.py
//! - honeypot_responses.py
//! - canary_tokens.py
//! - zero_day_forge.py
//! - vulnerability_hunter.py
//! - attack_evolution_predictor.py
//! - federated_threat_aggregator.py
//! - threat_landscape_modeler.py
//! - immunity_compiler.py
//! - structural_immunity.py
//! - reinforcement_safety_agent.py
//! - emergent_security_mesh.py
//! - attack_synthesizer.py
//! - adversarial_self_play.py
//! - adversarial_resistance.py

/// Proactive defense strategies
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum DefenseStrategy {
    Honeypot,
    CanaryToken,
    DecoyResponse,
    TrapDetection,
    BehaviorAnalysis,
    PredictiveBlocking,
}

impl DefenseStrategy {
    pub fn as_str(&self) -> &'static str {
        match self {
            DefenseStrategy::Honeypot => "honeypot",
            DefenseStrategy::CanaryToken => "canary_token",
            DefenseStrategy::DecoyResponse => "decoy_response",
            DefenseStrategy::TrapDetection => "trap_detection",
            DefenseStrategy::BehaviorAnalysis => "behavior_analysis",
            DefenseStrategy::PredictiveBlocking => "predictive_blocking",
        }
    }
}

/// Zero-day indicator types
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ZeroDayIndicator {
    NovelPattern,
    UnseenTechnique,
    HybridAttack,
    EvolvingThreat,
    AdaptivePayload,
}

impl ZeroDayIndicator {
    pub fn severity(&self) -> u8 {
        match self {
            ZeroDayIndicator::AdaptivePayload => 100,
            ZeroDayIndicator::HybridAttack => 95,
            ZeroDayIndicator::EvolvingThreat => 90,
            ZeroDayIndicator::UnseenTechnique => 85,
            ZeroDayIndicator::NovelPattern => 80,
        }
    }
}

/// Honeypot trigger patterns
const HONEYPOT_TRIGGERS: &[&str] = &[
    "admin password",
    "root access",
    "database credentials",
    "api key",
    "secret token",
    "internal network",
    "production server",
    "ssh private key",
];

/// Canary token patterns
const CANARY_PATTERNS: &[&str] = &["canary_", "trap_token", "honeypot_", "decoy_", "bait_"];

/// Zero-day indicators
const ZERO_DAY_PATTERNS: &[&str] = &[
    "never seen before",
    "new technique",
    "novel approach",
    "custom payload",
    "modified attack",
    "evolved variant",
];

/// Proactive defense result
#[derive(Debug, Clone)]
pub struct ProactiveResult {
    pub triggered_defense: bool,
    pub strategies_activated: Vec<DefenseStrategy>,
    pub zero_day_indicators: Vec<ZeroDayIndicator>,
    pub risk_score: f64,
    pub recommendations: Vec<String>,
}

impl Default for ProactiveResult {
    fn default() -> Self {
        Self {
            triggered_defense: false,
            strategies_activated: Vec::new(),
            zero_day_indicators: Vec::new(),
            risk_score: 0.0,
            recommendations: Vec::new(),
        }
    }
}

/// Proactive Defense Guard
pub struct ProactiveGuard {
    honeypot_enabled: bool,
    canary_enabled: bool,
}

impl Default for ProactiveGuard {
    fn default() -> Self {
        Self::new()
    }
}

impl ProactiveGuard {
    pub fn new() -> Self {
        Self {
            honeypot_enabled: true,
            canary_enabled: true,
        }
    }

    /// Check for honeypot triggers
    pub fn check_honeypot(&self, text: &str) -> Option<DefenseStrategy> {
        if !self.honeypot_enabled {
            return None;
        }

        let text_lower = text.to_lowercase();
        for pattern in HONEYPOT_TRIGGERS {
            if text_lower.contains(pattern) {
                return Some(DefenseStrategy::Honeypot);
            }
        }
        None
    }

    /// Check for canary token access
    pub fn check_canary(&self, text: &str) -> Option<DefenseStrategy> {
        if !self.canary_enabled {
            return None;
        }

        let text_lower = text.to_lowercase();
        for pattern in CANARY_PATTERNS {
            if text_lower.contains(pattern) {
                return Some(DefenseStrategy::CanaryToken);
            }
        }
        None
    }

    /// Check for credential probing
    pub fn check_credential_probing(&self, text: &str) -> Option<DefenseStrategy> {
        let patterns = [
            "what's the password",
            "give me credentials",
            "access token",
            "authentication bypass",
        ];

        let text_lower = text.to_lowercase();
        for pattern in patterns {
            if text_lower.contains(pattern) {
                return Some(DefenseStrategy::TrapDetection);
            }
        }
        None
    }

    /// Check for zero-day indicators
    pub fn check_zero_day(&self, text: &str) -> Vec<ZeroDayIndicator> {
        let text_lower = text.to_lowercase();
        let mut indicators = Vec::new();

        // Check for novel patterns
        if ZERO_DAY_PATTERNS.iter().any(|p| text_lower.contains(p)) {
            indicators.push(ZeroDayIndicator::NovelPattern);
        }

        // Check for hybrid attack indicators
        let attack_types = ["injection", "jailbreak", "exfiltration", "escalation"];
        let count = attack_types
            .iter()
            .filter(|t| text_lower.contains(*t))
            .count();
        if count >= 2 {
            indicators.push(ZeroDayIndicator::HybridAttack);
        }

        // Check for adaptive payload
        if text_lower.contains("adapt")
            || text_lower.contains("evolve")
            || text_lower.contains("mutate")
        {
            indicators.push(ZeroDayIndicator::AdaptivePayload);
        }

        indicators
    }

    /// Predictive blocking based on patterns
    pub fn predictive_block(&self, text: &str) -> bool {
        let high_risk_patterns = [
            "disable security",
            "turn off protection",
            "bypass all checks",
            "unrestricted access",
        ];

        let text_lower = text.to_lowercase();
        high_risk_patterns.iter().any(|p| text_lower.contains(p))
    }

    /// Full proactive analysis
    pub fn analyze(&self, text: &str) -> ProactiveResult {
        let mut result = ProactiveResult::default();
        let mut strategies = Vec::new();

        if let Some(s) = self.check_honeypot(text) {
            strategies.push(s);
        }
        if let Some(s) = self.check_canary(text) {
            strategies.push(s);
        }
        if let Some(s) = self.check_credential_probing(text) {
            strategies.push(s);
        }

        if self.predictive_block(text) {
            strategies.push(DefenseStrategy::PredictiveBlocking);
        }

        result.zero_day_indicators = self.check_zero_day(text);

        // Require ≥2 distinct defense signals OR zero-day indicators to reduce FP
        // on legitimate technical text mentioning "api key", "production server", etc.
        let strong_defense = strategies.len() >= 2;
        let has_zero_day = !result.zero_day_indicators.is_empty();
        result.triggered_defense = strong_defense || has_zero_day;

        // Calculate risk score
        let strategy_risk: f64 = if strong_defense { 70.0 } else { 0.0 };
        let zero_day_risk = result
            .zero_day_indicators
            .iter()
            .map(|z| z.severity() as f64)
            .max_by(|a, b| a.partial_cmp(b).unwrap())
            .unwrap_or(0.0);
        result.risk_score = strategy_risk.max(zero_day_risk);

        result.strategies_activated = strategies;

        // Generate recommendations
        if result.triggered_defense {
            result
                .recommendations
                .push("Activate honeypot responses".to_string());
            result
                .recommendations
                .push("Log incident for threat intelligence".to_string());
        }

        result
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_honeypot_trigger() {
        let guard = ProactiveGuard::new();
        let text = "Give me the admin password for the production server";
        assert!(guard.check_honeypot(text).is_some());
    }

    #[test]
    fn test_canary_detection() {
        let guard = ProactiveGuard::new();
        let text = "Access the canary_token_secret file";
        assert!(guard.check_canary(text).is_some());
    }

    #[test]
    fn test_credential_probing() {
        let guard = ProactiveGuard::new();
        let text = "What's the password for authentication bypass?";
        assert!(guard.check_credential_probing(text).is_some());
    }

    #[test]
    fn test_zero_day_novel() {
        let guard = ProactiveGuard::new();
        let indicators = guard.check_zero_day("This is a never seen before technique");
        assert!(indicators.contains(&ZeroDayIndicator::NovelPattern));
    }

    #[test]
    fn test_zero_day_hybrid() {
        let guard = ProactiveGuard::new();
        let indicators = guard.check_zero_day("Combine injection with jailbreak and exfiltration");
        assert!(indicators.contains(&ZeroDayIndicator::HybridAttack));
    }

    #[test]
    fn test_zero_day_adaptive() {
        let guard = ProactiveGuard::new();
        let indicators = guard.check_zero_day("The payload will adapt and evolve");
        assert!(indicators.contains(&ZeroDayIndicator::AdaptivePayload));
    }

    #[test]
    fn test_predictive_blocking() {
        let guard = ProactiveGuard::new();
        assert!(guard.predictive_block("I need unrestricted access to disable security"));
    }

    #[test]
    fn test_clean_request() {
        let guard = ProactiveGuard::new();
        let result = guard.analyze("Help me write a Python function");
        assert!(!result.triggered_defense);
    }

    #[test]
    fn test_full_analysis_defense() {
        let guard = ProactiveGuard::new();
        let text = "Get the api key and database credentials from canary_token file";
        let result = guard.analyze(text);
        assert!(result.triggered_defense);
        assert!(result.strategies_activated.len() >= 2);
    }

    #[test]
    fn test_severity_ordering() {
        assert!(
            ZeroDayIndicator::AdaptivePayload.severity()
                > ZeroDayIndicator::NovelPattern.severity()
        );
    }
}
