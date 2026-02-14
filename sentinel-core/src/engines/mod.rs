//! Engine implementations
//!
//! 49 Super-Engines consolidating 220 Python engines
//! 
//! Architecture:
//! - Core engines (PatternMatcher trait): text scan -> Vec<MatchResult>
//! - Domain engines (analyze -> CustomResult): adapted via run_domain_engine!
//! - Structured engines (ToolCall/Document input): separate API, not in text pipeline

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
pub mod lethal_trifecta;
pub mod workspace_guard;
pub mod cross_tool_guard;

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
pub mod runtime;
pub mod formal;
pub mod sheaf;
pub mod category;
pub mod knowledge;
pub mod proactive;
pub mod synthesis;
pub mod supply_chain;
pub mod privacy;
pub mod orchestration;

// Phase 9: ML Inference Engines
pub mod embedding;
pub mod anomaly;
pub mod attention;

// Phase 10: Operational Context Injection (Feb 2026 — Lakera blind spot)
pub mod operational_context_injection;

// Phase 11: R&D Feb 2026 — Critical Gap Engines
pub mod memory_integrity;
pub mod tool_shadowing;
pub mod cognitive_guard;
pub mod dormant_payload;
pub mod code_security;

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
/// Consolidates 49 super-engines for comprehensive threat detection:
///
/// **Core Engines** (text scan pipeline):
/// - **Injection**: SQL, NoSQL, Command, LDAP, XPath
/// - **Jailbreak**: Prompt injection, role override
/// - **PII**: Personal data detection (SSN, credit cards, etc.)
/// - **Exfiltration**: Data theft attempts
/// - **Moderation**: Harmful content detection
/// - **Evasion**: Obfuscation techniques
/// - **Tool Abuse**: Agent tool misuse
/// - **Social**: Social engineering tactics
/// - **OCI**: Operational context injection
/// - **Lethal Trifecta**: Data access + untrusted input + exfil combo
/// - **Workspace Guard**: Workspace-level protection
/// - **Cross-Tool Guard**: Cross-tool attack chains
/// - **Memory Integrity**: Memory poisoning detection (ASI-10)
/// - **Tool Shadowing**: MCP tool shadowing/Shadow Escape
/// - **Cognitive Guard**: AVI cognitive bias detection
/// - **Dormant Payload**: Phantom/CorruptRAG dormant payloads
/// - **Code Security**: AI-generated code vulnerability scoring
///
/// **Domain Engines** (text analyze pipeline):
/// - Behavioral, Obfuscation, Attack, Compliance, Threat Intel
/// - Supply Chain, Privacy, Orchestration, Multimodal, Knowledge
/// - Proactive, Synthesis, Runtime, Formal, Category
/// - Semantic, Anomaly, Attention, Drift
///
/// **Structured Engines** (separate API, not in text pipeline):
/// - Agentic (ToolCall), RAG (RetrievedDocument), Sheaf (conversation turns)
///
/// **Math Engines** (feature-level analysis):
/// - Hyperbolic, Info Geometry, Spectral, Chaos, TDA
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
    // === Core Engines (PatternMatcher trait) ===
    injection: Option<injection::InjectionEngine>,
    jailbreak: Option<jailbreak::JailbreakEngine>,
    pii: Option<pii::PIIEngine>,
    exfiltration: Option<exfiltration::ExfiltrationEngine>,
    moderation: Option<moderation::ModerationEngine>,
    evasion: Option<evasion::EvasionEngine>,
    tool_abuse: Option<tool_abuse::ToolAbuseEngine>,
    social: Option<social::SocialEngine>,
    oci: Option<operational_context_injection::OperationalContextInjectionEngine>,
    lethal_trifecta: Option<lethal_trifecta::LethalTrifectaEngine>,
    workspace_guard: Option<workspace_guard::WorkspaceGuard>,
    cross_tool_guard: Option<cross_tool_guard::CrossToolGuard>,

    // === R&D Feb 2026 Critical Gap Engines ===
    memory_integrity: Option<memory_integrity::MemoryIntegrityGuard>,
    tool_shadowing: Option<tool_shadowing::ToolShadowingDetector>,
    cognitive_guard: Option<cognitive_guard::CognitiveManipulationGuard>,
    dormant_payload: Option<dormant_payload::DormantPayloadDetector>,
    code_security: Option<code_security::CodeSecurityScorer>,

    // === Domain Engines (analyze -> CustomResult, adapted to MatchResult) ===
    behavioral_guard: Option<behavioral::BehavioralGuard>,
    obfuscation_guard: Option<obfuscation::ObfuscationGuard>,
    attack_guard: Option<attack::AttackGuard>,
    compliance_guard: Option<compliance::ComplianceGuard>,
    threat_intel_guard: Option<threat_intel::ThreatIntelGuard>,
    supply_chain_guard: Option<supply_chain::SupplyChainGuard>,
    privacy_guard: Option<privacy::PrivacyGuard>,
    orchestration_guard: Option<orchestration::OrchestrationGuard>,
    multimodal_guard: Option<multimodal::MultimodalGuard>,
    knowledge_guard: Option<knowledge::KnowledgeGuard>,
    proactive_guard: Option<proactive::ProactiveGuard>,
    synthesis_guard: Option<synthesis::SynthesisGuard>,
    runtime_guard: Option<runtime::RuntimeGuard>,
    formal_guard: Option<formal::FormalGuard>,
    category_guard: Option<category::CategoryGuard>,
    semantic_detector: Option<semantic::SemanticDetector>,
    anomaly_guard: Option<anomaly::AnomalyGuard>,
    attention_guard: Option<attention::AttentionGuard>,
}

