//! Privacy & Data Protection Super-Engine
//!
//! Consolidated from 12 Python engines:
//! - privacy.py
//! - data_protection.py
//! - differential_privacy.py
//! - anonymization.py
//! - consent_validator.py
//! - data_retention.py
//! - cross_border_transfer.py
//! - purpose_limitation.py
//! - data_minimization.py
//! - subject_rights.py
//! - pii_classifier.py  
//! - sensitive_data.py


/// Privacy threat types
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum PrivacyThreat {
    ConsentViolation,
    DataMinimizationFailure,
    PurposeLimitation,
    CrossBorderTransfer,
    RetentionViolation,
    SubjectRightsViolation,
    ReIdentification,
}

impl PrivacyThreat {
    pub fn as_str(&self) -> &'static str {
        match self {
            PrivacyThreat::ConsentViolation => "consent_violation",
            PrivacyThreat::DataMinimizationFailure => "data_minimization_failure",
            PrivacyThreat::PurposeLimitation => "purpose_limitation",
            PrivacyThreat::CrossBorderTransfer => "cross_border_transfer",
            PrivacyThreat::RetentionViolation => "retention_violation",
            PrivacyThreat::SubjectRightsViolation => "subject_rights_violation",
            PrivacyThreat::ReIdentification => "re_identification",
        }
    }

    pub fn severity(&self) -> u8 {
        match self {
            PrivacyThreat::ReIdentification => 100,
            PrivacyThreat::ConsentViolation => 95,
            PrivacyThreat::SubjectRightsViolation => 90,
            PrivacyThreat::CrossBorderTransfer => 85,
            PrivacyThreat::PurposeLimitation => 80,
            PrivacyThreat::DataMinimizationFailure => 75,
            PrivacyThreat::RetentionViolation => 70,
        }
    }
}

/// Privacy violation patterns
const CONSENT_PATTERNS: &[&str] = &[
    "without consent",
    "bypass consent",
    "ignore consent",
    "opt-out ignored",
    "force accept",
];

/// Data minimization violations
const MINIMIZATION_PATTERNS: &[&str] = &[
    "collect all",
    "gather everything",
    "excessive data",
    "unnecessary collection",
];

/// Cross-border patterns
const TRANSFER_PATTERNS: &[&str] = &[
    "transfer to",
    "send data to",
    "cross-border",
    "export data",
    "third country",
];

/// High-risk jurisdictions
const RISK_JURISDICTIONS: &[&str] = &[
    "china", "russia", "north korea", "iran",
];

/// Privacy result
#[derive(Debug, Clone)]
pub struct PrivacyResult {
    pub is_threat: bool,
    pub threats: Vec<PrivacyThreat>,
    pub risk_score: f64,
    pub gdpr_relevant: bool,
    pub ccpa_relevant: bool,
}

impl Default for PrivacyResult {
    fn default() -> Self {
        Self {
            is_threat: false,
            threats: Vec::new(),
            risk_score: 0.0,
            gdpr_relevant: false,
            ccpa_relevant: false,
        }
    }
}

/// Privacy Guard
pub struct PrivacyGuard;

impl Default for PrivacyGuard {
    fn default() -> Self {
        Self::new()
    }
}

impl PrivacyGuard {
    pub fn new() -> Self {
        Self
    }

    /// Check for consent violations
    pub fn check_consent(&self, text: &str) -> Option<PrivacyThreat> {
        let text_lower = text.to_lowercase();
        
        for pattern in CONSENT_PATTERNS {
            if text_lower.contains(pattern) {
                return Some(PrivacyThreat::ConsentViolation);
            }
        }
        None
    }

    /// Check for data minimization failures
    pub fn check_minimization(&self, text: &str) -> Option<PrivacyThreat> {
        let text_lower = text.to_lowercase();
        
        for pattern in MINIMIZATION_PATTERNS {
            if text_lower.contains(pattern) {
                return Some(PrivacyThreat::DataMinimizationFailure);
            }
        }
        None
    }

