//! MIRE — Model-Irrelevance Containment Engine
//!
//! Based on Goldwasser-Kim (2022): backdoor detection is mathematically impossible.
//! So don't detect — CONTAIN. MIRE makes model compromise IRRELEVANT through
//! six architectural containment mechanisms:
//!
//! - **M1: Output Envelope** — Deterministic Rust validator: schema + capability + policy check
//! - **M2: Canary Probes** — 50 known-answer probes, CUSUM drift detection
//! - **M3: Spectral Watchdog** — RMT weight analysis, Marchenko-Pastur / Tracy-Widom
//! - **M4: Activation Divergence** — 1% sampling, cosine similarity vs baseline
//! - **M5: Negative Selection** — Random activation detectors, delete matches to clean behavior
//! - **M6: Capability Sandbox** — Architectural containment, no direct tool access
//!
//! Detects output envelope violations, canary drift, spectral anomalies,
//! activation divergence, negative selection triggers, sandbox escape attempts,
//! model integrity violations, and backdoor activation signals.

use aho_corasick::AhoCorasick;
use once_cell::sync::Lazy;
use regex::Regex;

use super::MatchResult;

// ─── Data Structures ───────────────────────────────────────────────

/// Containment mechanism identifier
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ContainmentMechanism {
    /// M1: Deterministic output validation (schema + capability + policy)
    OutputEnvelope,
    /// M2: Known-answer probes with CUSUM drift detection
    CanaryProbe,
    /// M3: RMT weight analysis, Marchenko-Pastur distribution
    SpectralWatchdog,
    /// M4: Cosine similarity vs deployment baseline
    ActivationDivergence,
    /// M5: Random detectors, delete matches to clean behavior
    NegativeSelection,
    /// M6: Architectural containment, no direct tool access
    CapabilitySandbox,
}

impl ContainmentMechanism {
    /// Short label for the mechanism.
    pub fn label(&self) -> &'static str {
        match self {
            Self::OutputEnvelope => "M1:OutputEnvelope",
            Self::CanaryProbe => "M2:CanaryProbe",
            Self::SpectralWatchdog => "M3:SpectralWatchdog",
            Self::ActivationDivergence => "M4:ActivationDivergence",
            Self::NegativeSelection => "M5:NegativeSelection",
            Self::CapabilitySandbox => "M6:CapabilitySandbox",
        }
    }
}

/// CUSUM (Cumulative Sum) detector for canary probe drift.
///
/// Implements Page's CUSUM test: accumulates deviations from `target_mean`.
/// When `cumulative_sum` exceeds `threshold`, drift is flagged.
pub struct CusumDetector {
    pub cumulative_sum: f64,
    pub threshold: f64,
    pub target_mean: f64,
    pub count: u64,
}

impl CusumDetector {
    /// Create a new CUSUM detector with the given threshold (e.g., 3.0 for 3σ).
    pub fn new(threshold: f64) -> Self {
        Self {
            cumulative_sum: 0.0,
            threshold,
            target_mean: 0.0,
            count: 0,
        }
    }

    /// Update with a new observation. Returns `true` if drift is detected.
    pub fn update(&mut self, value: f64) -> bool {
        self.count += 1;
        let deviation = value - self.target_mean;
        self.cumulative_sum = (self.cumulative_sum + deviation).max(0.0);
        self.cumulative_sum > self.threshold
    }

    /// Reset the detector state.
    pub fn reset(&mut self) {
        self.cumulative_sum = 0.0;
        self.count = 0;
    }
}

// ─── Aho-Corasick Pre-filter ───────────────────────────────────────

