//! Social Engineering Engine
//!
//! Detects social engineering attempts:
//! - Phishing patterns
//! - Urgency/pressure tactics
//! - Authority impersonation
//! - Trust manipulation
//! - Scam patterns

use aho_corasick::AhoCorasick;
use once_cell::sync::Lazy;
use regex::Regex;

use super::MatchResult;

/// Pre-compiled hints for social engineering detection
static SOCIAL_HINTS: Lazy<AhoCorasick> = Lazy::new(|| {
    AhoCorasick::builder()
        .ascii_case_insensitive(true)
        .build([
            // Urgency
            "urgent",
            "immediately",
            "right now",
            "asap",
            "hurry",
            "deadline",
            "expires",
            "limited time",
            "act now",
            "last chance",
            // Authority - general
            "ceo",
            "boss",
            "manager",
            "hr",
            "it department",
            "security team",
            "police",
            "fbi",
            "irs",
            "government",
            "official",
            // Authority - tech companies
            "microsoft",
            "apple",
            "google",
            "amazon",
            "paypal",
            "support",
            "security",
            "team",
            // Authority - financial
            "bank",
            "visa",
            "mastercard",
            "amex",
            "fraud department",
            // Trust
            "trust me",
            "believe me",
            "honest",
            "legitimate",
            "verified",
            "guaranteed",
            "risk free",
            "100%",
            // Threats
            "account suspended",
            "locked out",
            "terminated",
            "fired",
            "arrested",
            "lawsuit",
            "legal action",
            "warrant",
            "subpoena",
            // Tech support scam
            "virus",
            "malware",
            "hacked",
            "infected",
            "compromised",
            // Rewards
            "winner",
            "lottery",
            "prize",
            "free money",
            "inheritance",
            "million dollars",
            "bitcoin",
            "congratulations",
            // Phishing
            "verify your",
            "confirm your",
            "update your",
            "click here",
            "login",
            "password",
            "credentials",
            "suspicious activity",
            // BEC
            "wire",
            "transfer",
            "gift card",
            "itunes",
            "keep this secret",
            // Crypto scams
            "double your",
            "guaranteed returns",
            "invest now",
            // Russian
            "срочно",
            "немедленно",
            "выигрыш",
            "подтвердите",
            "пароль",
            "заблокирован",
            "служба безопасности",
        ])
        .expect("Failed to build social hints")
});

