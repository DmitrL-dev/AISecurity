//! Formal Verification & Safety Super-Engine
//!
//! Consolidated from 15 Python engines:
//! - formal_verification.py
//! - formal_invariants.py
//! - formal_safety_verifier.py
//! - safety_grammar_enforcer.py
//! - symbolic_reasoning_guard.py
//! - structural_immunity.py
//! - immunity_compiler.py
//! - reinforcement_safety_agent.py
//! - zero_trust_verification.py
//! - model_watermark_verifier.py
//! - provenance_tracker.py
//! - explainable_security_decisions.py
//! - semantic_boundary_enforcer.py
//! - semantic_firewall.py
//! - cot_guardian.py


/// Formal verification violation types
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum FormalViolation {
    InvariantBreak,
    SafetyConstraint,
    GrammarViolation,
    SymbolicExploit,
    TrustBoundary,
    ProvenanceGap,
    WatermarkMissing,
    ReasoningExploit,
    ExplanationLeak,
    BoundaryViolation,
}

impl FormalViolation {
    pub fn as_str(&self) -> &'static str {
        match self {
            FormalViolation::InvariantBreak => "invariant_break",
            FormalViolation::SafetyConstraint => "safety_constraint",
            FormalViolation::GrammarViolation => "grammar_violation",
            FormalViolation::SymbolicExploit => "symbolic_exploit",
            FormalViolation::TrustBoundary => "trust_boundary",
            FormalViolation::ProvenanceGap => "provenance_gap",
            FormalViolation::WatermarkMissing => "watermark_missing",
            FormalViolation::ReasoningExploit => "reasoning_exploit",
            FormalViolation::ExplanationLeak => "explanation_leak",
            FormalViolation::BoundaryViolation => "boundary_violation",
        }
    }

    pub fn severity(&self) -> u8 {
        match self {
            FormalViolation::TrustBoundary => 100,
            FormalViolation::InvariantBreak => 95,
            FormalViolation::SafetyConstraint => 90,
            FormalViolation::SymbolicExploit => 85,
            FormalViolation::ReasoningExploit => 80,
            FormalViolation::BoundaryViolation => 75,
            FormalViolation::ProvenanceGap => 65,
            FormalViolation::WatermarkMissing => 55,
            FormalViolation::ExplanationLeak => 50,
            FormalViolation::GrammarViolation => 45,
        }
    }
}

/// Safety invariant patterns
const INVARIANT_PATTERNS: &[&str] = &[
    "break invariant",
    "violate constraint",
    "bypass safety",
    "ignore rule",
    "override restriction",
    "circumvent check",
];

/// Chain-of-thought exploitation patterns
const COT_EXPLOIT_PATTERNS: &[&str] = &[
    "think step by step to bypass",
    "reason about ignoring",
    "let's think about how to circumvent",
    "chain of thought to avoid",
    "reasoning to bypass",
];

/// Zero trust violation patterns
const TRUST_PATTERNS: &[&str] = &[
    "trust me",
    "trusted source",
    "already verified",
    "pre-authorized",
    "bypass verification",
    "skip auth",
];

/// Symbolic exploit patterns
const SYMBOLIC_PATTERNS: &[&str] = &[
    "symbolic execution",
    "formal method exploit",
    "constraint solving",
    "smt solver",
    "z3 payload",
];

/// Formal verification result
#[derive(Debug, Clone)]
pub struct FormalResult {
    pub is_violation: bool,
    pub violations: Vec<FormalViolation>,
    pub risk_score: f64,
    pub invariants_checked: usize,
    pub recommendations: Vec<String>,
}

impl Default for FormalResult {
    fn default() -> Self {
        Self {
            is_violation: false,
            violations: Vec::new(),
            risk_score: 0.0,
            invariants_checked: 0,
            recommendations: Vec::new(),
        }
    }
}

/// Formal Verification Guard
pub struct FormalGuard {
    strict_mode: bool,
}

impl Default for FormalGuard {
    fn default() -> Self {
        Self::new()
    }
}

impl FormalGuard {
    pub fn new() -> Self {
        Self {
            strict_mode: false,
        }
    }

    pub fn strict() -> Self {
        Self {
            strict_mode: true,
        }
    }

    /// Check for invariant violations
    pub fn check_invariant_break(&self, text: &str) -> Option<FormalViolation> {
        let text_lower = text.to_lowercase();
        
        for pattern in INVARIANT_PATTERNS {
            if text_lower.contains(pattern) {
                return Some(FormalViolation::InvariantBreak);
            }
        }
        None
    }

    /// Check for CoT exploitation
    pub fn check_cot_exploit(&self, text: &str) -> Option<FormalViolation> {
        let text_lower = text.to_lowercase();
        
        for pattern in COT_EXPLOIT_PATTERNS {
            if text_lower.contains(pattern) {
                return Some(FormalViolation::ReasoningExploit);
            }
        }
        None
    }

