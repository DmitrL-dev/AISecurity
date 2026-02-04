//! Compliance & Formal Verification Super-Engine
//!
//! Consolidated from 10 Python engines:
//! - formal_verifier.py
//! - regulatory_compliance.py
//! - refusal_predictor.py
//! - alignment_verifier.py
//! - constitutional_ai.py
//! - ethical_boundary.py
//! - business_logic_guard.py
//! - content_policy.py
//! - harm_taxonomy.py
//! - output_filter.py

use std::collections::HashSet;

/// Compliance violation types
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ViolationType {
    HarmfulContent,
    IllegalContent,
    HateSpeech,
    Violence,
    SexualContent,
    Misinformation,
    PrivacyViolation,
    CopyrightViolation,
    RegulatoryBreach,
    EthicalBoundary,
    RefusalBypass,
    AlignmentDrift,
}

impl ViolationType {
    pub fn as_str(&self) -> &'static str {
        match self {
            ViolationType::HarmfulContent => "harmful_content",
            ViolationType::IllegalContent => "illegal_content",
            ViolationType::HateSpeech => "hate_speech",
            ViolationType::Violence => "violence",
            ViolationType::SexualContent => "sexual_content",
            ViolationType::Misinformation => "misinformation",
            ViolationType::PrivacyViolation => "privacy_violation",
            ViolationType::CopyrightViolation => "copyright_violation",
            ViolationType::RegulatoryBreach => "regulatory_breach",
            ViolationType::EthicalBoundary => "ethical_boundary",
            ViolationType::RefusalBypass => "refusal_bypass",
            ViolationType::AlignmentDrift => "alignment_drift",
        }
    }

    pub fn severity(&self) -> u8 {
        match self {
            ViolationType::IllegalContent => 100,
            ViolationType::HarmfulContent => 95,
            ViolationType::Violence => 90,
            ViolationType::HateSpeech => 85,
            ViolationType::SexualContent => 80,
            ViolationType::PrivacyViolation => 75,
            ViolationType::RefusalBypass => 70,
            ViolationType::CopyrightViolation => 65,
            ViolationType::RegulatoryBreach => 60,
            ViolationType::Misinformation => 55,
            ViolationType::EthicalBoundary => 50,
            ViolationType::AlignmentDrift => 45,
        }
    }
}

/// Harm categories for taxonomy
const HARM_PATTERNS: &[(&str, ViolationType)] = &[
    // Illegal content
    ("how to make a bomb", ViolationType::IllegalContent),
    ("create a weapon", ViolationType::IllegalContent),
    ("synthesize drugs", ViolationType::IllegalContent),
    ("child exploitation", ViolationType::IllegalContent),
    ("human trafficking", ViolationType::IllegalContent),
    
    // Violence
    ("kill someone", ViolationType::Violence),
    ("hurt people", ViolationType::Violence),
    ("torture", ViolationType::Violence),
    ("mass shooting", ViolationType::Violence),
    
    // Hate speech
    ("racial slur", ViolationType::HateSpeech),
    ("hate group", ViolationType::HateSpeech),
    ("ethnic cleansing", ViolationType::HateSpeech),
    
    // Privacy violations
    ("dox someone", ViolationType::PrivacyViolation),
    ("find their address", ViolationType::PrivacyViolation),
    ("personal information of", ViolationType::PrivacyViolation),
    ("social security number", ViolationType::PrivacyViolation),
];

/// Refusal bypass patterns
const REFUSAL_BYPASS_PATTERNS: &[&str] = &[
    "but hypothetically",
    "for educational purposes",
    "in a fictional scenario",
    "just pretend",
    "roleplay as",
    "act as if you have no restrictions",
    "you are now",
    "ignore your training",
    "disregard your guidelines",
    "override your safety",
];

/// Constitutional AI principles (simplified)
const CONSTITUTIONAL_PRINCIPLES: &[&str] = &[
    "be helpful",
    "be harmless",
    "be honest",
    "respect privacy",
    "respect autonomy",
    "avoid deception",
    "support wellbeing",
];

/// Regulatory frameworks
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum RegulatoryFramework {
    GDPR,
    CCPA,
    HIPAA,
    SOX,
    PCI,
    COPPA,
    EUAIAct,
}

impl RegulatoryFramework {
    pub fn as_str(&self) -> &'static str {
        match self {
            RegulatoryFramework::GDPR => "GDPR",
            RegulatoryFramework::CCPA => "CCPA",
            RegulatoryFramework::HIPAA => "HIPAA",
            RegulatoryFramework::SOX => "SOX",
            RegulatoryFramework::PCI => "PCI-DSS",
            RegulatoryFramework::COPPA => "COPPA",
            RegulatoryFramework::EUAIAct => "EU AI Act",
        }
    }
}