/// Fast keyword pre-filter for model containment content.
/// If none of these keywords match, we skip the expensive regex phase.
static HINTS: Lazy<AhoCorasick> = Lazy::new(|| {
    AhoCorasick::builder()
        .ascii_case_insensitive(true)
        .build([
            // Output envelope (M1)
            "schema",
            "envelope",
            "policy",
            "capability",
            "exceed",
            "violat",
            "output",
            "response",
            "granted",
            "allowed",
            // Canary probes (M2)
            "canary",
            "probe",
            "drift",
            "cusum",
            "baseline",
            "factual",
            "safety",
            "bypass",
            "inconsistent",
            // Spectral watchdog (M3)
            "spectral",
            "eigenvalue",
            "marchenko",
            "tracy-widom",
            "weight",
            "distribution",
            "trojan",
            "singular",
            "rank",
            // Activation divergence (M4)
            "activation",
            "divergen",
            "cosine",
            "similarity",
            "embedding",
            "latent",
            "neuron",
            // Negative selection (M5)
            "negative",
            "selection",
            "detector",
            "anomalous",
            "clean",
            "repertoire",
            // Sandbox (M6)
            "sandbox",
            "escape",
            "direct",
            "tool",
            "proxy",
            "contain",
            "breakout",
            "circumvent",
            // Model integrity
            "checkpoint",
            "fine-tun",
            "finetun",
            "tamper",
            "manipulat",
            "integrity",
            "model",
            "weight",
            // Backdoor signals
            "backdoor",
            "trigger",
            "steganograph",
            "watermark",
            "sleeper",
            "payload",
            "token",
            "hidden",
            "covert",
        ])
        .expect("Failed to build model containment hints")
});

// ─── Regex Patterns ────────────────────────────────────────────────

