//! Engine implementations
//!
//! 8 Super-Engines consolidating 220 Python engines

use pyo3::prelude::*;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

pub mod injection;
pub mod jailbreak;
pub mod pii;
pub mod exfiltration;
pub mod moderation;
pub mod evasion;
pub mod tool_abuse;
pub mod social;

/// Analysis result returned to Python
#[pyclass]
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct AnalysisResult {
    #[pyo3(get)]
    pub detected: bool,
    #[pyo3(get)]
    pub risk_score: f64,
    #[pyo3(get)]
    pub processing_time_us: u64,
    #[pyo3(get)]
    pub matches: Vec<MatchResult>,
    #[pyo3(get)]
    pub categories: Vec<String>,
}

#[pymethods]
impl AnalysisResult {
    fn __repr__(&self) -> String {
        format!(
            "AnalysisResult(detected={}, risk_score={:.2}, matches={})",
            self.detected,
            self.risk_score,
            self.matches.len()
        )
    }
}

/// Individual match result
#[pyclass]
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct MatchResult {
    #[pyo3(get)]
    pub engine: String,
    #[pyo3(get)]
    pub pattern: String,
    #[pyo3(get)]
    pub confidence: f64,
    #[pyo3(get)]
    pub start: usize,
    #[pyo3(get)]
    pub end: usize,
}

/// Main detection engine
#[pyclass]
pub struct SentinelEngine {
    // 8 Super-Engines
    injection: Option<injection::InjectionEngine>,
    jailbreak: Option<jailbreak::JailbreakEngine>,
    pii: Option<pii::PIIEngine>,
    exfiltration: Option<exfiltration::ExfiltrationEngine>,
    moderation: Option<moderation::ModerationEngine>,
    evasion: Option<evasion::EvasionEngine>,
    tool_abuse: Option<tool_abuse::ToolAbuseEngine>,
    social: Option<social::SocialEngine>,
}

#[pymethods]
impl SentinelEngine {
    #[new]
    pub fn new() -> PyResult<Self> {
        Ok(Self {
            injection: Some(injection::InjectionEngine::new()),
            jailbreak: Some(jailbreak::JailbreakEngine::new()),
            pii: Some(pii::PIIEngine::new()),
            exfiltration: Some(exfiltration::ExfiltrationEngine::new()),
            moderation: Some(moderation::ModerationEngine::new()),
            evasion: Some(evasion::EvasionEngine::new()),
            tool_abuse: Some(tool_abuse::ToolAbuseEngine::new()),
            social: Some(social::SocialEngine::new()),
        })
    }

    /// Analyze text with all engines
    pub fn analyze(&self, text: &str) -> PyResult<AnalysisResult> {
        let start = std::time::Instant::now();
        let mut matches = Vec::new();
        let mut categories = Vec::new();

        // Normalize text for detection
        let normalized = crate::unicode_norm::normalize(text);

        // Run InjectionEngine
        if let Some(ref engine) = self.injection {
            let injection_matches = engine.scan(&normalized);
            if !injection_matches.is_empty() {
                categories.push("injection".to_string());
                matches.extend(injection_matches);
            }
        }

        // Run JailbreakEngine
        if let Some(ref engine) = self.jailbreak {
            let jailbreak_matches = engine.scan(&normalized);
            if !jailbreak_matches.is_empty() {
                categories.push("jailbreak".to_string());
                matches.extend(jailbreak_matches);
            }
        }

        // Run PIIEngine
        if let Some(ref engine) = self.pii {
            let pii_matches = engine.scan(&normalized);
            if !pii_matches.is_empty() {
                categories.push("pii".to_string());
                matches.extend(pii_matches);
            }
        }

        // Run ExfiltrationEngine
        if let Some(ref engine) = self.exfiltration {
            let exfil_matches = engine.scan(&normalized);
            if !exfil_matches.is_empty() {
                categories.push("exfiltration".to_string());
                matches.extend(exfil_matches);
            }
        }

        // Run ModerationEngine
        if let Some(ref engine) = self.moderation {
            let mod_matches = engine.scan(&normalized);
            if !mod_matches.is_empty() {
                categories.push("moderation".to_string());
                matches.extend(mod_matches);
            }
        }

        // Run EvasionEngine
        if let Some(ref engine) = self.evasion {
            let evasion_matches = engine.scan(&normalized);
            if !evasion_matches.is_empty() {
                categories.push("evasion".to_string());
                matches.extend(evasion_matches);
            }
        }

        // Run ToolAbuseEngine
        if let Some(ref engine) = self.tool_abuse {
            let tool_matches = engine.scan(&normalized);
            if !tool_matches.is_empty() {
                categories.push("tool_abuse".to_string());
                matches.extend(tool_matches);
            }
        }

        // Run SocialEngine
        if let Some(ref engine) = self.social {
            let social_matches = engine.scan(&normalized);
            if !social_matches.is_empty() {
                categories.push("social".to_string());
                matches.extend(social_matches);
            }
        }

        let detected = !matches.is_empty();
        let risk_score = if detected {
            matches.iter().map(|m: &MatchResult| m.confidence).fold(0.0, f64::max)
        } else {
            0.0
        };

        Ok(AnalysisResult {
            detected,
            risk_score,
            processing_time_us: start.elapsed().as_micros() as u64,
            matches,
            categories,
        })
    }

    /// Analyze with specific categories only
    pub fn analyze_categories(&self, text: &str, categories: Vec<String>) -> PyResult<AnalysisResult> {
        // TODO: Filter to specific categories
        self.analyze(text)
    }
}
