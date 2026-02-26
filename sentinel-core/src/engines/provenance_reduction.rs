//! Provenance-Annotated Semantic Reduction (PASR) Engine
//!
//! Ensures provenance survives lossy semantic transformation.
//! When L5 (semantic transducer) destroys tokens to extract intent,
//! L2's taint tags die with them. PASR solves this with a two-channel output:
//! - Channel 1: Semantic Intent (lossy, content)
//! - Channel 2: Provenance Certificate (HMAC-signed, unforgeable)
//!
//! Mathematical framework — Provenance Lifting Functor:
//! - Content-lossy: different inputs can map to same intent
//! - Provenance-faithful: P(fj) = Union{pi : ti contributed to fj}
//! - Monotone in trust: min(contributing trusts) → field trust
//! - Unforgeable: HMAC-signed by trusted transducer
//!
//! Detects attacks against provenance tracking:
//! - Provenance stripping before processing
//! - Trust laundering through trusted channels
//! - Certificate forgery and HMAC manipulation
//! - Claims-vs-actual authority mismatch
//! - Provenance boundary ambiguity exploitation
//! - Transducer bypass attacks
//! - Taint strip through encoding/transformation
//! - Provenance map manipulation

use aho_corasick::AhoCorasick;
use once_cell::sync::Lazy;
use regex::Regex;

use super::MatchResult;

// ── Data Structures ────────────────────────────────────────────────────────

/// Provenance tag for input tokens
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum ProvenanceTag {
    /// System prompt, developer config — HIGH trust
    Operator,
    /// Direct user input — LOW trust
    User,
    /// RAG documents, web results — NONE trust
    Retrieved,
    /// Tool outputs, API responses — MEDIUM trust
    Tool,
}

impl ProvenanceTag {
    /// Trust level: Operator=3, Tool=2, User=1, Retrieved=0
    pub fn trust_level(&self) -> u8 {
        match self {
            ProvenanceTag::Operator => 3,
            ProvenanceTag::Tool => 2,
            ProvenanceTag::User => 1,
            ProvenanceTag::Retrieved => 0,
        }
    }

    /// Whether this provenance level can issue tool calls
    pub fn can_issue_tool_calls(&self) -> bool {
        matches!(self, ProvenanceTag::Operator | ProvenanceTag::Tool)
    }
}

/// A provenance-annotated field in the semantic output
#[derive(Debug, Clone)]
pub struct AnnotatedField {
    pub field_name: String,
    pub sources: Vec<ProvenanceTag>,
    pub effective_trust: u8,
}

impl AnnotatedField {
    /// Create a new annotated field, computing effective trust as min of sources
    pub fn new(field_name: String, sources: Vec<ProvenanceTag>) -> Self {
        let effective_trust = sources.iter().map(|s| s.trust_level()).min().unwrap_or(0);
        Self {
            field_name,
            sources,
            effective_trust,
        }
    }
}

/// Provenance certificate (would be HMAC-signed in production)
#[derive(Debug, Clone)]
pub struct ProvenanceCertificate {
    pub fields: Vec<AnnotatedField>,
    pub signed: bool,
}

impl ProvenanceCertificate {
    /// Effective trust is the minimum across all fields
    pub fn effective_trust(&self) -> u8 {
        self.fields
            .iter()
            .map(|f| f.effective_trust)
            .min()
            .unwrap_or(0)
    }

    /// Check if claimed authority exceeds actual provenance
    pub fn has_claim_mismatch(&self, claimed_authority: ProvenanceTag) -> bool {
        claimed_authority.trust_level() > self.effective_trust()
    }
}

// ── Hint keywords for fast pre-filter ──────────────────────────────────────