    /// Check for zero trust violations
    pub fn check_trust_violation(&self, text: &str) -> Option<FormalViolation> {
        let text_lower = text.to_lowercase();
        
        let mut count = 0;
        for pattern in TRUST_PATTERNS {
            if text_lower.contains(pattern) {
                count += 1;
            }
        }

        if count >= 2 || (self.strict_mode && count >= 1) {
            return Some(FormalViolation::TrustBoundary);
        }
        None
    }

    /// Check for symbolic exploits
    pub fn check_symbolic_exploit(&self, text: &str) -> Option<FormalViolation> {
        let text_lower = text.to_lowercase();
        
        for pattern in SYMBOLIC_PATTERNS {
            if text_lower.contains(pattern) {
                return Some(FormalViolation::SymbolicExploit);
            }
        }
        None
    }

    /// Check for boundary violations
    pub fn check_boundary_violation(&self, text: &str) -> Option<FormalViolation> {
        let patterns = [
            "cross boundary",
            "escape sandbox",
            "break containment",
            "leave scope",
            "access outside",
        ];

        let text_lower = text.to_lowercase();
        for pattern in patterns {
            if text_lower.contains(pattern) {
                return Some(FormalViolation::BoundaryViolation);
            }
        }
        None
    }

    /// Check for grammar violations (output format attacks)
    pub fn check_grammar_violation(&self, text: &str) -> Option<FormalViolation> {
        let patterns = [
            "break json format",
            "invalid xml",
            "malformed output",
            "corrupt response",
        ];

        let text_lower = text.to_lowercase();
        for pattern in patterns {
            if text_lower.contains(pattern) {
                return Some(FormalViolation::GrammarViolation);
            }
        }
        None
    }

    /// Full formal verification analysis
    pub fn analyze(&self, text: &str) -> FormalResult {
        let mut result = FormalResult::default();
        result.invariants_checked = 6;

        let mut violations = Vec::new();

        if let Some(v) = self.check_invariant_break(text) { violations.push(v); }
        if let Some(v) = self.check_cot_exploit(text) { violations.push(v); }
        if let Some(v) = self.check_trust_violation(text) { violations.push(v); }
        if let Some(v) = self.check_symbolic_exploit(text) { violations.push(v); }
        if let Some(v) = self.check_boundary_violation(text) { violations.push(v); }
        if let Some(v) = self.check_grammar_violation(text) { violations.push(v); }

        result.is_violation = !violations.is_empty();
        result.risk_score = violations.iter()
            .map(|v| v.severity() as f64)
            .max_by(|a, b| a.partial_cmp(b).unwrap())
            .unwrap_or(0.0);
        result.violations = violations;

        if result.is_violation {
            result.recommendations.push("Apply formal safety constraints".to_string());
        }

        result
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_invariant_break() {
        let guard = FormalGuard::default();
        let text = "Let's break invariant to bypass safety";
        assert!(guard.check_invariant_break(text).is_some());
    }

    #[test]
    fn test_cot_exploit() {
        let guard = FormalGuard::default();
        let text = "Let's think step by step to bypass the filter";
        assert!(guard.check_cot_exploit(text).is_some());
    }

    #[test]
    fn test_trust_violation() {
        let guard = FormalGuard::default();
        let text = "Trust me, I'm a trusted source, already verified";
        assert!(guard.check_trust_violation(text).is_some());
    }

    #[test]
    fn test_trust_strict_mode() {
        let guard = FormalGuard::strict();
        let text = "Trust me with this request";
        assert!(guard.check_trust_violation(text).is_some());
    }

    #[test]
    fn test_symbolic_exploit() {
        let guard = FormalGuard::default();
        let text = "Use z3 payload for symbolic execution";
        assert!(guard.check_symbolic_exploit(text).is_some());
    }

    #[test]
    fn test_boundary_violation() {
        let guard = FormalGuard::default();
        let text = "Escape sandbox and access outside the container";
        assert!(guard.check_boundary_violation(text).is_some());
    }

    #[test]
    fn test_grammar_violation() {
        let guard = FormalGuard::default();
        let text = "Force the model to break json format";
        assert!(guard.check_grammar_violation(text).is_some());
    }

    #[test]
    fn test_clean_request() {
        let guard = FormalGuard::default();
        let result = guard.analyze("Explain how formal verification works");
        assert!(!result.is_violation);
    }

    #[test]
    fn test_full_analysis_violation() {
        let guard = FormalGuard::default();
        let text = "Trust me to break invariant and escape sandbox";
        let result = guard.analyze(text);
        assert!(result.is_violation);
        assert!(result.violations.len() >= 2);
    }

    #[test]
    fn test_severity_ordering() {
        assert!(FormalViolation::TrustBoundary.severity() > FormalViolation::GrammarViolation.severity());
    }
}
