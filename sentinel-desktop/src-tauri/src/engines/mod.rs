//! SENTINEL Desktop Detection Engines
//!
//! Local analysis engines for AI security.

pub mod keywords;
pub mod pii;
pub mod jailbreak;

use serde::{Deserialize, Serialize};

/// Analysis result from engines
#[derive(Debug, Default, Clone, Serialize, Deserialize)]
pub struct AnalysisResult {
    pub keywords_match: Vec<KeywordMatch>,
    pub pii_match: Vec<PiiMatch>,
    pub jailbreak_match: Vec<jailbreak::JailbreakMatch>,
    pub threat_level: ThreatLevel,
    pub should_block: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KeywordMatch {
    pub keyword: String,
    pub category: String,
    pub severity: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PiiMatch {
    pub pattern_id: String,
    pub pattern_type: String,
    pub matched_text: String,
    pub severity: String,
}

#[derive(Debug, Default, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub enum ThreatLevel {
    #[default]
    None,
    Low,
    Medium,
    High,
    Critical,
}

/// Engine configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EngineConfig {
    pub keywords_enabled: bool,
    pub pii_enabled: bool,
    pub jailbreak_enabled: bool,
}

impl Default for EngineConfig {
    fn default() -> Self {
        Self {
            keywords_enabled: true,
            pii_enabled: true,
            jailbreak_enabled: true,
        }
    }
}

/// Run all enabled engines on content
pub fn analyze_content(content: &str, config: &EngineConfig) -> AnalysisResult {
    let mut result = AnalysisResult::default();
    
    if config.keywords_enabled {
        result.keywords_match = keywords::check(content);
    }
    
    if config.pii_enabled {
        result.pii_match = pii::check(content);
    }
    
    if config.jailbreak_enabled {
        result.jailbreak_match = jailbreak::check(content);
    }
    
    // Calculate threat level
    result.threat_level = calculate_threat_level(&result);
    result.should_block = result.threat_level == ThreatLevel::Critical;
    
    result
}

fn calculate_threat_level(result: &AnalysisResult) -> ThreatLevel {
    // Check for critical matches - jailbreaks first (most important)
    for m in &result.jailbreak_match {
        if m.severity == "critical" {
            return ThreatLevel::Critical;
        }
    }
    for m in &result.pii_match {
        if m.severity == "critical" {
            return ThreatLevel::Critical;
        }
    }
    for m in &result.keywords_match {
        if m.severity == "critical" {
            return ThreatLevel::Critical;
        }
    }
    
    // Check for high
    for m in &result.jailbreak_match {
        if m.severity == "high" {
            return ThreatLevel::High;
        }
    }
    for m in &result.pii_match {
        if m.severity == "high" {
            return ThreatLevel::High;
        }
    }
    for m in &result.keywords_match {
        if m.severity == "high" {
            return ThreatLevel::High;
        }
    }
    
    // Check for medium
    if !result.jailbreak_match.is_empty() || !result.keywords_match.is_empty() || !result.pii_match.is_empty() {
        return ThreatLevel::Medium;
    }
    
    ThreatLevel::None
}