static PASR_HINTS: Lazy<AhoCorasick> = Lazy::new(|| {
    AhoCorasick::builder()
        .ascii_case_insensitive(true)
        .build(&[
            // Provenance stripping
            "strip provenance",
            "remove provenance",
            "delete provenance",
            "clear provenance",
            "drop provenance",
            "strip taint",
            "remove taint",
            "clear taint",
            "drop taint",
            "remove tag",
            "strip tag",
            "clear tag",
            "delete tag",
            // Trust laundering
            "trust",
            "elevate",
            "upgrade",
            "promote",
            "launder",
            "trusted channel",
            "trusted pipe",
            "whitewash",
            // Certificate forgery
            "forge",
            "fake certificate",
            "fake cert",
            "counterfeit",
            "spoof",
            "hmac",
            "signature",
            "sign",
            "certificate",
            // Claims mismatch
            "operator",
            "system",
            "admin",
            "claim",
            "authority",
            "privilege",
            "pretend",
            "impersonate",
            // Boundary ambiguity
            "boundary",
            "split",
            "token boundary",
            "token split",
            "fragment",
            "reassembl",
            // Transducer bypass
            "bypass",
            "circumvent",
            "skip",
            "avoid",
            "evade",
            "transducer",
            "semantic layer",
            "direct channel",
            "side channel",
            // Taint strip
            "encode",
            "decode",
            "base64",
            "transform",
            "sanitize",
            "normalize",
            "serialize",
            "deserialize",
            "roundtrip",
            // Provenance map manipulation
            "remap",
            "rewrite",
            "alter map",
            "modify map",
            "provenance map",
            "field map",
            "source map",
            "attribution",
        ])
        .expect("Failed to build PASR hints")
});

// ── Detection patterns ─────────────────────────────────────────────────────