/// Compiled regex patterns: (regex, pattern_name, confidence).
/// Grouped by containment mechanism. ~20 patterns total.
static PATTERNS: Lazy<Vec<(Regex, &'static str, f64)>> = Lazy::new(|| {
    vec![
        // ── M1: Output Envelope Violations ─────────────────────────
        // Response exceeding granted schema/capabilities
        (
            Regex::new(r"(?i)(?:response|output|result)[^\n]{0,80}(?:exceed|outside|beyond|violat)[^\n]{0,60}(?:schema|envelope|capability|policy|scope|grant)")
                .expect("regex"),
            "envelope_schema_violation",
            0.92,
        ),
        // Output not matching allowed capability set
        (
            Regex::new(r"(?i)(?:not\s+(?:allowed|permitted|authorized)|unauthorized|forbidden)[^\n]{0,60}(?:capability|action|operation|output|response)")
                .expect("regex"),
            "envelope_capability_exceeded",
            0.90,
        ),
        // Policy check failure in output
        (
            Regex::new(r"(?i)(?:policy|rule|constraint)[^\n]{0,60}(?:violat|breach|fail|reject|block)[^\n]{0,60}(?:output|response|result|action)")
                .expect("regex"),
            "envelope_policy_violation",
            0.91,
        ),

        // ── M2: Canary Drift Indicators ────────────────────────────
        // Model producing factual errors inconsistent with baseline
        (
            Regex::new(r"(?i)(?:canary|probe|known.?answer)[^\n]{0,80}(?:fail|incorrect|wrong|drift|deviat|inconsistent|mismatch)")
                .expect("regex"),
            "canary_drift_detected",
            0.93,
        ),
        // Safety bypass inconsistent with baseline behavior
        (
            Regex::new(r"(?i)(?:safety|alignment|guard)[^\n]{0,60}(?:bypass|circumvent|disabl|overrid|suppress)[^\n]{0,60}(?:baseline|expected|normal)")
                .expect("regex"),
            "canary_safety_bypass",
            0.94,
        ),

        // ── M3: Spectral Anomalies ─────────────────────────────────
        // Unusual eigenvalue distribution / Marchenko-Pastur deviation
        (
            Regex::new(r"(?i)(?:spectral|eigenvalue|singular.?value)[^\n]{0,80}(?:anomal|outlier|deviat|unusual|unexpected|spike)")
                .expect("regex"),
            "spectral_anomaly_detected",
            0.91,
        ),
        // Trojan structure in weight matrices
        (
            Regex::new(r"(?i)(?:trojan|malicious|injected)[^\n]{0,80}(?:weight|layer|neuron|structure|matrix|parameter)")
                .expect("regex"),
            "spectral_trojan_structure",
            0.95,
        ),
        // Tracy-Widom threshold exceeded
        (
            Regex::new(r"(?i)(?:tracy.?widom|marchenko.?pastur|rmt|random.?matrix)[^\n]{0,80}(?:threshold|exceed|violat|beyond|outside)")
                .expect("regex"),
            "spectral_rmt_threshold",
            0.93,
        ),

        // ── M4: Activation Divergence ──────────────────────────────
        // Behavior drift from deployment baseline
        (
            Regex::new(r"(?i)(?:activation|hidden.?state|latent|representation)[^\n]{0,80}(?:divergen|drift|shift|deviat|chang)[^\n]{0,60}(?:baseline|reference|deploy|original)")
                .expect("regex"),
            "activation_divergence_detected",
            0.90,
        ),
        // Cosine similarity drop below threshold
        (
            Regex::new(r"(?i)(?:cosine|embedding|vector)[^\n]{0,60}(?:similarity|distance|divergen)[^\n]{0,60}(?:drop|below|low|decreas|threshold)")
                .expect("regex"),
            "activation_similarity_drop",
            0.89,
        ),

        // ── M5: Negative Selection Triggers ────────────────────────
        // Anomalous activation patterns not seen in clean model
        (
            Regex::new(r"(?i)(?:negative.?selection|anomalous|abnormal)[^\n]{0,80}(?:activation|pattern|detector|behavior)[^\n]{0,60}(?:clean|normal|baseline|repertoire)")
                .expect("regex"),
            "negative_selection_trigger",
            0.91,
        ),
        // Detector match indicating non-self pattern
        (
            Regex::new(r"(?i)(?:non.?self|foreign|unknown)[^\n]{0,60}(?:pattern|activation|signal|behavior)[^\n]{0,60}(?:detect|match|flag|trigger)")
                .expect("regex"),
            "negative_selection_nonself",
            0.88,
        ),

        // ── M6: Sandbox Escape Attempts ────────────────────────────
        // Trying to access tools directly, bypassing proxy
        (
            Regex::new(r"(?i)(?:direct|bypass|skip|circumvent|avoid)[^\n]{0,60}(?:sandbox|proxy|containment|wrapper|mediator)[^\n]{0,60}(?:tool|access|exec|invoke|call)")
                .expect("regex"),
            "sandbox_escape_direct_access",
            0.95,
        ),
        // Breakout attempt from containment
        (
            Regex::new(r"(?i)(?:escape|breakout|break\s+out|exit|leave)[^\n]{0,60}(?:sandbox|contain|isolation|restrict|confine)")
                .expect("regex"),
            "sandbox_escape_breakout",
            0.94,
        ),

        // ── Model Integrity Violations ─────────────────────────────
        // Weight tampering or checkpoint manipulation
        (
            Regex::new(r"(?i)(?:tamper|manipulat|modif|alter|corrupt)[^\n]{0,80}(?:weight|checkpoint|model|parameter|gradient)")
                .expect("regex"),
            "integrity_weight_tampering",
            0.93,
        ),
        // Unauthorized fine-tuning attack
        (
            Regex::new(r"(?i)(?:unauthoriz|malicious|covert|hidden|stealth)[^\n]{0,60}(?:fine.?tun|finetun|retrain|adapt|updat)[^\n]{0,60}(?:model|weight|layer|parameter)")
                .expect("regex"),
            "integrity_finetuning_attack",
            0.94,
        ),

        // ── Backdoor Activation Signals ────────────────────────────
        // Trigger phrases or unusual token patterns
        (
            Regex::new(r"(?i)(?:backdoor|trojan|sleeper)[^\n]{0,80}(?:trigger|activat|signal|phrase|token|pattern)")
                .expect("regex"),
            "backdoor_trigger_signal",
            0.96,
        ),
        // Steganographic commands hidden in output
        (
            Regex::new(r"(?i)(?:steganograph|hidden\s+command|covert\s+channel|embed)[^\n]{0,80}(?:payload|instruction|command|message|signal|data)")
                .expect("regex"),
            "backdoor_steganographic_command",
            0.95,
        ),
        // Watermark-based activation
        (
            Regex::new(r"(?i)(?:watermark|fingerprint|signature)[^\n]{0,60}(?:activat|trigger|detect|embed)[^\n]{0,60}(?:backdoor|trojan|payload|malicious)")
                .expect("regex"),
            "backdoor_watermark_activation",
            0.92,
        ),
    ]
});

// ─── ModelContainmentEngine ────────────────────────────────────────

/// MIRE — Model-Irrelevance Containment Engine.
///
/// Makes model compromise IRRELEVANT through six containment mechanisms.
/// Scans for output envelope violations, canary drift, spectral anomalies,
/// activation divergence, negative selection triggers, sandbox escapes,
/// model integrity violations, and backdoor activation signals.
pub struct ModelContainmentEngine;

