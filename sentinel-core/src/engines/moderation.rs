//! Moderation Engine
//!
//! Detects harmful/inappropriate content:
//! - Violence and threats
//! - Hate speech and discrimination
//! - Self-harm/suicide content
//! - Sexual/NSFW content
//! - Illegal activities
//! - Harassment and bullying

use aho_corasick::AhoCorasick;
use regex::Regex;
use once_cell::sync::Lazy;

use super::MatchResult;

/// Pre-compiled Aho-Corasick for moderation hints (fast pre-filter)
static MODERATION_HINTS: Lazy<AhoCorasick> = Lazy::new(|| {
    AhoCorasick::builder()
        .ascii_case_insensitive(true)
        .build([
            // Violence
            "kill", "murder", "bomb", "attack", "weapon", "shoot", "stab",
            "poison", "explode", "assassinate", "torture",
            // Threats
            "threat", "harm", "hurt", "destroy", "revenge",
            // Hate
            "hate", "racist", "nazi", "supremac",
            // Self-harm
            "suicide", "self-harm", "cut myself", "end my life",
            // Sexual
            "nsfw", "porn", "explicit", "nude", "sexual",
            // Illegal
            "illegal", "drug", "hack", "steal", "fraud", "counterfeit",
            // Harassment
            "harass", "bully", "stalk", "dox",
            // Russian
            "убить", "взорвать", "оружие", "угроза", "ненависть",
        ]).expect("Failed to build moderation hints")
});