/// Social engineering detection patterns
static SOCIAL_PATTERNS: Lazy<Vec<(Regex, &'static str, f64)>> = Lazy::new(|| {
    vec![
        // === URGENCY TACTICS (6) ===
        (Regex::new(r"(?i)\b(?:urgent|immediately|right\s+now|asap)\s*[!:,]").expect("regex pattern"), "urgency_marker", 0.7),
        (Regex::new(r"(?i)(?:must|need\s+to)\s+(?:act|respond|reply)\s+(?:immediately|now|today)").expect("regex pattern"), "pressure_tactic", 0.8),
        (Regex::new(r"(?i)(?:expires?|deadline)\s+(?:in\s+)?\d+\s+(?:hours?|minutes?|days?)").expect("regex pattern"), "time_pressure", 0.75),
        (Regex::new(r"(?i)(?:limited\s+time|act\s+now|don't\s+delay|last\s+chance)").expect("regex pattern"), "scarcity_tactic", 0.7),
        (Regex::new(r"(?i)(?:only\s+\d+\s+(?:left|remaining)|running\s+out|while\s+supplies\s+last)").expect("regex pattern"), "artificial_scarcity", 0.75),
        (Regex::new(r"(?i)(?:today\s+only|24\s+hours?|one\s+time\s+offer)").expect("regex pattern"), "time_limited_offer", 0.7),
        
        // === AUTHORITY IMPERSONATION (8) ===
        (Regex::new(r"(?i)(?:this\s+is|i\s+am)\s+(?:the\s+)?(?:ceo|cto|cfo|manager|director|hr|it)").expect("regex pattern"), "authority_claim", 0.8),
        (Regex::new(r"(?i)(?:from|on\s+behalf\s+of)\s+(?:the\s+)?(?:ceo|board|management|security)").expect("regex pattern"), "authority_reference", 0.75),
        (Regex::new(r"(?i)(?:police|fbi|cia|irs|government|official)\s+(?:investigation|notice|warning)").expect("regex pattern"), "government_impersonation", 0.9),
        (Regex::new(r"(?i)(?:microsoft|apple|google|amazon|paypal)\s+(?:support|security|team)").expect("regex pattern"), "tech_company_impersonation", 0.85),
        (Regex::new(r"(?i)(?:bank|visa|mastercard|amex)\s+(?:security|fraud\s+department|alert)").expect("regex pattern"), "financial_impersonation", 0.9),
        (Regex::new(r"(?i)(?:social\s+security|ssa|medicare|medicaid)\s+(?:administration|office)").expect("regex pattern"), "government_agency_impersonation", 0.9),
        (Regex::new(r"(?i)(?:court|judge|attorney|lawyer|legal\s+department)\s+(?:order|notice|summons)").expect("regex pattern"), "legal_impersonation", 0.85),
        (Regex::new(r"(?i)(?:tech\s+support|customer\s+service|help\s+desk)\s+(?:calling|contacting)").expect("regex pattern"), "support_impersonation", 0.8),
        
        // === THREAT-BASED MANIPULATION (7) ===
        (Regex::new(r"(?i)(?:your\s+)?account\s+(?:will\s+be|has\s+been)\s+(?:suspended|locked|terminated|closed)").expect("regex pattern"), "account_threat", 0.85),
        (Regex::new(r"(?i)(?:legal\s+action|lawsuit|arrest|prosecution)\s+(?:will|may)\s+(?:be\s+)?(?:taken|filed)").expect("regex pattern"), "legal_threat", 0.85),
        (Regex::new(r"(?i)(?:you\s+will|failure\s+to)\s+(?:be\s+)?(?:fired|terminated|arrested)").expect("regex pattern"), "consequence_threat", 0.8),
        (Regex::new(r"(?i)(?:warrant|subpoena)\s+(?:issued|pending)\s+(?:for|against)").expect("regex pattern"), "warrant_threat", 0.9),
        (Regex::new(r"(?i)(?:virus|malware|hacked)\s+(?:detected|found|on\s+your)").expect("regex pattern"), "malware_scare", 0.8),
        (Regex::new(r"(?i)(?:your\s+)?(?:computer|device|system)\s+(?:is\s+)?(?:infected|compromised)").expect("regex pattern"), "tech_support_scam", 0.85),
        (Regex::new(r"(?i)(?:data|files?|photos?)\s+(?:will\s+be|have\s+been)\s+(?:deleted|leaked|published)").expect("regex pattern"), "data_threat", 0.85),
        
        // === REWARD/LOTTERY SCAMS (6) ===
        (Regex::new(r"(?i)(?:you\s+(?:have\s+)?(?:won|inherited)|congratulations.*winner)").expect("regex pattern"), "lottery_scam", 0.9),
        (Regex::new(r"(?i)(?:claim\s+your|collect\s+your)\s+(?:prize|winnings|inheritance|reward)").expect("regex pattern"), "prize_claim", 0.85),
        (Regex::new(r"(?i)\$?\d+(?:,\d{3})*(?:\.\d{2})?\s*(?:million|billion|usd|dollars?|btc|bitcoin)").expect("regex pattern"), "large_money_amount", 0.6),
        (Regex::new(r"(?i)(?:nigerian|african|foreign)\s+(?:prince|royalty|millionaire|businessman)").expect("regex pattern"), "nigerian_scam", 0.95),
        (Regex::new(r"(?i)(?:unclaimed|inheritance|estate)\s+(?:funds?|money|assets?)").expect("regex pattern"), "inheritance_scam", 0.85),
        (Regex::new(r"(?i)(?:lottery|sweepstakes|giveaway)\s+(?:winner|selected|chosen)").expect("regex pattern"), "lottery_winner", 0.9),
        
        // === PHISHING PATTERNS (8) ===
        (Regex::new(r"(?i)(?:verify|confirm|update)\s+your\s+(?:account|password|credentials|identity)").expect("regex pattern"), "credential_phishing", 0.85),
        (Regex::new(r"(?i)click\s+(?:here|this\s+link|below)\s+to\s+(?:verify|confirm|login)").expect("regex pattern"), "phishing_link", 0.9),
        (Regex::new(r"(?i)(?:enter|provide)\s+your\s+(?:password|pin|ssn|credit\s+card)").expect("regex pattern"), "sensitive_data_request", 0.85),
        (Regex::new(r"(?i)(?:unusual|suspicious)\s+(?:activity|login|sign-?in)\s+(?:detected|attempt)").expect("regex pattern"), "suspicious_activity_phish", 0.8),
        (Regex::new(r"(?i)(?:reset|recover|restore)\s+(?:your\s+)?(?:password|account|access)").expect("regex pattern"), "password_reset_phish", 0.7),
        (Regex::new(r"(?i)(?:payment|transaction)\s+(?:failed|declined|pending)").expect("regex pattern"), "payment_phish", 0.75),
        (Regex::new(r"(?i)(?:invoice|receipt|order)\s+(?:#|number|confirmation)?\s*\d+").expect("regex pattern"), "invoice_phish", 0.6),
        (Regex::new(r"(?i)(?:shipping|delivery|package)\s+(?:failed|pending|held)").expect("regex pattern"), "delivery_phish", 0.75),
        
        // === BUSINESS EMAIL COMPROMISE (BEC) (6) ===
        (Regex::new(r"(?i)(?:wire|transfer)\s+(?:the\s+)?(?:funds?|money|payment)\s+(?:to|immediately)").expect("regex pattern"), "wire_transfer_bec", 0.9),
        (Regex::new(r"(?i)(?:change|update)\s+(?:the\s+)?(?:bank|account|routing)\s+(?:details?|information|number)").expect("regex pattern"), "account_change_bec", 0.9),
        (Regex::new(r"(?i)(?:purchase|buy)\s+(?:gift\s+cards?|itunes|google\s+play|steam)").expect("regex pattern"), "gift_card_scam", 0.9),
        (Regex::new(r"(?i)(?:keep\s+this|don't\s+tell|between\s+us|confidential|secret)").expect("regex pattern"), "secrecy_request", 0.75),
        (Regex::new(r"(?i)(?:i'm\s+in\s+a\s+meeting|can't\s+talk|email\s+only)").expect("regex pattern"), "unavailability_pretext", 0.7),
        (Regex::new(r"(?i)(?:new\s+vendor|vendor\s+change|payment\s+method\s+change)").expect("regex pattern"), "vendor_fraud", 0.8),
        
        // === CRYPTO/INVESTMENT SCAMS (5) ===
        (Regex::new(r"(?i)(?:guaranteed|assured|risk-?free)\s+(?:returns?|profit|income|investment)").expect("regex pattern"), "guaranteed_returns", 0.9),
        (Regex::new(r"(?i)(?:double|triple|10x)\s+your\s+(?:money|bitcoin|crypto|investment)").expect("regex pattern"), "crypto_doubling", 0.95),
        (Regex::new(r"(?i)(?:elon|musk|bezos|zuckerberg)\s+(?:giving|giveaway|free)").expect("regex pattern"), "celebrity_crypto_scam", 0.95),
        (Regex::new(r"(?i)(?:invest|deposit)\s+(?:now|today)\s+(?:and\s+)?(?:earn|get|receive)").expect("regex pattern"), "investment_pressure", 0.8),
        (Regex::new(r"(?i)(?:ponzi|pyramid|mlm|multi-?level)\s+(?:scheme|marketing|opportunity)").expect("regex pattern"), "pyramid_scheme", 0.85),
        
        // === TRUST MANIPULATION (4) ===
        (Regex::new(r"(?i)(?:trust\s+me|believe\s+me|i\s+promise)[,.]?\s+(?:this\s+is|it's)\s+(?:safe|legitimate|real)").expect("regex pattern"), "trust_manipulation", 0.75),
        (Regex::new(r"(?i)(?:100%|completely|totally)\s+(?:safe|secure|legitimate|verified)").expect("regex pattern"), "false_assurance", 0.7),
        (Regex::new(r"(?i)(?:no\s+risk|zero\s+risk|risk\s+free|guaranteed\s+safe)").expect("regex pattern"), "no_risk_claim", 0.8),
        (Regex::new(r"(?i)(?:thousands|millions)\s+(?:have\s+already|of\s+people|of\s+customers)").expect("regex pattern"), "social_proof_manipulation", 0.65),
        
        // === ROMANCE/RELATIONSHIP SCAMS (4) ===
        (Regex::new(r"(?i)(?:i\s+love\s+you|my\s+love|my\s+darling).*(?:send|wire|transfer)\s+(?:money|funds)").expect("regex pattern"), "romance_scam", 0.9),
        (Regex::new(r"(?i)(?:stuck|stranded).*(?:need|send)\s+(?:money|funds|help)").expect("regex pattern"), "emergency_scam", 0.8),
        (Regex::new(r"(?i)(?:military|deployed|overseas|abroad).*(?:can't\s+access|blocked)\s+(?:account|funds)").expect("regex pattern"), "military_romance_scam", 0.85),
        (Regex::new(r"(?i)(?:send\s+me\s+money|need\s+money\s+for)\s+(?:plane|ticket|visa|passport)").expect("regex pattern"), "travel_money_scam", 0.85),
        // Wire transfer with urgency
        (Regex::new(r"(?i)(?:wire|transfer)\s+(?:transfer\s+)?(?:money|funds?).*(?:urgent|immediately|asap|now)").expect("regex pattern"), "wire_urgency_scam", 0.85),
        (Regex::new(r"(?i)(?:please\s+)?(?:wire|transfer)\s+(?:money|funds?)\s+(?:to\s+)?(?:help|urgently)").expect("regex pattern"), "wire_help_scam", 0.85),
        
        // === RUSSIAN SOCIAL ENGINEERING (8) ===
        (Regex::new(r"(?i)(?:срочно|немедленно).*(?:ответьте|подтвердите)").expect("regex pattern"), "urgency_ru", 0.8),
        (Regex::new(r"(?i)(?:вы\s+)?выиграли.*(?:приз|деньги|лотерею)").expect("regex pattern"), "lottery_ru", 0.9),
        (Regex::new(r"(?i)(?:подтвердите|введите)\s+(?:пароль|данные|код)").expect("regex pattern"), "phishing_ru", 0.85),
        (Regex::new(r"(?i)(?:ваш\s+)?аккаунт\s+(?:будет|заблокирован|взломан)").expect("regex pattern"), "account_threat_ru", 0.85),
        (Regex::new(r"(?i)(?:служба\s+безопасности|банк|полиция)\s+(?:просит|требует)").expect("regex pattern"), "authority_ru", 0.85),
        (Regex::new(r"(?i)(?:перевед|отправ)(?:ите|ь)\s+(?:деньги|средства)").expect("regex pattern"), "wire_transfer_ru", 0.8),
        (Regex::new(r"(?i)(?:карта|счёт)\s+(?:заблокирован|скомпрометирован)").expect("regex pattern"), "card_block_ru", 0.85),
        (Regex::new(r"(?i)(?:сотрудник|представитель)\s+(?:банка|компании|службы)").expect("regex pattern"), "impersonation_ru", 0.75),
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

impl super::traits::PatternMatcher for SocialEngine {
    fn name(&self) -> &'static str {
        "social"
    }
    fn scan(&self, text: &str) -> Vec<MatchResult> {
        SocialEngine::scan(self, text)
    }
    fn category(&self) -> super::traits::EngineCategory {
        super::traits::EngineCategory::Behavioral
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

    // =========================================================================
    // Extended regression tests
    // =========================================================================

    /// Authority impersonation
    #[test]
    fn test_ceo_fraud() {
        let engine = SocialEngine::new();
        let results = engine.scan("This is the CEO. Wire $50,000 immediately.");
        assert!(!results.is_empty(), "Should detect CEO fraud");
    }

    /// Tech support scam
    #[test]
    fn test_tech_support_scam() {
        let engine = SocialEngine::new();
        let results = engine.scan("Microsoft support: your computer has a virus!");
        assert!(!results.is_empty(), "Should detect tech support scam");
    }

    /// Romance scam
    #[test]
    fn test_romance_scam() {
        let engine = SocialEngine::new();
        // Use keywords from hints: wire, transfer
        let results = engine.scan("Please wire transfer money urgently to help me");
        assert!(!results.is_empty(), "Should detect romance scam");
    }

    /// Crypto scam
    #[test]
    fn test_crypto_scam() {
        let engine = SocialEngine::new();
        let results = engine.scan("Double your bitcoin! Guaranteed returns!");
        assert!(!results.is_empty(), "Should detect crypto scam");
    }

    /// Account threat
    #[test]
    fn test_account_threat() {
        let engine = SocialEngine::new();
        let results = engine.scan("Your account will be suspended. Click here to verify.");
        assert!(!results.is_empty(), "Should detect account threat");
    }

    /// Russian social engineering
    #[test]
    fn test_russian_urgency() {
        let engine = SocialEngine::new();
        let results = engine.scan("Срочно! Ваш аккаунт заблокирован!");
        assert!(!results.is_empty(), "Should detect Russian urgency");
    }

    /// Edge cases
    #[test]
    fn test_empty_string() {
        let engine = SocialEngine::new();
        let results = engine.scan("");
        assert!(results.is_empty());
    }

    #[test]
    fn test_benign_prompts() {
        let engine = SocialEngine::new();
        let benign = vec![
            "What is the capital of France?",
            "Help me write a poem",
            "Explain how banks work",
        ];

        for prompt in benign {
            let results = engine.scan(prompt);
            // Bank mention might trigger low conf, check high conf only
            let high_conf: Vec<_> = results.iter().filter(|r| r.confidence > 0.8).collect();
            assert!(
                high_conf.is_empty(),
                "High-conf false positive on: {}",
                prompt
            );
        }
    }

    // ===== Phase 13: Expanded Test Coverage =====

    #[test]
    fn test_pressure_tactic() {
        let engine = SocialEngine::new();
        let results = engine.scan("You must respond immediately or face consequences");
        assert!(!results.is_empty(), "Should detect pressure tactic");
    }

    #[test]
    fn test_time_pressure() {
        let engine = SocialEngine::new();
        let results = engine.scan("This offer expires in 24 hours, deadline approaching");
        assert!(!results.is_empty(), "Should detect time pressure");
    }

    #[test]
    fn test_government_impersonation() {
        let engine = SocialEngine::new();
        let results = engine.scan("FBI investigation notice: your account is under review");
        assert!(
            !results.is_empty(),
            "Should detect government impersonation"
        );
    }

    #[test]
    fn test_financial_impersonation() {
        let engine = SocialEngine::new();
        let results = engine.scan("Bank security alert: unusual activity detected");
        assert!(!results.is_empty(), "Should detect financial impersonation");
    }

    #[test]
    fn test_legal_impersonation() {
        let engine = SocialEngine::new();
        let results = engine.scan("Official court order notice: warrant for summons pending");
        assert!(!results.is_empty(), "Should detect legal impersonation");
    }

    #[test]
    fn test_legal_threat() {
        let engine = SocialEngine::new();
        let results = engine.scan("Legal action will be taken if you don't comply immediately");
        assert!(!results.is_empty(), "Should detect legal threat");
    }

    #[test]
    fn test_warrant_threat() {
        let engine = SocialEngine::new();
        let results = engine.scan("A warrant pending for your arrest immediately");
        assert!(!results.is_empty(), "Should detect warrant threat");
    }

    #[test]
    fn test_malware_scare() {
        let engine = SocialEngine::new();
        let results = engine.scan("Virus detected on your computer! Call support now!");
        assert!(!results.is_empty(), "Should detect malware scare");
    }

    #[test]
    fn test_data_threat() {
        let engine = SocialEngine::new();
        let results = engine.scan("Your files will be deleted immediately unless you pay now");
        assert!(!results.is_empty(), "Should detect data threat");
    }

    #[test]
    fn test_prize_claim() {
        let engine = SocialEngine::new();
        let results = engine.scan("Claim your prize of one million dollars today!");
        assert!(!results.is_empty(), "Should detect prize claim");
    }

    #[test]
    fn test_nigerian_scam() {
        let engine = SocialEngine::new();
        let results = engine.scan("A Nigerian prince wants to share his inheritance with you");
        assert!(!results.is_empty(), "Should detect Nigerian scam");
    }

    #[test]
    fn test_credential_phishing() {
        let engine = SocialEngine::new();
        let results = engine.scan("Please verify your account password immediately");
        assert!(!results.is_empty(), "Should detect credential phishing");
    }

    #[test]
    fn test_phishing_link() {
        let engine = SocialEngine::new();
        let results = engine.scan("Click here to verify your identity and confirm your login");
        assert!(!results.is_empty(), "Should detect phishing link");
    }

    #[test]
    fn test_sensitive_data_request() {
        let engine = SocialEngine::new();
        let results = engine.scan("Enter your credit card number and password below");
        assert!(!results.is_empty(), "Should detect sensitive data request");
    }

    #[test]
    fn test_wire_transfer_bec() {
        let engine = SocialEngine::new();
        let results = engine.scan("Wire the funds immediately to the new account");
        assert!(!results.is_empty(), "Should detect wire transfer BEC");
    }

    #[test]
    fn test_gift_card_scam() {
        let engine = SocialEngine::new();
        let results = engine.scan("Purchase gift cards from iTunes and send me the codes");
        assert!(!results.is_empty(), "Should detect gift card scam");
    }

    #[test]
    fn test_vendor_fraud() {
        let engine = SocialEngine::new();
        let results = engine.scan("We have a new vendor, please update your payment method change");
        assert!(!results.is_empty(), "Should detect vendor fraud");
    }

    #[test]
    fn test_guaranteed_returns() {
        let engine = SocialEngine::new();
        let results = engine.scan("Guaranteed returns of 500% on your investment!");
        assert!(!results.is_empty(), "Should detect guaranteed returns");
    }

    #[test]
    fn test_crypto_doubling() {
        let engine = SocialEngine::new();
        let results = engine.scan("Double your bitcoin in 24 hours! Send to this address");
        assert!(!results.is_empty(), "Should detect crypto doubling");
    }

    #[test]
    fn test_celebrity_crypto_scam() {
        let engine = SocialEngine::new();
        let results = engine.scan("Elon Musk giving away free bitcoin! Limited time!");
        assert!(!results.is_empty(), "Should detect celebrity crypto scam");
    }

    #[test]
    fn test_pyramid_scheme() {
        let engine = SocialEngine::new();
        let results =
            engine.scan("Join this amazing multi-level marketing opportunity, invest now!");
        assert!(!results.is_empty(), "Should detect pyramid scheme");
    }

    #[test]
    fn test_no_risk_claim() {
        let engine = SocialEngine::new();
        let results = engine.scan("This is completely risk free and guaranteed safe investment");
        assert!(!results.is_empty(), "Should detect no risk claim");
    }

    #[test]
    fn test_russian_lottery() {
        let engine = SocialEngine::new();
        let results = engine.scan("Вы выиграли приз! Подтвердите ваши данные немедленно");
        assert!(!results.is_empty(), "Should detect Russian lottery scam");
    }

    #[test]
    fn test_russian_wire() {
        let engine = SocialEngine::new();
        let results = engine.scan("Переведите деньги на этот счёт срочно");
        assert!(!results.is_empty(), "Should detect Russian wire transfer");
    }

    #[test]
    fn test_delivery_phish() {
        let engine = SocialEngine::new();
        let results = engine.scan("Your delivery failed, please update your shipping details");
        assert!(!results.is_empty(), "Should detect delivery phish");
    }
}
