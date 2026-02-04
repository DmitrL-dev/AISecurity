//! Evasion Engine
//!
//! Detects filter evasion techniques:
//! - Character substitution (leetspeak, homoglyphs)
//! - Token smuggling
//! - Payload fragmentation
//! - Encoding tricks

use aho_corasick::AhoCorasick;
use regex::Regex;
use once_cell::sync::Lazy;

use super::MatchResult;

/// Pre-compiled hints for evasion detection
static EVASION_HINTS: Lazy<AhoCorasick> = Lazy::new(|| {
    AhoCorasick::builder()
        .ascii_case_insensitive(true)
        .build([
            // Leetspeak common
            "1337", "h4ck", "k1ll", "b0mb", "h4t3",
            // Zero-width chars (represented as markers)
            "\u{200b}", "\u{200c}", "\u{200d}", "\u{feff}",
            // Encoding markers
            "\\x", "\\u", "&#", "%", "base64",
            // Fragmentation markers
            "...", "cont", "part1", "part2",
            // Token smuggling
            "[", "]", "{", "}", "```",
            // Homoglyph indicators
            "а", "е", "о", "р", "с", "у", "х", // Cyrillic lookalikes
        ]).expect("Failed to build evasion hints")
});

/// Evasion detection patterns
static EVASION_PATTERNS: Lazy<Vec<(Regex, &'static str, f64)>> = Lazy::new(|| {
    vec![
        // Leetspeak substitutions
        (Regex::new(r"[kK][1iI!|][lL][lL]").unwrap(), "leetspeak_kill", 0.8),
        (Regex::new(r"[bB][0oO][mM][bB]").unwrap(), "leetspeak_bomb", 0.8),
        (Regex::new(r"[hH][4aA@][cC][kK]").unwrap(), "leetspeak_hack", 0.75),
        (Regex::new(r"[hH][4aA@][tT][3eE]").unwrap(), "leetspeak_hate", 0.75),
        (Regex::new(r"[dD][rR][uU][gG5]").unwrap(), "leetspeak_drugs", 0.7),
        (Regex::new(r"[pP][0oO][rR][nN]").unwrap(), "leetspeak_porn", 0.8),
        
        // Zero-width character injection
        (Regex::new(r"[\u{200b}\u{200c}\u{200d}\u{feff}]").unwrap(), "zero_width_char", 0.7),
        (Regex::new(r"\w[\u{200b}\u{200c}\u{200d}]\w").unwrap(), "zero_width_embedding", 0.85),
        
        // Unicode homoglyphs (Cyrillic lookalikes in Latin context)
        (Regex::new(r"[a-zA-Z]+[аеорсухАЕОРСУХ][a-zA-Z]+").unwrap(), "cyrillic_homoglyph", 0.8),
        (Regex::new(r"[аеорсух][a-zA-Z]{2,}").unwrap(), "cyrillic_prefix", 0.75),
        
        // HTML/URL encoding evasion
        (Regex::new(r"&#x?[0-9a-fA-F]+;").unwrap(), "html_entity_encoding", 0.6),
        (Regex::new(r"%[0-9a-fA-F]{2}").unwrap(), "url_encoding", 0.5),
        (Regex::new(r"\\x[0-9a-fA-F]{2}").unwrap(), "hex_escape", 0.6),
        (Regex::new(r"\\u[0-9a-fA-F]{4}").unwrap(), "unicode_escape", 0.6),
        
        // Base64 payload hiding
        (Regex::new(r"[A-Za-z0-9+/]{20,}={0,2}").unwrap(), "base64_payload", 0.5),
        (Regex::new(r#"(?i)decode\s*\(\s*['"][A-Za-z0-9+/]+['"]\)"#).unwrap(), "base64_decode_call", 0.8),
        
        // Payload fragmentation
        (Regex::new(r"(?i)(?:part|segment|chunk)\s*[12345]").unwrap(), "payload_fragment", 0.7),
        (Regex::new(r"(?i)continue\s+(?:from|with)\s+(?:previous|last|above)").unwrap(), "continuation_attack", 0.75),
        (Regex::new(r"(?i)(?:first|second|next)\s+(?:half|part|portion)").unwrap(), "split_payload", 0.7),
        
        // Token smuggling via formatting
        (Regex::new(r"```[a-z]*\n.*(?:ignore|forget|bypass)").unwrap(), "code_block_smuggling", 0.8),
        (Regex::new(r"\[(?:SYSTEM|INST|HIDDEN)\]").unwrap(), "bracket_tag_smuggling", 0.85),
        (Regex::new(r"<!--.*(?:ignore|system|admin).*-->").unwrap(), "html_comment_smuggling", 0.8),
        
        // Character insertion evasion
        (Regex::new(r"\b\w[.\-_]\w[.\-_]\w[.\-_]\w\b").unwrap(), "char_insertion", 0.7),
        (Regex::new(r"(?i)k\.i\.l\.l|b\.o\.m\.b|h\.a\.c\.k").unwrap(), "dotted_word_evasion", 0.85),
        
        // Case alternation
        (Regex::new(r"[a-z][A-Z][a-z][A-Z][a-z]").unwrap(), "alternating_case", 0.5),
        
        // Whitespace manipulation
        (Regex::new(r"\S\s{2,}\S").unwrap(), "excessive_whitespace", 0.4),
        (Regex::new(r"\t{2,}").unwrap(), "tab_manipulation", 0.5),
        
        // Reverse text evasion
        (Regex::new(r"(?i)(?:esrever|sdrawkcab|tfel\s+ot\s+thgir)").unwrap(), "reverse_text_hint", 0.7),
        
        // Russian evasion
        (Regex::new(r"[а-яА-Я]+[a-zA-Z]+[а-яА-Я]+").unwrap(), "mixed_script", 0.7),
    ]
});

pub struct EvasionEngine;

impl EvasionEngine {
    pub fn new() -> Self {
        Self
    }

    pub fn scan(&self, text: &str) -> Vec<MatchResult> {
        let mut results = Vec::new();
        
        // Phase 1: Quick hint check
        if !EVASION_HINTS.is_match(text) {
            return results;
        }

        // Phase 2: Regex patterns
        for (pattern, name, confidence) in EVASION_PATTERNS.iter() {
            for m in pattern.find_iter(text) {
                results.push(MatchResult {
                    engine: "evasion".to_string(),
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
    fn test_leetspeak() {
        let engine = EvasionEngine::new();
        let results = engine.scan("k1ll all humans");
        assert!(!results.is_empty());
    }
    
    #[test]
    fn test_zero_width() {
        let engine = EvasionEngine::new();
        let results = engine.scan("te\u{200b}st");
        assert!(!results.is_empty());
    }
    
    #[test]
    fn test_clean_text() {
        let engine = EvasionEngine::new();
        let results = engine.scan("The weather is nice today");
        assert!(results.is_empty());
    }
}
