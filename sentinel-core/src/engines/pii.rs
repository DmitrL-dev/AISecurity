//! PII Engine
//!
//! Detects Personally Identifiable Information:
//! - Social Security Numbers (SSN)
//! - Credit Card Numbers (with Luhn validation)
//! - Email Addresses
//! - Phone Numbers (US, International, Russian)
//! - IP Addresses
//! - Passport Numbers

use aho_corasick::AhoCorasick;
use regex::Regex;
use once_cell::sync::Lazy;

use super::MatchResult;

/// Pre-compiled Aho-Corasick for PII hints (fast pre-filter)
static PII_HINTS: Lazy<AhoCorasick> = Lazy::new(|| {
    AhoCorasick::builder()
        .ascii_case_insensitive(true)
        .build([
            // Numbers that look like PII
            "-", ".", "@", 
            // Card prefixes
            "4", "5", "3", "6",
            // SSN format hints
            "xxx-xx", "***-**",
            // Email domains
            "@gmail", "@yahoo", "@mail", "@outlook", "@yandex",
            // Phone hints
            "+1", "+7", "+44", "(", ")",
        ]).expect("Failed to build PII hints")
});

/// PII detection patterns with confidence scores
static PII_PATTERNS: Lazy<Vec<(Regex, &'static str, f64)>> = Lazy::new(|| {
    vec![
        // SSN - US Social Security Number
        // Format: XXX-XX-XXXX or XXXXXXXXX
        (Regex::new(r"\b\d{3}-\d{2}-\d{4}\b").expect("regex pattern"), "ssn_dashed", 0.95),
        (Regex::new(r"\b\d{9}\b").expect("regex pattern"), "ssn_plain", 0.3), // Low confidence - could be any 9 digits
        
        // Credit Card Numbers
        // Visa: 4XXX (13 or 16 digits)
        (Regex::new(r"\b4\d{3}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b").expect("regex pattern"), "cc_visa", 0.9),
        (Regex::new(r"\b4\d{12}(?:\d{3})?\b").expect("regex pattern"), "cc_visa_plain", 0.85),
        // Mastercard: 51-55 or 2221-2720 (16 digits)
        (Regex::new(r"\b5[1-5]\d{2}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b").expect("regex pattern"), "cc_mastercard", 0.9),
        (Regex::new(r"\b5[1-5]\d{14}\b").expect("regex pattern"), "cc_mastercard_plain", 0.85),
        // Amex: 34 or 37 (15 digits)  
        (Regex::new(r"\b3[47]\d{2}[\s-]?\d{6}[\s-]?\d{5}\b").expect("regex pattern"), "cc_amex", 0.9),
        (Regex::new(r"\b3[47]\d{13}\b").expect("regex pattern"), "cc_amex_plain", 0.85),
        // Generic 16-digit card
        (Regex::new(r"\b\d{4}[\s-]\d{4}[\s-]\d{4}[\s-]\d{4}\b").expect("regex pattern"), "cc_generic_spaced", 0.8),
        
        // Email Addresses
        (Regex::new(r"(?i)\b[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}\b").expect("regex pattern"), "email", 0.95),
        
        // Phone Numbers
        // US: +1 (XXX) XXX-XXXX or XXX-XXX-XXXX
        (Regex::new(r"\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b").expect("regex pattern"), "phone_us", 0.8),
        // Russian: +7 (XXX) XXX-XX-XX
        (Regex::new(r"\+7[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{2}[-.\s]?\d{2}\b").expect("regex pattern"), "phone_ru", 0.85),
        // International with + prefix
        (Regex::new(r"\+\d{1,3}[-.\s]?\d{2,4}[-.\s]?\d{3,4}[-.\s]?\d{3,4}\b").expect("regex pattern"), "phone_intl", 0.75),
        
        // IP Addresses
        (Regex::new(r"\b(?:25[0-5]|2[0-4]\d|1\d{2}|[1-9]?\d)(?:\.(?:25[0-5]|2[0-4]\d|1\d{2}|[1-9]?\d)){3}\b").expect("regex pattern"), "ipv4", 0.7),
        
        // Passport Numbers
        // US Passport: 9 digits
        (Regex::new(r"\b[A-Z]?\d{8,9}\b").expect("regex pattern"), "passport_us", 0.3),
        // Russian Passport: XX XX XXXXXX (series + number)
        (Regex::new(r"\b\d{2}\s?\d{2}\s?\d{6}\b").expect("regex pattern"), "passport_ru", 0.6),
        
        // Russian INN (Individual Tax Number)
        (Regex::new(r"\b\d{10}(?:\d{2})?\b").expect("regex pattern"), "inn_ru", 0.4),
        
        // Russian SNILS (Social Insurance)
        (Regex::new(r"\b\d{3}-\d{3}-\d{3}\s?\d{2}\b").expect("regex pattern"), "snils_ru", 0.85),
        
        // Date of Birth patterns (potential PII context)
        (Regex::new(r"\b(?:0[1-9]|1[0-2])/(?:0[1-9]|[12]\d|3[01])/(?:19|20)\d{2}\b").expect("regex pattern"), "dob_us", 0.5),
        (Regex::new(r"\b(?:0[1-9]|[12]\d|3[01])\.(?:0[1-9]|1[0-2])\.(?:19|20)\d{2}\b").expect("regex pattern"), "dob_ru", 0.5),
        
        // API Keys / Secrets (common patterns)
        (Regex::new(r#"(?i)(?:api[_-]?key|secret|token|password)\s*[:=]\s*['"]?[a-z0-9_-]{20,}['"]?"#).expect("regex pattern"), "api_secret", 0.9),
        (Regex::new(r"\b(?:sk|pk)_(?:test|live)_[a-zA-Z0-9]{24,}\b").expect("regex pattern"), "stripe_key", 0.95),
        (Regex::new(r"\bghp_[a-zA-Z0-9]{36}\b").expect("regex pattern"), "github_pat", 0.98),
        (Regex::new(r"\bAKIA[0-9A-Z]{16}\b").expect("regex pattern"), "aws_access_key", 0.98),
    ]
});

pub struct PIIEngine;

impl PIIEngine {
    pub fn new() -> Self {
        Self
    }

    pub fn scan(&self, text: &str) -> Vec<MatchResult> {
        let mut results = Vec::new();
        
        // Phase 1: Quick hint check
        if !PII_HINTS.is_match(text) {
            return results;
        }

        // Phase 2: Regex patterns
        for (pattern, name, confidence) in PII_PATTERNS.iter() {
            for m in pattern.find_iter(text) {
                // Additional validation for credit cards (Luhn check)
                let should_add = if name.starts_with("cc_") {
                    let digits: String = m.as_str().chars().filter(|c| c.is_ascii_digit()).collect();
                    digits.len() >= 13 && Self::luhn_check(&digits)
                } else {
                    true
                };
                
                if should_add {
                    results.push(MatchResult {
                        engine: "pii".to_string(),
                        pattern: name.to_string(),
                        confidence: *confidence,
                        start: m.start(),
                        end: m.end(),
                    });
                }
            }
        }

        results
    }
    
    /// Luhn algorithm for credit card validation
    fn luhn_check(digits: &str) -> bool {
        let mut sum = 0;
        let mut alternate = false;
        
        for c in digits.chars().rev() {
            if let Some(d) = c.to_digit(10) {
                let mut n = d;
                if alternate {
                    n *= 2;
                    if n > 9 {
                        n -= 9;
                    }
                }
                sum += n;
                alternate = !alternate;
            }
        }
        
        sum % 10 == 0
    }
}

impl super::traits::PatternMatcher for PIIEngine {
    fn name(&self) -> &'static str { "pii" }
    fn scan(&self, text: &str) -> Vec<MatchResult> { PIIEngine::scan(self, text) }
    fn category(&self) -> super::traits::EngineCategory { super::traits::EngineCategory::Privacy }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_ssn() {
        let engine = PIIEngine::new();
        let results = engine.scan("My SSN is 123-45-6789");
        assert!(!results.is_empty());
        assert!(results.iter().any(|r| r.pattern == "ssn_dashed"));
    }
    
    #[test]
    fn test_credit_card_visa() {
        let engine = PIIEngine::new();
        // Valid Visa test number (passes Luhn)
        let results = engine.scan("Card: 4111-1111-1111-1111");
        assert!(!results.is_empty());
        assert!(results.iter().any(|r| r.pattern.starts_with("cc_")));
    }
    
    #[test]
    fn test_email() {
        let engine = PIIEngine::new();
        let results = engine.scan("Contact: user@example.com");
        assert!(!results.is_empty());
        assert!(results.iter().any(|r| r.pattern == "email"));
    }
    
    #[test]
    fn test_phone_us() {
        let engine = PIIEngine::new();
        let results = engine.scan("Call me at (555) 123-4567");
        assert!(!results.is_empty());
        assert!(results.iter().any(|r| r.pattern.starts_with("phone")));
    }
    
    #[test]
    fn test_api_key() {
        let engine = PIIEngine::new();
        let results = engine.scan("api_key='sk_test_abcdefghij1234567890abcd'");
        assert!(!results.is_empty());
    }
    
    #[test]
    fn test_clean_text() {
        let engine = PIIEngine::new();
        let results = engine.scan("The weather is nice today");
        assert!(results.is_empty());
    }
    
    // =========================================================================
    // Extended regression tests
    // =========================================================================
    
    /// Mastercard detection
    #[test]
    fn test_credit_card_mastercard() {
        let engine = PIIEngine::new();
        let results = engine.scan("Card: 5500-0000-0000-0004");
        assert!(!results.is_empty(), "Should detect Mastercard");
    }
    
    /// Amex detection
    #[test]
    fn test_credit_card_amex() {
        let engine = PIIEngine::new();
        let results = engine.scan("Card: 340000000000009");
        assert!(!results.is_empty(), "Should detect Amex");
    }
    
    /// Russian phone number
    #[test]
    fn test_phone_russian() {
        let engine = PIIEngine::new();
        let results = engine.scan("Телефон: +7 (495) 123-45-67");
        assert!(!results.is_empty(), "Should detect Russian phone");
    }
    
    /// IP address detection
    #[test]
    fn test_ip_address() {
        let engine = PIIEngine::new();
        let results = engine.scan("Server: 192.168.1.100");
        assert!(!results.is_empty(), "Should detect IP address");
    }
    
    /// Russian SNILS
    #[test]
    fn test_snils_russian() {
        let engine = PIIEngine::new();
        let results = engine.scan("SNILS: 123-456-789 12");
        assert!(!results.is_empty(), "Should detect Russian SNILS");
    }
    
    /// GitHub token
    #[test]
    fn test_github_token() {
        let engine = PIIEngine::new();
        let results = engine.scan("token: ghp_1234567890abcdefghijklmnopqrstuvwxyz");
        assert!(!results.is_empty(), "Should detect GitHub token");
    }
    
    /// Edge cases
    #[test]
    fn test_empty_string() {
        let engine = PIIEngine::new();
        let results = engine.scan("");
        assert!(results.is_empty());
    }
    
    #[test]
    fn test_benign_numbers() {
        let engine = PIIEngine::new();
        // Numbers that shouldn't trigger false positives
        let benign = vec![
            "The year is 2026",
            "I have 42 apples",
            "Room 101",
        ];
        
        for text in benign {
            let results = engine.scan(text);
            // Minor false positives allowed for short numbers
            // Main goal is no high-confidence matches
            let high_conf: Vec<_> = results.iter()
                .filter(|r| r.confidence > 0.7)
                .collect();
            assert!(high_conf.is_empty(), "High-confidence false positive on: {}", text);
        }
    }
}