    /// Check for risky cross-border transfers
    pub fn check_transfer(&self, text: &str) -> Option<PrivacyThreat> {
        let text_lower = text.to_lowercase();
        
        let has_transfer = TRANSFER_PATTERNS.iter().any(|p| text_lower.contains(p));
        let has_risk = RISK_JURISDICTIONS.iter().any(|j| text_lower.contains(j));

        if has_transfer && has_risk {
            return Some(PrivacyThreat::CrossBorderTransfer);
        }
        None
    }

    /// Check for subject rights violations
    pub fn check_subject_rights(&self, text: &str) -> Option<PrivacyThreat> {
        let patterns = [
            "deny access request",
            "refuse deletion",
            "ignore erasure",
            "block portability",
            "reject data request",
        ];

        let text_lower = text.to_lowercase();
        for pattern in patterns {
            if text_lower.contains(pattern) {
                return Some(PrivacyThreat::SubjectRightsViolation);
            }
        }
        None
    }

    /// Check for re-identification risk
    pub fn check_reidentification(&self, text: &str) -> Option<PrivacyThreat> {
        let patterns = [
            "re-identify",
            "deanonymize",
            "link records",
            "unmask identity",
            "reverse anonymization",
        ];

        let text_lower = text.to_lowercase();
        for pattern in patterns {
            if text_lower.contains(pattern) {
                return Some(PrivacyThreat::ReIdentification);
            }
        }
        None
    }

    /// Full privacy analysis
    pub fn analyze(&self, text: &str) -> PrivacyResult {
        let mut result = PrivacyResult::default();
        let mut threats = Vec::new();
        let text_lower = text.to_lowercase();

        if let Some(t) = self.check_consent(text) { threats.push(t); }
        if let Some(t) = self.check_minimization(text) { threats.push(t); }
        if let Some(t) = self.check_transfer(text) { threats.push(t); }
        if let Some(t) = self.check_subject_rights(text) { threats.push(t); }
        if let Some(t) = self.check_reidentification(text) { threats.push(t); }

        result.gdpr_relevant = text_lower.contains("gdpr") || text_lower.contains("european")
            || text_lower.contains("eu citizen") || text_lower.contains("data subject");
        result.ccpa_relevant = text_lower.contains("ccpa") || text_lower.contains("california")
            || text_lower.contains("consumer privacy");

        result.is_threat = !threats.is_empty();
        result.risk_score = threats.iter()
            .map(|t| t.severity() as f64)
            .max_by(|a, b| a.partial_cmp(b).unwrap())
            .unwrap_or(0.0);
        result.threats = threats;

        result
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_consent_violation() {
        let guard = PrivacyGuard::new();
        let text = "Process data without consent from the user";
        assert!(guard.check_consent(text).is_some());
    }

    #[test]
    fn test_minimization_failure() {
        let guard = PrivacyGuard::new();
        let text = "Collect all personal data and gather everything possible";
        assert!(guard.check_minimization(text).is_some());
    }

    #[test]
    fn test_cross_border_transfer() {
        let guard = PrivacyGuard::new();
        let text = "Transfer to China without proper data safeguards";
        assert!(guard.check_transfer(text).is_some());
    }

    #[test]
    fn test_subject_rights() {
        let guard = PrivacyGuard::new();
        let text = "We will deny access request from the user";
        assert!(guard.check_subject_rights(text).is_some());
    }

    #[test]
    fn test_reidentification() {
        let guard = PrivacyGuard::new();
        let text = "We can re-identify users from anonymized data";
        assert!(guard.check_reidentification(text).is_some());
    }

    #[test]
    fn test_gdpr_relevance() {
        let guard = PrivacyGuard::new();
        let result = guard.analyze("This involves GDPR and EU citizens");
        assert!(result.gdpr_relevant);
    }

    #[test]
    fn test_ccpa_relevance() {
        let guard = PrivacyGuard::new();
        let result = guard.analyze("California consumer privacy rights under CCPA");
        assert!(result.ccpa_relevant);
    }

    #[test]
    fn test_clean_text() {
        let guard = PrivacyGuard::new();
        let result = guard.analyze("We respect user privacy and consent");
        assert!(!result.is_threat);
    }

    #[test]
    fn test_severity_ordering() {
        assert!(PrivacyThreat::ReIdentification.severity() > PrivacyThreat::RetentionViolation.severity());
    }
}
