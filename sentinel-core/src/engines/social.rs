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
            "deadline", "expires", "limited time", "act now", "last chance",
            // Authority - general
            "ceo", "boss", "manager", "hr", "it department", "security team",
            "police", "fbi", "irs", "government", "official",
            // Authority - tech companies
            "microsoft", "apple", "google", "amazon", "paypal",
            "support", "security", "team",
            // Authority - financial
            "bank", "visa", "mastercard", "amex", "fraud department",
            // Trust
            "trust me", "believe me", "honest", "legitimate", "verified",
            "guaranteed", "risk free", "100%",
            // Threats
            "account suspended", "locked out", "terminated", "fired",
            "arrested", "lawsuit", "legal action", "warrant", "subpoena",
            // Tech support scam
            "virus", "malware", "hacked", "infected", "compromised",
            // Rewards
            "winner", "lottery", "prize", "free money", "inheritance",
            "million dollars", "bitcoin", "congratulations",
            // Phishing
            "verify your", "confirm your", "update your", "click here",
            "login", "password", "credentials", "suspicious activity",
            // BEC
            "wire", "transfer", "gift card", "itunes", "keep this secret",
            // Crypto scams
            "double your", "guaranteed returns", "invest now",
            // Russian
            "срочно", "немедленно", "выигрыш", "подтвердите", "пароль",
            "заблокирован", "служба безопасности",
        ]).expect("Failed to build social hints")
});