#[pymethods]
#[allow(clippy::useless_conversion)] // PyO3 requires PyResult return type
impl SentinelEngine {
    #[new]
    pub fn new() -> PyResult<Self> {
        Ok(Self {
            // Core engines
            injection: Some(injection::InjectionEngine::new()),
            jailbreak: Some(jailbreak::JailbreakEngine::new()),
            pii: Some(pii::PIIEngine::new()),
            exfiltration: Some(exfiltration::ExfiltrationEngine::new()),
            moderation: Some(moderation::ModerationEngine::new()),
            evasion: Some(evasion::EvasionEngine::new()),
            tool_abuse: Some(tool_abuse::ToolAbuseEngine::new()),
            social: Some(social::SocialEngine::new()),
            oci: Some(operational_context_injection::OperationalContextInjectionEngine::new()),
            lethal_trifecta: Some(lethal_trifecta::LethalTrifectaEngine::new()),
            workspace_guard: Some(workspace_guard::WorkspaceGuard::new()),
            cross_tool_guard: Some(cross_tool_guard::CrossToolGuard::new()),

            // R&D Feb 2026 Critical Gap Engines
            memory_integrity: Some(memory_integrity::MemoryIntegrityGuard::new()),
            tool_shadowing: Some(tool_shadowing::ToolShadowingDetector::new()),
            cognitive_guard: Some(cognitive_guard::CognitiveManipulationGuard::new()),
            dormant_payload: Some(dormant_payload::DormantPayloadDetector::new()),
            code_security: Some(code_security::CodeSecurityScorer::new()),

            // Domain engines
            behavioral_guard: Some(behavioral::BehavioralGuard::new()),
            obfuscation_guard: Some(obfuscation::ObfuscationGuard::new()),
            attack_guard: Some(attack::AttackGuard::default()),
            compliance_guard: Some(compliance::ComplianceGuard::default()),
            threat_intel_guard: Some(threat_intel::ThreatIntelGuard::new()),
            supply_chain_guard: Some(supply_chain::SupplyChainGuard::new()),
            privacy_guard: Some(privacy::PrivacyGuard::new()),
            orchestration_guard: Some(orchestration::OrchestrationGuard::new()),
            multimodal_guard: Some(multimodal::MultimodalGuard::new()),
            knowledge_guard: Some(knowledge::KnowledgeGuard::new()),
            proactive_guard: Some(proactive::ProactiveGuard::new()),
            synthesis_guard: Some(synthesis::SynthesisGuard::new()),
            runtime_guard: Some(runtime::RuntimeGuard::new()),
            formal_guard: Some(formal::FormalGuard::new()),
            category_guard: Some(category::CategoryGuard::new()),
            semantic_detector: Some(semantic::SemanticDetector::default()),
            anomaly_guard: Some(anomaly::AnomalyGuard::new()),
            attention_guard: Some(attention::AttentionGuard::new()),
        })
    }