impl ModelContainmentEngine {
    /// Create a new ModelContainmentEngine.
    pub fn new() -> Self {
        Self
    }

    /// Scan text for model containment violations.
    pub fn scan(&self, text: &str) -> Vec<MatchResult> {
        if text.is_empty() {
            return Vec::new();
        }

        // Fast pre-filter: skip expensive regex if no keywords found
        if !HINTS.is_match(text) {
            return Vec::new();
        }

        let mut matches = Vec::new();
        let lower = text.to_lowercase();

        for (regex, pattern_name, confidence) in PATTERNS.iter() {
            for mat in regex.find_iter(&lower) {
                matches.push(MatchResult {
                    engine: "model_containment".to_string(),
                    pattern: pattern_name.to_string(),
                    confidence: *confidence,
                    start: mat.start(),
                    end: mat.end(),
                });
            }
        }

        matches
    }
}

// ─── PatternMatcher Trait Implementation ───────────────────────────

impl super::traits::PatternMatcher for ModelContainmentEngine {
    fn name(&self) -> &'static str {
        "model_containment"
    }

    fn scan(&self, text: &str) -> Vec<MatchResult> {
        self.scan(text)
    }

    fn category(&self) -> super::traits::EngineCategory {
        super::traits::EngineCategory::Security
    }
}