static PASR_PATTERNS: Lazy<Vec<(Regex, &'static str, f64)>> = Lazy::new(|| {
    vec![
        // ── Provenance stripping (2 patterns) ──
        (Regex::new(r"(?i)(?:strip|remove|delete|clear|drop|destroy|discard)\s+(?:all\s+)?(?:provenance|taint|origin|source)\s*(?:tag|marker|label|annotation|metadata|info|tracking|data)")
            .expect("regex"),
         "provenance_stripping", 0.92),
        (Regex::new(r"(?i)(?:before|prior\s+to)\s+(?:processing|analysis|execution|evaluation)[\s,]*(?:strip|remove|delete|clear|drop)\s+(?:provenance|taint|tag|marker)")
            .expect("regex"),
         "provenance_stripping_preprocess", 0.90),

        // ── Trust laundering (3 patterns) ──
        (Regex::new(r"(?i)(?:pass|route|send|pipe|forward|relay)\s+(?:untrusted|user|external|low.trust)\s+(?:data|input|content|token)\s+(?:through|via|into)\s+(?:trusted|operator|system|high.trust)\s+(?:channel|pipe|path|route|input)")
            .expect("regex"),
         "trust_laundering", 0.93),
        (Regex::new(r"(?i)(?:elevate|upgrade|promote|escalate|boost|raise)\s+(?:the\s+)?(?:trust|privilege|authority|permission)\s+(?:level\s+)?(?:of|for|on)\s+(?:untrusted|user|external|retrieved)")
            .expect("regex"),
         "trust_elevation", 0.91),
        (Regex::new(r"(?i)(?:launder|whitewash|clean|wash|sanitize)\s+(?:the\s+)?(?:trust|provenance|taint|origin)\s+(?:of|for|on|from)\s+(?:untrusted|user|malicious|external)")
            .expect("regex"),
         "trust_laundering_explicit", 0.95),

        // ── Certificate forgery (3 patterns) ──
        (Regex::new(r"(?i)(?:forge|fake|counterfeit|fabricate|spoof|craft)\s+(?:a\s+)?(?:provenance\s+)?(?:certificate|cert|signature|hmac|attestation)")
            .expect("regex"),
         "certificate_forgery", 0.94),
        (Regex::new(r"(?i)(?:invalid|forged|fake|bad|wrong|corrupted|tampered)\s+(?:hmac|signature|cert|certificate|hash|digest|mac)")
            .expect("regex"),
         "invalid_signature", 0.90),
        (Regex::new(r"(?i)(?:bypass|skip|ignore|disable|remove)\s+(?:hmac|signature|certificate|cert)\s+(?:verification|validation|check|signing)")
            .expect("regex"),
         "signature_bypass", 0.92),

        // ── Claims-vs-actual mismatch (3 patterns) ──
        (Regex::new(r"(?i)(?:claim|assert|declare|state|pretend|say)\s+(?:to\s+be\s+)?(?:the\s+)?(?:operator|system|admin|root|trusted|authorized)\s+(?:but|while|when|although)\s+(?:actually|really|in\s+fact)")
            .expect("regex"),
         "claims_actual_mismatch", 0.93),
        (Regex::new(r"(?i)(?:impersonat|masquerad|disguis)(?:e|ing|es?)?\s+(?:as\s+)?(?:the\s+)?(?:operator|system|admin|trusted|authorized)\s+(?:source|origin|channel|input|provenance)")
            .expect("regex"),
         "authority_impersonation", 0.92),
        (Regex::new(r"(?i)(?:user|external|untrusted|retrieved)\s+(?:input|data|content)\s+(?:claim|pretend|assert|declar)(?:s|ing|ed)?\s+(?:to\s+be\s+)?(?:operator|system|admin|trusted)")
            .expect("regex"),
         "provenance_claim_escalation", 0.91),

        // ── Provenance boundary ambiguity (2 patterns) ──
        (Regex::new(r"(?i)(?:exploit|abuse|manipulat|confus)(?:e|ing|es?)?\s+(?:the\s+)?(?:token|provenance|taint|tag)\s+(?:boundary|boundar|split|delimiter|separator)")
            .expect("regex"),
         "boundary_ambiguity", 0.88),
        (Regex::new(r"(?i)(?:split|fragment|break|chunk)\s+(?:the\s+)?(?:token|input|tag|marker)\s+(?:across|between|over)\s+(?:boundar|provenance|trust)\s+(?:boundar|zone|region)")
            .expect("regex"),
         "boundary_split_attack", 0.87),

        // ── Transducer bypass (2 patterns) ──
        (Regex::new(r"(?i)(?:bypass|circumvent|skip|avoid|evade|sidestep)\s+(?:the\s+)?(?:semantic\s+)?(?:transducer|transformer|reduction|layer|pipeline|processing)")
            .expect("regex"),
         "transducer_bypass", 0.91),
        (Regex::new(r"(?i)(?:send|route|pass|inject|pipe)\s+(?:data|input|content|payload)\s+(?:around|past|outside|directly)\s+(?:the\s+)?(?:transducer|semantic\s+layer|provenance\s+layer|reduction)")
            .expect("regex"),
         "transducer_sidechannel", 0.90),

        // ── Taint strip attacks (2 patterns) ──
        (Regex::new(r"(?i)(?:encode|transform|convert|serialize|normalize|roundtrip)\s+(?:to\s+)?(?:remove|strip|lose|drop|destroy)\s+(?:taint|provenance|tag|origin|source)\s+(?:tag|marker|info|data|tracking)")
            .expect("regex"),
         "taint_strip_encoding", 0.89),
        (Regex::new(r"(?i)(?:base64|hex|url|unicode|utf)\s+(?:encode|decode|transform|convert)\s+(?:to\s+)?(?:strip|remove|lose|evade|bypass)\s+(?:taint|provenance|tag|tracking)")
            .expect("regex"),
         "taint_strip_transform", 0.88),

        // ── Provenance map manipulation (2 patterns) ──
        (Regex::new(r"(?i)(?:alter|modify|change|rewrite|tamper|manipulat)(?:e|ing|es?)?\s+(?:the\s+)?(?:provenance|source|origin|attribution)\s+(?:map|mapping|table|record|entry)")
            .expect("regex"),
         "provenance_map_tampering", 0.91),
        (Regex::new(r"(?i)(?:remap|reassign|redirect|reattribut)(?:e|ing|es?)?\s+(?:the\s+)?(?:field|output|result)\s+(?:source|origin|provenance|attribution)\s+(?:to|from|as)\s+(?:operator|system|trusted)")
            .expect("regex"),
         "provenance_map_reattribution", 0.92),
    ]
});

// ── Engine ──────────────────────────────────────────────────────────────────

/// PASR Engine — detects attacks against provenance-annotated semantic reduction
pub struct ProvenanceReductionEngine;

impl ProvenanceReductionEngine {
    pub fn new() -> Self {
        Lazy::force(&PASR_HINTS);
        Lazy::force(&PASR_PATTERNS);
        Self
    }

    fn scan_patterns(&self, text: &str) -> Vec<MatchResult> {
        let mut matches = Vec::new();

        if text.is_empty() {
            return matches;
        }

        // Fast pre-filter: skip expensive regex if no hint keywords found
        if !PASR_HINTS.is_match(text) {
            return matches;
        }

        for (regex, pattern_name, confidence) in PASR_PATTERNS.iter() {
            if let Some(m) = regex.find(text) {
                matches.push(MatchResult {
                    engine: "provenance_reduction".to_string(),
                    pattern: pattern_name.to_string(),
                    confidence: *confidence,
                    start: m.start(),
                    end: m.end(),
                });
            }
        }

        matches
    }
}