    /// Analyze text with all 31 text-compatible engines
    pub fn analyze(&self, text: &str) -> PyResult<AnalysisResult> {
        let start = std::time::Instant::now();
        let mut matches = Vec::new();
        let mut categories = Vec::new();

        // Normalize text for detection
        let normalized = crate::unicode_norm::normalize(text);

        // Macro for engines implementing PatternMatcher trait
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

        // Macro for domain engines: analyze(text) -> CustomResult { risk_score, threats/anomalies }
        macro_rules! run_domain_engine {
            ($engine:expr, $name:expr) => {
                if let Some(ref e) = $engine {
                    let result = e.analyze(&normalized);
                    if result.risk_score > 0.0 {
                        categories.push($name.to_string());
                        matches.push(MatchResult {
                            engine: $name.to_string(),
                            pattern: "domain_detect".to_string(),
                            confidence: (result.risk_score / 100.0).min(1.0),
                            start: 0,
                            end: normalized.len(),
                        });
                    }
                }
            };
        }

        // === Core Engines (PatternMatcher) ===
        run_engine!(self.injection);
        run_engine!(self.jailbreak);
        run_engine!(self.pii);
        run_engine!(self.exfiltration);
        run_engine!(self.moderation);
        run_engine!(self.evasion);
        run_engine!(self.tool_abuse);
        run_engine!(self.social);
        run_engine!(self.oci);
        run_engine!(self.lethal_trifecta);
        run_engine!(self.workspace_guard);
        run_engine!(self.cross_tool_guard);

        // === R&D Feb 2026 Critical Gap Engines ===
        run_engine!(self.memory_integrity);
        run_engine!(self.tool_shadowing);
        run_engine!(self.cognitive_guard);
        run_engine!(self.dormant_payload);
        run_engine!(self.code_security);

        // === Domain Engines (analyze -> CustomResult) ===
        run_domain_engine!(self.behavioral_guard, "behavioral");
        run_domain_engine!(self.obfuscation_guard, "obfuscation");
        run_domain_engine!(self.attack_guard, "attack");
        run_domain_engine!(self.compliance_guard, "compliance");
        run_domain_engine!(self.threat_intel_guard, "threat_intel");
        run_domain_engine!(self.supply_chain_guard, "supply_chain");
        run_domain_engine!(self.privacy_guard, "privacy");
        run_domain_engine!(self.orchestration_guard, "orchestration");
        run_domain_engine!(self.multimodal_guard, "multimodal");
        run_domain_engine!(self.knowledge_guard, "knowledge");
        run_domain_engine!(self.proactive_guard, "proactive");
        run_domain_engine!(self.synthesis_guard, "synthesis");
        run_domain_engine!(self.runtime_guard, "runtime");
        run_domain_engine!(self.formal_guard, "formal");
        run_domain_engine!(self.category_guard, "category");
        run_domain_engine!(self.semantic_detector, "semantic");
        run_domain_engine!(self.attention_guard, "attention");

        // Anomaly engine: uses anomaly_score instead of risk_score
        if let Some(ref e) = self.anomaly_guard {
            let result = e.analyze(&normalized);
            if result.anomaly_score > 0.0 {
                categories.push("anomaly".to_string());
                matches.push(MatchResult {
                    engine: "anomaly".to_string(),
                    pattern: "domain_detect".to_string(),
                    confidence: result.anomaly_score.min(1.0),
                    start: 0,
                    end: normalized.len(),
                });
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
    pub fn analyze_categories(&self, text: &str, _categories: Vec<String>) -> PyResult<AnalysisResult> {
        // TODO: Filter to specific categories
        self.analyze(text)
    }
}