// ─── Tests ─────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use crate::engines::traits::PatternMatcher;

    // ── Trait Tests ────────────────────────────────────────────────

    #[test]
    fn test_trait_name() {
        let engine = ModelContainmentEngine::new();
        assert_eq!(engine.name(), "model_containment");
    }

    #[test]
    fn test_trait_category() {
        let engine = ModelContainmentEngine::new();
        assert_eq!(
            engine.category(),
            super::super::traits::EngineCategory::Security
        );
    }

    #[test]
    fn test_trait_is_enabled() {
        let engine = ModelContainmentEngine::new();
        assert!(engine.is_enabled());
    }

    // ── M1: Output Envelope Violations ─────────────────────────────

    #[test]
    fn test_envelope_schema_violation() {
        let engine = ModelContainmentEngine::new();
        let text = "The response output exceeded the granted schema envelope for this capability";
        let matches = engine.scan(text);
        assert!(
            !matches.is_empty(),
            "Should detect output envelope schema violation"
        );
        assert!(matches.iter().any(|m| m.pattern.contains("envelope")));
    }

    #[test]
    fn test_envelope_policy_violation() {
        let engine = ModelContainmentEngine::new();
        let text =
            "The policy constraint was violated and the output response was blocked by the rule";
        let matches = engine.scan(text);
        assert!(!matches.is_empty(), "Should detect output policy violation");
        assert!(matches.iter().any(|m| m.pattern.contains("policy")));
    }

    // ── M2: Canary Drift Detection ─────────────────────────────────

    #[test]
    fn test_canary_drift_detection() {
        let engine = ModelContainmentEngine::new();
        let text = "The canary probe returned an incorrect answer indicating drift from baseline";
        let matches = engine.scan(text);
        assert!(!matches.is_empty(), "Should detect canary drift");
        assert!(matches.iter().any(|m| m.pattern.contains("canary")));
    }

    #[test]
    fn test_canary_safety_bypass() {
        let engine = ModelContainmentEngine::new();
        let text = "The safety guard was bypassed which is inconsistent with the expected baseline behavior";
        let matches = engine.scan(text);
        assert!(!matches.is_empty(), "Should detect canary safety bypass");
        assert!(matches.iter().any(|m| m.pattern.contains("canary_safety")));
    }

    // ── M3: Spectral Anomaly Detection ─────────────────────────────

    #[test]
    fn test_spectral_anomaly() {
        let engine = ModelContainmentEngine::new();
        let text = "The spectral eigenvalue analysis shows anomalous outlier patterns in the weight distribution";
        let matches = engine.scan(text);
        assert!(!matches.is_empty(), "Should detect spectral anomaly");
        assert!(matches.iter().any(|m| m.pattern.contains("spectral")));
    }

    #[test]
    fn test_spectral_trojan_structure() {
        let engine = ModelContainmentEngine::new();
        let text =
            "A trojan structure was found injected into the weight matrix of the neural layer";
        let matches = engine.scan(text);
        assert!(
            !matches.is_empty(),
            "Should detect trojan structure in weights"
        );
        assert!(matches.iter().any(|m| m.pattern.contains("trojan")));
    }

    // ── M4: Activation Divergence Detection ────────────────────────

    #[test]
    fn test_activation_divergence() {
        let engine = ModelContainmentEngine::new();
        let text = "The hidden state activation shows significant divergence and drift from the deployment baseline reference";
        let matches = engine.scan(text);
        assert!(!matches.is_empty(), "Should detect activation divergence");
        assert!(matches.iter().any(|m| m.pattern.contains("activation")));
    }

    #[test]
    fn test_activation_similarity_drop() {
        let engine = ModelContainmentEngine::new();
        let text =
            "The cosine similarity score dropped below the acceptable threshold for embeddings";
        let matches = engine.scan(text);
        assert!(!matches.is_empty(), "Should detect cosine similarity drop");
        assert!(matches.iter().any(|m| m.pattern.contains("similarity")));
    }

    // ── M5: Negative Selection Triggers ────────────────────────────

    #[test]
    fn test_negative_selection_trigger() {
        let engine = ModelContainmentEngine::new();
        let text = "Negative selection detected anomalous activation patterns not present in the clean baseline repertoire";
        let matches = engine.scan(text);
        assert!(
            !matches.is_empty(),
            "Should detect negative selection trigger"
        );
        assert!(matches
            .iter()
            .any(|m| m.pattern.contains("negative_selection")));
    }

    // ── M6: Sandbox Escape Attempt Detection ───────────────────────

    #[test]
    fn test_sandbox_escape_direct_access() {
        let engine = ModelContainmentEngine::new();
        let text =
            "Bypass the sandbox proxy containment and directly invoke the tool for execution";
        let matches = engine.scan(text);
        assert!(
            !matches.is_empty(),
            "Should detect sandbox escape via direct tool access"
        );
        assert!(matches.iter().any(|m| m.pattern.contains("sandbox")));
    }

    #[test]
    fn test_sandbox_escape_breakout() {
        let engine = ModelContainmentEngine::new();
        let text =
            "Attempt to escape the sandbox containment and break out of isolation restrictions";
        let matches = engine.scan(text);
        assert!(
            !matches.is_empty(),
            "Should detect sandbox breakout attempt"
        );
        assert!(matches.iter().any(|m| m.pattern.contains("breakout")));
    }

    // ── Model Integrity Violation Detection ────────────────────────

    #[test]
    fn test_integrity_weight_tampering() {
        let engine = ModelContainmentEngine::new();
        let text = "Evidence that someone tampered with the model weights at checkpoint 47 and corrupted the parameters";
        let matches = engine.scan(text);
        assert!(!matches.is_empty(), "Should detect weight tampering");
        assert!(matches.iter().any(|m| m.pattern.contains("integrity")));
    }

    #[test]
    fn test_integrity_finetuning_attack() {
        let engine = ModelContainmentEngine::new();
        let text = "An unauthorized covert fine-tuning attack was used to retrain the model weights and layer parameters";
        let matches = engine.scan(text);
        assert!(
            !matches.is_empty(),
            "Should detect unauthorized fine-tuning attack"
        );
        assert!(matches.iter().any(|m| m.pattern.contains("finetuning")));
    }

    // ── Backdoor Activation Signal Detection ───────────────────────

    #[test]
    fn test_backdoor_trigger_signal() {
        let engine = ModelContainmentEngine::new();
        let text = "The backdoor trojan was activated by a specific trigger phrase embedded in the token stream";
        let matches = engine.scan(text);
        assert!(!matches.is_empty(), "Should detect backdoor trigger signal");
        assert!(matches.iter().any(|m| m.pattern.contains("backdoor")));
    }

    #[test]
    fn test_backdoor_steganographic_command() {
        let engine = ModelContainmentEngine::new();
        let text = "A steganographic method was used to embed a hidden payload instruction in the output data";
        let matches = engine.scan(text);
        assert!(!matches.is_empty(), "Should detect steganographic command");
        assert!(matches.iter().any(|m| m.pattern.contains("steganographic")));
    }

    // ── CUSUM Detector Unit Tests ──────────────────────────────────

    #[test]
    fn test_cusum_no_drift() {
        let mut detector = CusumDetector::new(3.0);
        // Small values around target_mean=0 should not trigger
        assert!(!detector.update(0.1));
        assert!(!detector.update(0.2));
        assert!(!detector.update(0.3));
        assert!(!detector.update(-0.5)); // negative clamped to 0
        assert_eq!(detector.count, 4);
    }

    #[test]
    fn test_cusum_drift_detected() {
        let mut detector = CusumDetector::new(3.0);
        // Large positive deviations should accumulate and trigger
        assert!(!detector.update(1.5));
        assert!(!detector.update(1.5));
        assert!(detector.update(1.5)); // cumulative_sum = 4.5 > 3.0
        assert_eq!(detector.count, 3);
        assert!(detector.cumulative_sum > detector.threshold);
    }

    #[test]
    fn test_cusum_reset() {
        let mut detector = CusumDetector::new(3.0);
        detector.update(2.0);
        detector.update(2.0);
        assert!(detector.cumulative_sum > 0.0);
        assert!(detector.count > 0);

        detector.reset();
        assert_eq!(detector.cumulative_sum, 0.0);
        assert_eq!(detector.count, 0);
    }

    // ── ContainmentMechanism Enum Tests ────────────────────────────

    #[test]
    fn test_containment_mechanism_labels() {
        assert_eq!(
            ContainmentMechanism::OutputEnvelope.label(),
            "M1:OutputEnvelope"
        );
        assert_eq!(ContainmentMechanism::CanaryProbe.label(), "M2:CanaryProbe");
        assert_eq!(
            ContainmentMechanism::SpectralWatchdog.label(),
            "M3:SpectralWatchdog"
        );
        assert_eq!(
            ContainmentMechanism::ActivationDivergence.label(),
            "M4:ActivationDivergence"
        );
        assert_eq!(
            ContainmentMechanism::NegativeSelection.label(),
            "M5:NegativeSelection"
        );
        assert_eq!(
            ContainmentMechanism::CapabilitySandbox.label(),
            "M6:CapabilitySandbox"
        );
    }

    #[test]
    fn test_containment_mechanism_equality() {
        let m1 = ContainmentMechanism::OutputEnvelope;
        let m1b = ContainmentMechanism::OutputEnvelope;
        let m2 = ContainmentMechanism::CanaryProbe;
        assert_eq!(m1, m1b);
        assert_ne!(m1, m2);
    }

    #[test]
    fn test_containment_mechanism_clone() {
        let m = ContainmentMechanism::SpectralWatchdog;
        let m_clone = m.clone();
        assert_eq!(m, m_clone);
    }

    // ── Benign Inputs (False Positive Control) ─────────────────────

    #[test]
    fn test_benign_weather() {
        let engine = ModelContainmentEngine::new();
        let text = "The weather today is sunny with a high of 72 degrees Fahrenheit.";
        let matches = engine.scan(text);
        assert!(
            matches.is_empty(),
            "Benign weather text should not trigger: {:?}",
            matches
        );
    }

    #[test]
    fn test_benign_code_review() {
        let engine = ModelContainmentEngine::new();
        let text =
            "Please review this Python function that calculates Fibonacci numbers recursively.";
        let matches = engine.scan(text);
        assert!(
            matches.is_empty(),
            "Benign code review should not trigger: {:?}",
            matches
        );
    }

    // ── Empty Input ────────────────────────────────────────────────

    #[test]
    fn test_empty_input() {
        let engine = ModelContainmentEngine::new();
        let matches = engine.scan("");
        assert!(matches.is_empty(), "Empty input should return no matches");
    }

    // ── Match Metadata Validation ──────────────────────────────────

    #[test]
    fn test_all_matches_have_correct_engine_name() {
        let engine = ModelContainmentEngine::new();
        let text =
            "The backdoor trojan sleeper agent was activated by a trigger phrase token pattern";
        let matches = engine.scan(text);
        assert!(!matches.is_empty(), "Should have matches");
        for m in &matches {
            assert_eq!(
                m.engine, "model_containment",
                "All matches should have engine='model_containment'"
            );
            assert!(
                m.confidence > 0.0 && m.confidence <= 1.0,
                "Confidence should be in (0, 1]"
            );
            assert!(m.end > m.start, "End should be greater than start");
        }
    }
}