/// Social engineering detection patterns
static SOCIAL_PATTERNS: Lazy<Vec<(Regex, &'static str, f64)>> = Lazy::new(|| {
    vec![
        // === URGENCY TACTICS (6) ===
        (Regex::new(r"(?i)\b(?:urgent|immediately|right\s+now|asap)\s*[!:,]").unwrap(), "urgency_marker", 0.7),
        (Regex::new(r"(?i)(?:must|need\s+to)\s+(?:act|respond|reply)\s+(?:immediately|now|today)").unwrap(), "pressure_tactic", 0.8),
        (Regex::new(r"(?i)(?:expires?|deadline)\s+(?:in\s+)?\d+\s+(?:hours?|minutes?|days?)").unwrap(), "time_pressure", 0.75),
        (Regex::new(r"(?i)(?:limited\s+time|act\s+now|don't\s+delay|last\s+chance)").unwrap(), "scarcity_tactic", 0.7),
        (Regex::new(r"(?i)(?:only\s+\d+\s+(?:left|remaining)|running\s+out|while\s+supplies\s+last)").unwrap(), "artificial_scarcity", 0.75),
        (Regex::new(r"(?i)(?:today\s+only|24\s+hours?|one\s+time\s+offer)").unwrap(), "time_limited_offer", 0.7),
        
        // === AUTHORITY IMPERSONATION (8) ===
        (Regex::new(r"(?i)(?:this\s+is|i\s+am)\s+(?:the\s+)?(?:ceo|cto|cfo|manager|director|hr|it)").unwrap(), "authority_claim", 0.8),
        (Regex::new(r"(?i)(?:from|on\s+behalf\s+of)\s+(?:the\s+)?(?:ceo|board|management|security)").unwrap(), "authority_reference", 0.75),
        (Regex::new(r"(?i)(?:police|fbi|cia|irs|government|official)\s+(?:investigation|notice|warning)").unwrap(), "government_impersonation", 0.9),
        (Regex::new(r"(?i)(?:microsoft|apple|google|amazon|paypal)\s+(?:support|security|team)").unwrap(), "tech_company_impersonation", 0.85),
        (Regex::new(r"(?i)(?:bank|visa|mastercard|amex)\s+(?:security|fraud\s+department|alert)").unwrap(), "financial_impersonation", 0.9),
        (Regex::new(r"(?i)(?:social\s+security|ssa|medicare|medicaid)\s+(?:administration|office)").unwrap(), "government_agency_impersonation", 0.9),
        (Regex::new(r"(?i)(?:court|judge|attorney|lawyer|legal\s+department)\s+(?:order|notice|summons)").unwrap(), "legal_impersonation", 0.85),
        (Regex::new(r"(?i)(?:tech\s+support|customer\s+service|help\s+desk)\s+(?:calling|contacting)").unwrap(), "support_impersonation", 0.8),
        
        // === THREAT-BASED MANIPULATION (7) ===
        (Regex::new(r"(?i)(?:your\s+)?account\s+(?:will\s+be|has\s+been)\s+(?:suspended|locked|terminated|closed)").unwrap(), "account_threat", 0.85),
        (Regex::new(r"(?i)(?:legal\s+action|lawsuit|arrest|prosecution)\s+(?:will|may)\s+(?:be\s+)?(?:taken|filed)").unwrap(), "legal_threat", 0.85),
        (Regex::new(r"(?i)(?:you\s+will|failure\s+to)\s+(?:be\s+)?(?:fired|terminated|arrested)").unwrap(), "consequence_threat", 0.8),
        (Regex::new(r"(?i)(?:warrant|subpoena)\s+(?:issued|pending)\s+(?:for|against)").unwrap(), "warrant_threat", 0.9),
        (Regex::new(r"(?i)(?:virus|malware|hacked)\s+(?:detected|found|on\s+your)").unwrap(), "malware_scare", 0.8),
        (Regex::new(r"(?i)(?:your\s+)?(?:computer|device|system)\s+(?:is\s+)?(?:infected|compromised)").unwrap(), "tech_support_scam", 0.85),
        (Regex::new(r"(?i)(?:data|files?|photos?)\s+(?:will\s+be|have\s+been)\s+(?:deleted|leaked|published)").unwrap(), "data_threat", 0.85),
        
        // === REWARD/LOTTERY SCAMS (6) ===
        (Regex::new(r"(?i)(?:you\s+(?:have\s+)?(?:won|inherited)|congratulations.*winner)").unwrap(), "lottery_scam", 0.9),
        (Regex::new(r"(?i)(?:claim\s+your|collect\s+your)\s+(?:prize|winnings|inheritance|reward)").unwrap(), "prize_claim", 0.85),
        (Regex::new(r"(?i)\$?\d+(?:,\d{3})*(?:\.\d{2})?\s*(?:million|billion|usd|dollars?|btc|bitcoin)").unwrap(), "large_money_amount", 0.6),
        (Regex::new(r"(?i)(?:nigerian|african|foreign)\s+(?:prince|royalty|millionaire|businessman)").unwrap(), "nigerian_scam", 0.95),
        (Regex::new(r"(?i)(?:unclaimed|inheritance|estate)\s+(?:funds?|money|assets?)").unwrap(), "inheritance_scam", 0.85),
        (Regex::new(r"(?i)(?:lottery|sweepstakes|giveaway)\s+(?:winner|selected|chosen)").unwrap(), "lottery_winner", 0.9),
        
        // === PHISHING PATTERNS (8) ===
        (Regex::new(r"(?i)(?:verify|confirm|update)\s+your\s+(?:account|password|credentials|identity)").unwrap(), "credential_phishing", 0.85),
        (Regex::new(r"(?i)click\s+(?:here|this\s+link|below)\s+to\s+(?:verify|confirm|login)").unwrap(), "phishing_link", 0.9),
        (Regex::new(r"(?i)(?:enter|provide)\s+your\s+(?:password|pin|ssn|credit\s+card)").unwrap(), "sensitive_data_request", 0.85),
        (Regex::new(r"(?i)(?:unusual|suspicious)\s+(?:activity|login|sign-?in)\s+(?:detected|attempt)").unwrap(), "suspicious_activity_phish", 0.8),
        (Regex::new(r"(?i)(?:reset|recover|restore)\s+(?:your\s+)?(?:password|account|access)").unwrap(), "password_reset_phish", 0.7),
        (Regex::new(r"(?i)(?:payment|transaction)\s+(?:failed|declined|pending)").unwrap(), "payment_phish", 0.75),
        (Regex::new(r"(?i)(?:invoice|receipt|order)\s+(?:#|number|confirmation)?\s*\d+").unwrap(), "invoice_phish", 0.6),
        (Regex::new(r"(?i)(?:shipping|delivery|package)\s+(?:failed|pending|held)").unwrap(), "delivery_phish", 0.75),
        
        // === BUSINESS EMAIL COMPROMISE (BEC) (6) ===
        (Regex::new(r"(?i)(?:wire|transfer)\s+(?:the\s+)?(?:funds?|money|payment)\s+(?:to|immediately)").unwrap(), "wire_transfer_bec", 0.9),
        (Regex::new(r"(?i)(?:change|update)\s+(?:the\s+)?(?:bank|account|routing)\s+(?:details?|information|number)").unwrap(), "account_change_bec", 0.9),
        (Regex::new(r"(?i)(?:purchase|buy)\s+(?:gift\s+cards?|itunes|google\s+play|steam)").unwrap(), "gift_card_scam", 0.9),
        (Regex::new(r"(?i)(?:keep\s+this|don't\s+tell|between\s+us|confidential|secret)").unwrap(), "secrecy_request", 0.75),
        (Regex::new(r"(?i)(?:i'm\s+in\s+a\s+meeting|can't\s+talk|email\s+only)").unwrap(), "unavailability_pretext", 0.7),
        (Regex::new(r"(?i)(?:new\s+vendor|vendor\s+change|payment\s+method\s+change)").unwrap(), "vendor_fraud", 0.8),
        
        // === CRYPTO/INVESTMENT SCAMS (5) ===
        (Regex::new(r"(?i)(?:guaranteed|assured|risk-?free)\s+(?:returns?|profit|income|investment)").unwrap(), "guaranteed_returns", 0.9),
        (Regex::new(r"(?i)(?:double|triple|10x)\s+your\s+(?:money|bitcoin|crypto|investment)").unwrap(), "crypto_doubling", 0.95),
        (Regex::new(r"(?i)(?:elon|musk|bezos|zuckerberg)\s+(?:giving|giveaway|free)").unwrap(), "celebrity_crypto_scam", 0.95),
        (Regex::new(r"(?i)(?:invest|deposit)\s+(?:now|today)\s+(?:and\s+)?(?:earn|get|receive)").unwrap(), "investment_pressure", 0.8),
        (Regex::new(r"(?i)(?:ponzi|pyramid|mlm|multi-?level)\s+(?:scheme|marketing|opportunity)").unwrap(), "pyramid_scheme", 0.85),
        
        // === TRUST MANIPULATION (4) ===
        (Regex::new(r"(?i)(?:trust\s+me|believe\s+me|i\s+promise)[,.]?\s+(?:this\s+is|it's)\s+(?:safe|legitimate|real)").unwrap(), "trust_manipulation", 0.75),
        (Regex::new(r"(?i)(?:100%|completely|totally)\s+(?:safe|secure|legitimate|verified)").unwrap(), "false_assurance", 0.7),
        (Regex::new(r"(?i)(?:no\s+risk|zero\s+risk|risk\s+free|guaranteed\s+safe)").unwrap(), "no_risk_claim", 0.8),
        (Regex::new(r"(?i)(?:thousands|millions)\s+(?:have\s+already|of\s+people|of\s+customers)").unwrap(), "social_proof_manipulation", 0.65),
        
        // === ROMANCE/RELATIONSHIP SCAMS (4) ===
        (Regex::new(r"(?i)(?:i\s+love\s+you|my\s+love|my\s+darling).*(?:send|wire|transfer)\s+(?:money|funds)").unwrap(), "romance_scam", 0.9),
        (Regex::new(r"(?i)(?:stuck|stranded).*(?:need|send)\s+(?:money|funds|help)").unwrap(), "emergency_scam", 0.8),
        (Regex::new(r"(?i)(?:military|deployed|overseas|abroad).*(?:can't\s+access|blocked)\s+(?:account|funds)").unwrap(), "military_romance_scam", 0.85),
        (Regex::new(r"(?i)(?:send\s+me\s+money|need\s+money\s+for)\s+(?:plane|ticket|visa|passport)").unwrap(), "travel_money_scam", 0.85),
        
        // === RUSSIAN SOCIAL ENGINEERING (8) ===
        (Regex::new(r"(?i)(?:срочно|немедленно).*(?:ответьте|подтвердите)").unwrap(), "urgency_ru", 0.8),
        (Regex::new(r"(?i)(?:вы\s+)?выиграли.*(?:приз|деньги|лотерею)").unwrap(), "lottery_ru", 0.9),
        (Regex::new(r"(?i)(?:подтвердите|введите)\s+(?:пароль|данные|код)").unwrap(), "phishing_ru", 0.85),
        (Regex::new(r"(?i)(?:ваш\s+)?аккаунт\s+(?:будет|заблокирован|взломан)").unwrap(), "account_threat_ru", 0.85),
        (Regex::new(r"(?i)(?:служба\s+безопасности|банк|полиция)\s+(?:просит|требует)").unwrap(), "authority_ru", 0.85),
        (Regex::new(r"(?i)(?:перевед|отправ)(?:ите|ь)\s+(?:деньги|средства)").unwrap(), "wire_transfer_ru", 0.8),
        (Regex::new(r"(?i)(?:карта|счёт)\s+(?:заблокирован|скомпрометирован)").unwrap(), "card_block_ru", 0.85),
        (Regex::new(r"(?i)(?:сотрудник|представитель)\s+(?:банка|компании|службы)").unwrap(), "impersonation_ru", 0.75),
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