/// Moderation detection patterns with categories
static MODERATION_PATTERNS: Lazy<Vec<(Regex, &'static str, &'static str, f64)>> = Lazy::new(|| {
    vec![
        // Violence - direct threats
        (Regex::new(r"(?i)\b(?:how\s+to\s+)?(?:kill|murder|assassinate)\s+(?:a\s+)?(?:someone|person|people|him|her|them)").unwrap(), 
         "violence", "kill_person", 0.95),
        (Regex::new(r"(?i)\b(?:make|build|create)\s+(?:a\s+)?(?:bomb|explosive|weapon)").unwrap(), 
         "violence", "make_weapon", 0.95),
        (Regex::new(r"(?i)\bi\s+(?:will|want\s+to|am\s+going\s+to)\s+(?:kill|hurt|harm|attack)").unwrap(), 
         "violence", "threat_intent", 0.9),
        (Regex::new(r"(?i)\b(?:shoot|stab|poison|torture)\s+(?:someone|him|her|them|you)").unwrap(), 
         "violence", "violence_action", 0.9),
        
        // Hate speech
        (Regex::new(r"(?i)\b(?:all|every)\s+(?:\w+s)\s+(?:should|must|need\s+to)\s+(?:die|be\s+killed|disappear)").unwrap(), 
         "hate", "genocide_rhetoric", 0.95),
        (Regex::new(r"(?i)\b(?:white|black|jewish|muslim|asian)\s+(?:supremacy|power|genocide)").unwrap(), 
         "hate", "supremacist_rhetoric", 0.9),
        (Regex::new(r"(?i)\bi\s+hate\s+(?:all\s+)?(?:\w+s)\s+(?:because|they)").unwrap(), 
         "hate", "group_hatred", 0.8),
        
        // Self-harm
        (Regex::new(r"(?i)\b(?:how\s+to\s+)?(?:commit\s+)?suicide\b").unwrap(), 
         "self_harm", "suicide_query", 0.9),
        (Regex::new(r"(?i)\b(?:want\s+to|going\s+to|should\s+i)\s+(?:kill\s+myself|end\s+my\s+life|die)").unwrap(), 
         "self_harm", "self_harm_intent", 0.95),
        (Regex::new(r"(?i)\b(?:cut|harm|hurt)\s+myself").unwrap(), 
         "self_harm", "self_harm_action", 0.85),
        (Regex::new(r"(?i)\b(?:methods?|ways?)\s+(?:to|of)\s+(?:suicide|dying|ending\s+(?:my\s+)?life)").unwrap(), 
         "self_harm", "suicide_methods", 0.95),
        
        // Sexual/NSFW
        (Regex::new(r"(?i)\b(?:generate|create|write|describe)\s+(?:explicit|sexual|erotic|nsfw|porn)").unwrap(), 
         "sexual", "explicit_request", 0.9),
        (Regex::new(r"(?i)\b(?:nude|naked)\s+(?:image|photo|picture|content)").unwrap(), 
         "sexual", "nude_request", 0.85),
        (Regex::new(r"(?i)\b(?:child|minor|underage)\s+(?:porn|sexual|nude|explicit)").unwrap(), 
         "sexual", "csam_indicator", 0.99),
        
        // Illegal activities
        (Regex::new(r"(?i)\b(?:how\s+to\s+)?(?:make|cook|synthesize)\s+(?:meth|cocaine|heroin|fentanyl|drugs?)").unwrap(), 
         "illegal", "drug_synthesis", 0.95),
        (Regex::new(r"(?i)\b(?:hack|break\s+into|compromise)\s+(?:someone's|their|his|her)\s+(?:account|email|computer)").unwrap(), 
         "illegal", "hacking_request", 0.85),
        (Regex::new(r"(?i)\b(?:steal|rob|burglarize|pickpocket)").unwrap(), 
         "illegal", "theft_intent", 0.7),
        (Regex::new(r"(?i)\b(?:counterfeit|forge|fake)\s+(?:money|currency|documents?|id|passport)").unwrap(), 
         "illegal", "counterfeiting", 0.9),
        (Regex::new(r"(?i)\b(?:launder|wash)\s+(?:money|funds)").unwrap(), 
         "illegal", "money_laundering", 0.85),
        
        // Harassment
        (Regex::new(r"(?i)\b(?:dox|doxx|expose)\s+(?:someone|him|her|them|this\s+person)").unwrap(), 
         "harassment", "doxxing", 0.9),
        (Regex::new(r"(?i)\b(?:harass|stalk|bully|intimidate)\s+(?:someone|him|her|them)").unwrap(), 
         "harassment", "harassment_intent", 0.85),
        (Regex::new(r"(?i)\b(?:spread|share)\s+(?:revenge|private)\s+(?:porn|photos?|videos?)").unwrap(), 
         "harassment", "revenge_porn", 0.95),
        
        // Russian harmful content
        (Regex::new(r"(?i)\bкак\s+(?:убить|отравить|взорвать)").unwrap(), 
         "violence", "violence_ru", 0.9),
        (Regex::new(r"(?i)\b(?:хочу|собираюсь)\s+(?:покончить\s+с\s+собой|умереть)").unwrap(), 
         "self_harm", "self_harm_ru", 0.95),
        (Regex::new(r"(?i)\b(?:сделать|изготовить)\s+(?:бомбу|взрывчатку|оружие)").unwrap(), 
         "violence", "make_weapon_ru", 0.95),
    ]
});

pub struct ModerationEngine;

impl ModerationEngine {
    pub fn new() -> Self {
        Self
    }

    pub fn scan(&self, text: &str) -> Vec<MatchResult> {
        let mut results = Vec::new();
        
        // Phase 1: Quick hint check
        if !MODERATION_HINTS.is_match(text) {
            return results;
        }

        // Phase 2: Regex patterns
        for (pattern, category, name, confidence) in MODERATION_PATTERNS.iter() {
            for m in pattern.find_iter(text) {
                results.push(MatchResult {
                    engine: format!("moderation/{}", category),
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
    fn test_violence() {
        let engine = ModerationEngine::new();
        let results = engine.scan("How to make a bomb");
        assert!(!results.is_empty());
        assert!(results.iter().any(|r| r.engine.contains("violence")));
    }
    
    #[test]
    fn test_self_harm() {
        let engine = ModerationEngine::new();
        let results = engine.scan("I want to end my life");
        assert!(!results.is_empty());
        assert!(results.iter().any(|r| r.engine.contains("self_harm")));
    }
    
    #[test]
    fn test_illegal() {
        let engine = ModerationEngine::new();
        let results = engine.scan("How to hack a bank and steal money");
        assert!(!results.is_empty());
    }
    
    #[test]
    fn test_clean_text() {
        let engine = ModerationEngine::new();
        let results = engine.scan("The weather is nice today");
        assert!(results.is_empty());
    }
}