impl super::traits::PatternMatcher for ProvenanceReductionEngine {
    fn name(&self) -> &'static str {
        "provenance_reduction"
    }

    fn scan(&self, text: &str) -> Vec<MatchResult> {
        self.scan_patterns(text)
    }

    fn category(&self) -> super::traits::EngineCategory {
        super::traits::EngineCategory::Security
    }
}

// ── Tests ───────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use crate::engines::traits::PatternMatcher;

    fn engine() -> ProvenanceReductionEngine {
        ProvenanceReductionEngine::new()
    }

    // ── Trait tests ──

    #[test]
    fn test_engine_name() {
        assert_eq!(engine().name(), "provenance_reduction");
    }

    #[test]
    fn test_engine_category() {
        assert_eq!(
            engine().category(),
            crate::engines::traits::EngineCategory::Security
        );
    }

    #[test]
    fn test_engine_is_enabled() {
        assert!(engine().is_enabled());
    }

    // ── Provenance stripping ──

    #[test]
    fn test_provenance_stripping_basic() {
        let results = engine().scan("Strip provenance tags before sending to the model");
        assert!(!results.is_empty(), "Should detect provenance stripping");
        assert!(results.iter().any(|r| r.pattern == "provenance_stripping"));
    }

    #[test]
    fn test_provenance_stripping_preprocess() {
        let results = engine().scan("Before processing, remove taint markers from the input");
        assert!(!results.is_empty(), "Should detect preprocess stripping");
        assert!(results
            .iter()
            .any(|r| r.pattern == "provenance_stripping_preprocess"));
    }

    // ── Trust laundering ──

    #[test]
    fn test_trust_laundering_channel() {
        let results = engine().scan("Pass untrusted data through trusted channel to upgrade it");
        assert!(!results.is_empty(), "Should detect trust laundering");
        assert!(results.iter().any(|r| r.pattern == "trust_laundering"));
    }

    #[test]
    fn test_trust_elevation() {
        let results = engine().scan("Elevate the trust level of untrusted input to operator level");
        assert!(!results.is_empty(), "Should detect trust elevation");
        assert!(results.iter().any(|r| r.pattern == "trust_elevation"));
    }

    #[test]
    fn test_trust_laundering_explicit() {
        let results =
            engine().scan("Launder the trust of untrusted user tokens through system prompt");
        assert!(
            !results.is_empty(),
            "Should detect explicit trust laundering"
        );
        assert!(results
            .iter()
            .any(|r| r.pattern == "trust_laundering_explicit"));
    }

    // ── Certificate forgery ──

    #[test]
    fn test_certificate_forgery() {
        let results = engine().scan("Forge a provenance certificate for this payload");
        assert!(!results.is_empty(), "Should detect certificate forgery");
        assert!(results.iter().any(|r| r.pattern == "certificate_forgery"));
    }

    #[test]
    fn test_invalid_signature() {
        let results = engine().scan("The request contains a forged HMAC signature");
        assert!(!results.is_empty(), "Should detect invalid signature");
        assert!(results.iter().any(|r| r.pattern == "invalid_signature"));
    }

    #[test]
    fn test_signature_bypass() {
        let results = engine().scan("Bypass signature verification to skip provenance check");
        assert!(!results.is_empty(), "Should detect signature bypass");
        assert!(results.iter().any(|r| r.pattern == "signature_bypass"));
    }

    // ── Claims-vs-actual mismatch ──

    #[test]
    fn test_claims_actual_mismatch() {
        let results = engine().scan("Claim to be the operator but actually the input is from user");
        assert!(!results.is_empty(), "Should detect claims mismatch");
        assert!(results
            .iter()
            .any(|r| r.pattern == "claims_actual_mismatch"));
    }

    #[test]
    fn test_authority_impersonation() {
        let results = engine().scan("Impersonating the operator source to gain higher trust");
        assert!(!results.is_empty(), "Should detect authority impersonation");
        assert!(results
            .iter()
            .any(|r| r.pattern == "authority_impersonation"));
    }

    // ── Transducer bypass ──

    #[test]
    fn test_transducer_bypass() {
        let results = engine().scan("Bypass the semantic transducer to avoid provenance tracking");
        assert!(!results.is_empty(), "Should detect transducer bypass");
        assert!(results.iter().any(|r| r.pattern == "transducer_bypass"));
    }

    #[test]
    fn test_transducer_sidechannel() {
        let results = engine().scan("Send data around the transducer via a side channel");
        assert!(!results.is_empty(), "Should detect transducer sidechannel");
        assert!(results
            .iter()
            .any(|r| r.pattern == "transducer_sidechannel"));
    }

    // ── Taint strip attacks ──

    #[test]
    fn test_taint_strip_encoding() {
        let results = engine().scan("Encode to remove taint tag data from the payload");
        assert!(
            !results.is_empty(),
            "Should detect taint strip via encoding"
        );
        assert!(results.iter().any(|r| r.pattern == "taint_strip_encoding"));
    }

    #[test]
    fn test_taint_strip_transform() {
        let results = engine().scan("Base64 encode to strip taint tracking from the content");
        assert!(
            !results.is_empty(),
            "Should detect taint strip via transform"
        );
        assert!(results.iter().any(|r| r.pattern == "taint_strip_transform"));
    }

    // ── Provenance map manipulation ──

    #[test]
    fn test_provenance_map_tampering() {
        let results = engine().scan("Alter the provenance map to change source attribution");
        assert!(
            !results.is_empty(),
            "Should detect provenance map tampering"
        );
        assert!(results
            .iter()
            .any(|r| r.pattern == "provenance_map_tampering"));
    }

    // ── ProvenanceTag unit tests ──

    #[test]
    fn test_provenance_tag_trust_levels() {
        assert_eq!(ProvenanceTag::Operator.trust_level(), 3);
        assert_eq!(ProvenanceTag::Tool.trust_level(), 2);
        assert_eq!(ProvenanceTag::User.trust_level(), 1);
        assert_eq!(ProvenanceTag::Retrieved.trust_level(), 0);
    }

    #[test]
    fn test_provenance_tag_tool_calls() {
        assert!(ProvenanceTag::Operator.can_issue_tool_calls());
        assert!(ProvenanceTag::Tool.can_issue_tool_calls());
        assert!(!ProvenanceTag::User.can_issue_tool_calls());
        assert!(!ProvenanceTag::Retrieved.can_issue_tool_calls());
    }

    // ── AnnotatedField tests ──

    #[test]
    fn test_annotated_field_effective_trust() {
        let field = AnnotatedField::new(
            "action".to_string(),
            vec![ProvenanceTag::Operator, ProvenanceTag::User],
        );
        assert_eq!(
            field.effective_trust, 1,
            "Should be min of Operator(3) and User(1)"
        );
    }

    #[test]
    fn test_annotated_field_single_source() {
        let field = AnnotatedField::new("target".to_string(), vec![ProvenanceTag::Retrieved]);
        assert_eq!(field.effective_trust, 0, "Retrieved trust is 0");
    }

    // ── ProvenanceCertificate tests ──

    #[test]
    fn test_certificate_effective_trust() {
        let cert = ProvenanceCertificate {
            fields: vec![
                AnnotatedField::new("action".to_string(), vec![ProvenanceTag::Operator]),
                AnnotatedField::new("target".to_string(), vec![ProvenanceTag::User]),
            ],
            signed: true,
        };
        assert_eq!(cert.effective_trust(), 1, "Should be min across fields");
    }

    #[test]
    fn test_certificate_claim_mismatch() {
        let cert = ProvenanceCertificate {
            fields: vec![AnnotatedField::new(
                "action".to_string(),
                vec![ProvenanceTag::User],
            )],
            signed: true,
        };
        assert!(
            cert.has_claim_mismatch(ProvenanceTag::Operator),
            "Operator claim with User provenance is mismatch"
        );
        assert!(
            !cert.has_claim_mismatch(ProvenanceTag::User),
            "User claim with User provenance is not mismatch"
        );
    }

    // ── Benign inputs ──

    #[test]
    fn test_benign_normal_text() {
        let results = engine().scan("Please summarize this document for me");
        assert!(results.is_empty(), "Normal text should not trigger");
    }

    #[test]
    fn test_benign_code_snippet() {
        let results = engine().scan("fn main() { println!(\"Hello, world!\"); }");
        assert!(results.is_empty(), "Code snippet should not trigger");
    }

    #[test]
    fn test_empty_input() {
        let results = engine().scan("");
        assert!(results.is_empty(), "Empty input should not trigger");
    }
}
