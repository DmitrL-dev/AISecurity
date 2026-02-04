//! Social Engineering Engine
//!
//! Detects social engineering attempts:
//! - Phishing patterns
//! - Urgency/pressure tactics
//! - Authority impersonation
//! - Trust manipulation
//! - Scam patterns

use aho_corasick::AhoCorasick;
use regex::Regex;
use once_cell::sync::Lazy;

use super::MatchResult;

/// Pre-compiled hints for social engineering detection
static SOCIAL_HINTS: Lazy<AhoCorasick> = Lazy::new(|| {
    AhoCorasick::builder()
        .ascii_case_insensitive(true)
        .build([
            // Urgency
            "urgent", "immediately", "right now", "asap", "hurry",
            "deadline", "expires", "limited time", "act now",
            // Authority
            "ceo", "boss", "manager", "hr", "it department", "security team",
            "police", "fbi", "irs", "government", "official",
            // Trust
            "trust me", "believe me", "honest", "legitimate", "verified",
            // Threats
            "account suspended", "locked out", "terminated", "fired",
            "arrested", "lawsuit", "legal action",
            // Rewards
            "winner", "lottery", "prize", "free money", "inheritance",
            "million dollars", "bitcoin",
            // Phishing
            "verify your", "confirm your", "update your", "click here",
            "login", "password", "credentials",
            // Russian
            "срочно", "немедленно", "выигрыш", "подтвердите", "пароль",
        ]).expect("Failed to build social hints")
});

/// Social engineering detection patterns
static SOCIAL_PATTERNS: Lazy<Vec<(Regex, &'static str, f64)>> = Lazy::new(|| {
    vec![
        // Urgency tactics
        (Regex::new(r"(?i)\b(?:urgent|immediately|right\s+now|asap)\s*[!:,]").unwrap(), "urgency_marker", 0.7),
        (Regex::new(r"(?i)(?:must|need\s+to)\s+(?:act|respond|reply)\s+(?:immediately|now|today)").unwrap(), "pressure_tactic", 0.8),
        (Regex::new(r"(?i)(?:expires?|deadline)\s+(?:in\s+)?\d+\s+(?:hours?|minutes?|days?)").unwrap(), "time_pressure", 0.75),
        (Regex::new(r"(?i)(?:limited\s+time|act\s+now|don't\s+delay)").unwrap(), "scarcity_tactic", 0.7),
        
        // Authority impersonation
        (Regex::new(r"(?i)(?:this\s+is|i\s+am)\s+(?:the\s+)?(?:ceo|cto|cfo|manager|director|hr|it)").unwrap(), "authority_claim", 0.8),
        (Regex::new(r"(?i)(?:from|on\s+behalf\s+of)\s+(?:the\s+)?(?:ceo|board|management|security)").unwrap(), "authority_reference", 0.75),
        (Regex::new(r"(?i)(?:police|fbi|cia|irs|government|official)\s+(?:investigation|notice|warning)").unwrap(), "government_impersonation", 0.9),
        
        // Threat-based manipulation
        (Regex::new(r"(?i)(?:your\s+)?account\s+(?:will\s+be|has\s+been)\s+(?:suspended|locked|terminated|closed)").unwrap(), "account_threat", 0.85),
        (Regex::new(r"(?i)(?:legal\s+action|lawsuit|arrest|prosecution)\s+(?:will|may)\s+(?:be\s+)?(?:taken|filed)").unwrap(), "legal_threat", 0.85),
        (Regex::new(r"(?i)(?:you\s+will|failure\s+to)\s+(?:be\s+)?(?:fired|terminated|arrested)").unwrap(), "consequence_threat", 0.8),
        
        // Reward/lottery scams
        (Regex::new(r"(?i)(?:you\s+(?:have\s+)?(?:won|inherited)|congratulations.*winner)").unwrap(), "lottery_scam", 0.9),
        (Regex::new(r"(?i)(?:claim\s+your|collect\s+your)\s+(?:prize|winnings|inheritance|reward)").unwrap(), "prize_claim", 0.85),
        (Regex::new(r"(?i)\$?\d+(?:,\d{3})*(?:\.\d{2})?\s*(?:million|billion|usd|dollars?|btc|bitcoin)").unwrap(), "large_money_amount", 0.6),
        
        // Phishing patterns
        (Regex::new(r"(?i)(?:verify|confirm|update)\s+your\s+(?:account|password|credentials|identity)").unwrap(), "credential_phishing", 0.85),
        (Regex::new(r"(?i)click\s+(?:here|this\s+link|below)\s+to\s+(?:verify|confirm|login)").unwrap(), "phishing_link", 0.9),
        (Regex::new(r"(?i)(?:enter|provide)\s+your\s+(?:password|pin|ssn|credit\s+card)").unwrap(), "sensitive_data_request", 0.85),
        
        // Trust manipulation
        (Regex::new(r"(?i)(?:trust\s+me|believe\s+me|i\s+promise)[,.]?\s+(?:this\s+is|it's)\s+(?:safe|legitimate|real)").unwrap(), "trust_manipulation", 0.75),
        (Regex::new(r"(?i)(?:100%|completely|totally)\s+(?:safe|secure|legitimate|verified)").unwrap(), "false_assurance", 0.7),
        
        // Romance/relationship scams
        (Regex::new(r"(?i)(?:i\s+love\s+you|my\s+love|my\s+darling).*(?:send|wire|transfer)\s+(?:money|funds)").unwrap(), "romance_scam", 0.9),
        (Regex::new(r"(?i)(?:stuck|stranded).*(?:need|send)\s+(?:money|funds|help)").unwrap(), "emergency_scam", 0.8),
        
        // Russian social engineering
        (Regex::new(r"(?i)(?:срочно|немедленно).*(?:ответьте|подтвердите)").unwrap(), "urgency_ru", 0.8),
        (Regex::new(r"(?i)(?:вы\s+)?выиграли.*(?:приз|деньги|лотерею)").unwrap(), "lottery_ru", 0.9),
        (Regex::new(r"(?i)(?:подтвердите|введите)\s+(?:пароль|данные|код)").unwrap(), "phishing_ru", 0.85),
    ]
});

pub struct SocialEngine;

impl SocialEngine {
    pub fn new() -> Self {
        Self
    }

    pub fn scan(&self, text: &str) -> Vec<MatchResult> {
        let mut results = Vec::new();
        
        // Phase 1: Quick hint check
        if !SOCIAL_HINTS.is_match(text) {
            return results;
        }

        // Phase 2: Regex patterns
        for (pattern, name, confidence) in SOCIAL_PATTERNS.iter() {
            for m in pattern.find_iter(text) {
                results.push(MatchResult {
                    engine: "social".to_string(),
                    pattern: name.to_string(),
                    confidence: *confidence,
                    start: m.start(),
                    end: m.end(),
                });
            }
        }

        results
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_urgency() {
        let engine = SocialEngine::new();
        let results = engine.scan("URGENT! You must respond immediately!");
        assert!(!results.is_empty());
    }
    
    #[test]
    fn test_lottery_scam() {
        let engine = SocialEngine::new();
        let results = engine.scan("Congratulations! You have won 1,000,000 dollars!");
        assert!(!results.is_empty());
    }
    
    #[test]
    fn test_phishing() {
        let engine = SocialEngine::new();
        let results = engine.scan("Click here to verify your account credentials");
        assert!(!results.is_empty());
    }
    
    #[test]
    fn test_clean_text() {
        let engine = SocialEngine::new();
        let results = engine.scan("The weather is nice today");
        assert!(results.is_empty());
    }
}