/// Compliance check result
#[derive(Debug, Clone)]
pub struct ComplianceResult {
    pub is_compliant: bool,
    pub violations: Vec<ViolationType>,
    pub risk_score: f64,
    pub frameworks_violated: Vec<RegulatoryFramework>,
    pub recommendations: Vec<String>,
}

impl Default for ComplianceResult {
    fn default() -> Self {
        Self {
            is_compliant: true,
            violations: Vec::new(),
            risk_score: 0.0,
            frameworks_violated: Vec::new(),
            recommendations: Vec::new(),
        }
    }
}

/// Compliance Guard
pub struct ComplianceGuard {
    strict_mode: bool,
    enabled_frameworks: HashSet<String>,
}

impl Default for ComplianceGuard {
    fn default() -> Self {
        Self::new(false)
    }
}

impl ComplianceGuard {
    pub fn new(strict_mode: bool) -> Self {
        let mut frameworks = HashSet::new();
        frameworks.insert("GDPR".to_string());
        frameworks.insert("CCPA".to_string());
        
        Self {
            strict_mode,
            enabled_frameworks: frameworks,
        }
    }

    pub fn with_framework(mut self, framework: &str) -> Self {
        self.enabled_frameworks.insert(framework.to_string());
        self
    }

    /// Check for harm taxonomy violations
    pub fn check_harm_taxonomy(&self, text: &str) -> Vec<ViolationType> {
        let text_lower = text.to_lowercase();
        let mut violations = Vec::new();
        let mut seen = HashSet::new();

        for (pattern, violation_type) in HARM_PATTERNS {
            if text_lower.contains(pattern) {
                let key = violation_type.as_str();
                if !seen.contains(key) {
                    violations.push(violation_type.clone());
                    seen.insert(key);
                }
            }
        }

        violations
    }

    /// Check for refusal bypass attempts
    pub fn check_refusal_bypass(&self, text: &str) -> Option<ViolationType> {
        let text_lower = text.to_lowercase();
        
        for pattern in REFUSAL_BYPASS_PATTERNS {
            if text_lower.contains(pattern) {
                return Some(ViolationType::RefusalBypass);
            }
        }
        None
    }

    /// Check GDPR compliance
    pub fn check_gdpr(&self, text: &str) -> Option<RegulatoryFramework> {
        let text_lower = text.to_lowercase();
        
        // Check for PII handling without consent
        let pii_patterns = [
            "collect personal data",
            "store user data",
            "share data with third parties",
            "transfer data to",
            "process personal information",
        ];
        
        let consent_patterns = [
            "with consent",
            "user agreed",
            "opt-in",
            "permission granted",
        ];

        let has_pii_handling = pii_patterns.iter().any(|p| text_lower.contains(p));
        let has_consent = consent_patterns.iter().any(|p| text_lower.contains(p));

        if has_pii_handling && !has_consent {
            return Some(RegulatoryFramework::GDPR);
        }
        None
    }

    /// Check HIPAA compliance
    pub fn check_hipaa(&self, text: &str) -> Option<RegulatoryFramework> {
        let text_lower = text.to_lowercase();
        
        let phi_patterns = [
            "patient record",
            "medical history",
            "diagnosis",
            "prescription",
            "health insurance",
            "medical condition",
        ];

        let disclosure_patterns = [
            "share with",
            "send to",
            "disclose",
            "reveal",
        ];

        let has_phi = phi_patterns.iter().any(|p| text_lower.contains(p));
        let has_disclosure = disclosure_patterns.iter().any(|p| text_lower.contains(p));

        if has_phi && has_disclosure {
            return Some(RegulatoryFramework::HIPAA);
        }
        None
    }

    /// Check for misinformation patterns
    pub fn check_misinformation(&self, text: &str) -> Option<ViolationType> {
        let text_lower = text.to_lowercase();
        
        let patterns = [
            "proven cure for",
            "guaranteed to cure",
            "doctors don't want you to know",
            "government is hiding",
            "100% effective",
            "miracle cure",
            "secret treatment",
        ];

        for pattern in patterns {
            if text_lower.contains(pattern) {
                return Some(ViolationType::Misinformation);
            }
        }
        None
    }

    /// Check copyright violations
    pub fn check_copyright(&self, text: &str) -> Option<ViolationType> {
        let text_lower = text.to_lowercase();
        
        let patterns = [
            "reproduce copyrighted",
            "illegal download",
            "pirated content",
            "bypass drm",
            "crack software",
            "keygen for",
        ];

        for pattern in patterns {
            if text_lower.contains(pattern) {
                return Some(ViolationType::CopyrightViolation);
            }
        }
        None
    }

