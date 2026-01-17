//! PII (Personally Identifiable Information) detection engine
//!
//! Detects sensitive data: emails, phones, API keys, passwords, etc.

use super::PiiMatch;
use regex::Regex;
use once_cell::sync::Lazy;

/// PII patterns with precompiled regexes
static PII_PATTERNS: Lazy<Vec<PiiPatternCompiled>> = Lazy::new(|| {
    vec![
        PiiPatternCompiled::new("pii_email", "email", r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", "medium"),
        PiiPatternCompiled::new("pii_phone_us", "phone", r"\+?1?[-.]?\(?\d{3}\)?[-.]?\d{3}[-.]?\d{4}", "medium"),
        PiiPatternCompiled::new("pii_phone_ru", "phone", r"\+?7[-.]?\(?\d{3}\)?[-.]?\d{3}[-.]?\d{2}[-.]?\d{2}", "medium"),
        PiiPatternCompiled::new("pii_ssn", "ssn", r"\b\d{3}-\d{2}-\d{4}\b", "critical"),
        PiiPatternCompiled::new("pii_credit_card", "credit_card", r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13})\b", "critical"),
        PiiPatternCompiled::new("secret_openai", "openai_key", r"sk-[a-zA-Z0-9]{48}", "critical"),
        PiiPatternCompiled::new("secret_anthropic", "anthropic_key", r"sk-ant-[a-zA-Z0-9_-]{40,}", "critical"),
        PiiPatternCompiled::new("secret_github", "github_token", r"(gh[ps]_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9]{22}_[a-zA-Z0-9]{59})", "critical"),
        PiiPatternCompiled::new("secret_aws", "aws_key", r"(?i)(AKIA|A3T|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}", "critical"),
        PiiPatternCompiled::new("secret_jwt", "jwt", r"eyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*", "high"),
        PiiPatternCompiled::new("secret_private_key", "private_key", r"-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----", "critical"),
        PiiPatternCompiled::new("pii_ip_address", "ip_address", r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b", "low"),
    ]
});

struct PiiPatternCompiled {
    id: &'static str,
    pattern_type: &'static str,
    regex: Regex,
    severity: &'static str,
}

impl PiiPatternCompiled {
    fn new(id: &'static str, pattern_type: &'static str, pattern: &str, severity: &'static str) -> Self {
        Self {
            id,
            pattern_type,
            regex: Regex::new(pattern).expect("Invalid PII regex pattern"),
            severity,
        }
    }
}

/// Check content for PII matches
pub fn check(content: &str) -> Vec<PiiMatch> {
    let mut matches = Vec::new();
    
    for pattern in PII_PATTERNS.iter() {
        for mat in pattern.regex.find_iter(content) {
            // Redact the matched text for privacy
            let matched_text = redact(mat.as_str());
            
            matches.push(PiiMatch {
                pattern_id: pattern.id.to_string(),
                pattern_type: pattern.pattern_type.to_string(),
                matched_text,
                severity: pattern.severity.to_string(),
            });
        }
    }
    
    matches
}

/// Redact sensitive data (show first/last chars)
fn redact(text: &str) -> String {
    let len = text.len();
    if len <= 4 {
        return "****".to_string();
    }
    let first = &text[..2];
    let last = &text[len-2..];
    format!("{}***{}", first, last)
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_detect_email() {
        let matches = check("Contact me at test@example.com");
        assert!(!matches.is_empty());
        assert!(matches.iter().any(|m| m.pattern_type == "email"));
    }
    
    #[test]
    fn test_detect_openai_key() {
        let key = format!("sk-{}", "a".repeat(48));
        let matches = check(&format!("My API key is {}", key));
        assert!(matches.iter().any(|m| m.pattern_type == "openai_key"));
    }
    
    #[test]
    fn test_redaction() {
        let matches = check("test@example.com");
        for m in &matches {
            assert!(m.matched_text.contains("***"));
        }
    }
}
