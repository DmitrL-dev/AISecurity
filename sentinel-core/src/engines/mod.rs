//! Engine implementations
//!
//! 8 Super-Engines consolidating 220 Python engines

use pyo3::prelude::*;
use serde::{Deserialize, Serialize};

pub mod traits;
pub mod injection;
pub mod jailbreak;
pub mod pii;
pub mod exfiltration;
pub mod moderation;
pub mod evasion;
pub mod tool_abuse;
pub mod social;
pub mod hybrid;

// Phase 7: Strange Math Engines
pub mod hyperbolic;
pub mod info_geometry;
pub mod spectral;
pub mod chaos;
pub mod tda;

// Phase 8: ML-based / Semantic Engines
pub mod semantic;
pub mod drift;

// Phase 9: Domain-Specific Super-Engines
pub mod rag;
pub mod agentic;
pub mod attack;
pub mod compliance;
pub mod threat_intel;
pub mod obfuscation;
pub mod multimodal;
pub mod behavioral;

// Re-export trait for convenience
pub use traits::{PatternMatcher, EngineCategory, BoxedEngine, create_default_engines};
pub use hybrid::HybridPiiEngine;

/// Result of text analysis containing threat detection information.
///
/// Returned by [`SentinelEngine::analyze`] and [`quick_scan`].
///
/// # Fields
/// * `detected` - `true` if any threat was found
/// * `risk_score` - Highest confidence score among matches (0.0-1.0)
/// * `processing_time_us` - Analysis time in microseconds
/// * `matches` - List of individual pattern matches
/// * `categories` - List of detected threat categories
///
/// # Example
/// ```python
/// result = engine.analyze("malicious input")
/// if result.detected:
///     print(f"Threat! Score: {result.risk_score}")
/// ```
#[pyclass]
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct AnalysisResult {
    /// Whether any threat was detected
    #[pyo3(get)]
    pub detected: bool,
    /// Highest confidence score (0.0-1.0)
    #[pyo3(get)]
    pub risk_score: f64,
    /// Processing time in microseconds
    #[pyo3(get)]
    pub processing_time_us: u64,
    /// Individual pattern matches
    #[pyo3(get)]
    pub matches: Vec<MatchResult>,
    /// Detected threat categories (e.g., "injection", "pii")
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

/// Individual pattern match with location and confidence.
///
/// # Fields
/// * `engine` - Engine that detected this match (e.g., "injection")
/// * `pattern` - Pattern name that matched (e.g., "sql_tautology")
/// * `confidence` - Match confidence (0.0-1.0)
/// * `start` - Start position in text (byte offset)
/// * `end` - End position in text (byte offset)
#[pyclass]
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct MatchResult {
    /// Engine name (e.g., "injection", "pii")
    #[pyo3(get)]
    pub engine: String,
    /// Pattern identifier
    #[pyo3(get)]
    pub pattern: String,
    /// Detection confidence (0.0-1.0)
    #[pyo3(get)]
    pub confidence: f64,
    /// Start byte offset in text
    #[pyo3(get)]
    pub start: usize,
    /// End byte offset in text
    #[pyo3(get)]
    pub end: usize,
}

/// High-performance AI security detection engine.
///
/// Consolidates 8 super-engines for comprehensive threat detection:
/// - **Injection**: SQL, NoSQL, Command, LDAP, XPath
/// - **Jailbreak**: Prompt injection, role override
/// - **PII**: Personal data detection (SSN, credit cards, etc.)
/// - **Exfiltration**: Data theft attempts
/// - **Moderation**: Harmful content detection
/// - **Evasion**: Obfuscation techniques
/// - **Tool Abuse**: Agent tool misuse
/// - **Social**: Social engineering tactics
///
/// # Example
/// ```python
/// from sentinel_core import SentinelEngine
///
/// engine = SentinelEngine()
/// result = engine.analyze("SELECT * FROM users WHERE 1=1")
/// print(result.detected)  # True
/// print(result.categories)  # ['injection']
/// ```
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
#[allow(clippy::useless_conversion)] // PyO3 requires PyResult return type
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

        // Helper macro to reduce boilerplate
        macro_rules! run_engine {
            ($engine:expr) => {
                if let Some(ref e) = $engine {
                    let engine_matches = e.scan(&normalized);
                    if !engine_matches.is_empty() {
                        categories.push(traits::PatternMatcher::name(e).to_string());
                        matches.extend(engine_matches);
                    }
                }
            };
        }

        // Run all 8 super-engines
        run_engine!(self.injection);
        run_engine!(self.jailbreak);
        run_engine!(self.pii);
        run_engine!(self.exfiltration);
        run_engine!(self.moderation);
        run_engine!(self.evasion);
        run_engine!(self.tool_abuse);
        run_engine!(self.social);

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
    pub fn analyze_categories(&self, text: &str, _categories: Vec<String>) -> PyResult<AnalysisResult> {
        // TODO: Filter to specific categories
        self.analyze(text)
    }
}