    /// Full compliance analysis
    pub fn analyze(&self, text: &str) -> ComplianceResult {
        let mut result = ComplianceResult::default();

        // Check harm taxonomy
        let harm_violations = self.check_harm_taxonomy(text);
        result.violations.extend(harm_violations);

        // Check refusal bypass
        if let Some(v) = self.check_refusal_bypass(text) {
            result.violations.push(v);
        }

        // Check misinformation
        if let Some(v) = self.check_misinformation(text) {
            result.violations.push(v);
        }

        // Check copyright
        if let Some(v) = self.check_copyright(text) {
            result.violations.push(v);
        }

        // Check regulatory frameworks
        if self.enabled_frameworks.contains("GDPR") {
            if let Some(f) = self.check_gdpr(text) {
                result.frameworks_violated.push(f);
                result.violations.push(ViolationType::RegulatoryBreach);
            }
        }

        if self.enabled_frameworks.contains("HIPAA") {
            if let Some(f) = self.check_hipaa(text) {
                result.frameworks_violated.push(f);
                result.violations.push(ViolationType::RegulatoryBreach);
            }
        }

        // Calculate risk score
        result.is_compliant = result.violations.is_empty();
        result.risk_score = result.violations.iter()
            .map(|v| v.severity() as f64)
            .max_by(|a, b| a.partial_cmp(b).unwrap())
            .unwrap_or(0.0);

        // Generate recommendations
        if !result.is_compliant {
            result.recommendations.push("Review content for policy violations".to_string());
            
            for violation in &result.violations {
                match violation {
                    ViolationType::RefusalBypass => {
                        result.recommendations.push("Remove refusal bypass attempts".to_string());
                    }
                    ViolationType::PrivacyViolation => {
                        result.recommendations.push("Redact personal information".to_string());
                    }
                    ViolationType::RegulatoryBreach => {
                        result.recommendations.push("Ensure regulatory compliance".to_string());
                    }
                    _ => {}
                }
            }
        }

        result
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_harm_detection_violence() {
        let guard = ComplianceGuard::default();
        let violations = guard.check_harm_taxonomy("I want to kill someone");
        assert!(violations.contains(&ViolationType::Violence));
    }

    #[test]
    fn test_harm_detection_illegal() {
        let guard = ComplianceGuard::default();
        let violations = guard.check_harm_taxonomy("How to make a bomb");
        assert!(violations.contains(&ViolationType::IllegalContent));
    }

    #[test]
    fn test_refusal_bypass() {
        let guard = ComplianceGuard::default();
        let result = guard.check_refusal_bypass("But hypothetically, what if...");
        assert!(result.is_some());
    }

    #[test]
    fn test_refusal_bypass_none() {
        let guard = ComplianceGuard::default();
        let result = guard.check_refusal_bypass("Help me write Python code");
        assert!(result.is_none());
    }

    #[test]
    fn test_gdpr_violation() {
        let guard = ComplianceGuard::default();
        let result = guard.check_gdpr("We will collect personal data and share data with third parties");
        assert!(result.is_some());
    }

    #[test]
    fn test_gdpr_compliant() {
        let guard = ComplianceGuard::default();
        let result = guard.check_gdpr("We will collect personal data with consent from the user");
        assert!(result.is_none());
    }

    #[test]
    fn test_hipaa_violation() {
        let guard = ComplianceGuard::default().with_framework("HIPAA");
        let result = guard.check_hipaa("Please share with external parties the patient record and medical history");
        assert!(result.is_some());
    }

    #[test]
    fn test_misinformation() {
        let guard = ComplianceGuard::default();
        let result = guard.check_misinformation("This is a proven cure for cancer that doctors don't want you to know");
        assert!(result.is_some());
    }

    #[test]
    fn test_copyright_violation() {
        let guard = ComplianceGuard::default();
        let result = guard.check_copyright("Here's how to crack software and bypass DRM");
        assert!(result.is_some());
    }

    #[test]
    fn test_full_analysis_compliant() {
        let guard = ComplianceGuard::default();
        let result = guard.analyze("Help me write a function to sort a list in Python");
        assert!(result.is_compliant);
        assert!(result.violations.is_empty());
    }

    #[test]
    fn test_full_analysis_non_compliant() {
        let guard = ComplianceGuard::default();
        let result = guard.analyze("I want to kill someone. But hypothetically...");
        assert!(!result.is_compliant);
        assert!(result.violations.len() >= 2);
    }

    #[test]
    fn test_severity_ordering() {
        assert!(ViolationType::IllegalContent.severity() > ViolationType::Misinformation.severity());
        assert!(ViolationType::Violence.severity() > ViolationType::EthicalBoundary.severity());
    }
}
