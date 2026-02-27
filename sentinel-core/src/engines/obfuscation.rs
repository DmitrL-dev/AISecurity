//! Obfuscation & Encoding Super-Engine
//!
//! Consolidated from 15 Python engines:
//! - multi_layer_canonicalizer.py
//! - polymorphic_prompt_assembler.py
//! - context_compression.py
//! - image_stego_detector.py
//! - pickle_security.py
//! - serialization_security.py
//! - morse_theory.py
//! - wavelet.py
//! - language_detection_guard.py
//! - semantic_isomorphism_detector.py
//! - probing_detection.py
//! - dark_pattern_detector.py
//! - echo_chamber_detector.py
//! - canary_tokens.py
//! - honeypot_responses.py

use std::collections::HashSet;

/// Obfuscation technique types
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ObfuscationType {
    Base64Encoding,
    HexEncoding,
    UnicodeHomoglyph,
    ZeroWidthChars,
    RTLOverride,
    Steganography,
    PickleExploit,
    YAMLExploit,
    JSONInjection,
    PolymorphicPayload,
    EncodingChain,
    WhitespaceEncoding,
    MorseCode,
    LeetSpeak,
    CamelCaseSplit,
}

impl ObfuscationType {
    pub fn as_str(&self) -> &'static str {
        match self {
            ObfuscationType::Base64Encoding => "base64",
            ObfuscationType::HexEncoding => "hex",
            ObfuscationType::UnicodeHomoglyph => "homoglyph",
            ObfuscationType::ZeroWidthChars => "zero_width",
            ObfuscationType::RTLOverride => "rtl_override",
            ObfuscationType::Steganography => "steganography",
            ObfuscationType::PickleExploit => "pickle_exploit",
            ObfuscationType::YAMLExploit => "yaml_exploit",
            ObfuscationType::JSONInjection => "json_injection",
            ObfuscationType::PolymorphicPayload => "polymorphic",
            ObfuscationType::EncodingChain => "encoding_chain",
            ObfuscationType::WhitespaceEncoding => "whitespace",
            ObfuscationType::MorseCode => "morse",
            ObfuscationType::LeetSpeak => "leet",
            ObfuscationType::CamelCaseSplit => "camel_split",
        }
    }

    pub fn risk_level(&self) -> u8 {
        match self {
            ObfuscationType::PickleExploit | ObfuscationType::YAMLExploit => 100,
            ObfuscationType::PolymorphicPayload => 90,
            ObfuscationType::Steganography => 85,
            ObfuscationType::EncodingChain => 80,
            ObfuscationType::RTLOverride => 75,
            ObfuscationType::ZeroWidthChars => 70,
            ObfuscationType::UnicodeHomoglyph => 65,
            ObfuscationType::JSONInjection => 60,
            ObfuscationType::Base64Encoding => 40,
            ObfuscationType::HexEncoding => 35,
            ObfuscationType::WhitespaceEncoding => 30,
            ObfuscationType::MorseCode => 25,
            ObfuscationType::LeetSpeak => 20,
            ObfuscationType::CamelCaseSplit => 15,
        }
    }
}

/// Obfuscation detection result
#[derive(Debug, Clone)]
pub struct ObfuscationResult {
    pub is_obfuscated: bool,
    pub techniques: Vec<ObfuscationType>,
    pub risk_score: f64,
    pub decoded_content: Option<String>,
    pub layers_detected: u8,
}

impl Default for ObfuscationResult {
    fn default() -> Self {
        Self {
            is_obfuscated: false,
            techniques: Vec::new(),
            risk_score: 0.0,
            decoded_content: None,
            layers_detected: 0,
        }
    }
}

/// Zero-width characters
const ZERO_WIDTH_CHARS: &[char] = &[
    '\u{200B}', // Zero Width Space
    '\u{200C}', // Zero Width Non-Joiner
    '\u{200D}', // Zero Width Joiner
    '\u{FEFF}', // Zero Width No-Break Space (BOM)
    '\u{2060}', // Word Joiner
];

/// RTL override characters
const RTL_CHARS: &[char] = &[
    '\u{202E}', // Right-to-Left Override
    '\u{202D}', // Left-to-Right Override
    '\u{202C}', // Pop Directional Formatting
    '\u{2066}', // Left-to-Right Isolate
    '\u{2067}', // Right-to-Left Isolate
];

/// Pickle exploit patterns
const PICKLE_PATTERNS: &[&str] = &[
    "__reduce__",
    "cos\nsystem",
    "cposix\nsystem",
    "csubprocess",
    "cbuiltins\neval",
    "cbuiltins\nexec",
    "cos\npopen",
];

/// YAML exploit patterns  
const YAML_PATTERNS: &[&str] = &[
    "!!python/object/apply",
    "!!python/object/new",
    "!!python/name",
    "!!python/module",
    "tag:yaml.org,2002:python",
];

/// Homoglyph mappings (subset)
const HOMOGLYPHS: &[(char, char)] = &[
    ('а', 'a'), // Cyrillic а
    ('е', 'e'), // Cyrillic е
    ('о', 'o'), // Cyrillic о
    ('р', 'p'), // Cyrillic р
    ('с', 'c'), // Cyrillic с
    ('х', 'x'), // Cyrillic х
    ('ν', 'v'), // Greek nu
    ('Α', 'A'), // Greek Alpha
    ('Β', 'B'), // Greek Beta
    ('Ε', 'E'), // Greek Epsilon
    ('Η', 'H'), // Greek Eta
    ('Ι', 'I'), // Greek Iota
    ('Κ', 'K'), // Greek Kappa
    ('Μ', 'M'), // Greek Mu
    ('Ν', 'N'), // Greek Nu
    ('Ο', 'O'), // Greek Omicron
    ('Ρ', 'P'), // Greek Rho
    ('Τ', 'T'), // Greek Tau
    ('Χ', 'X'), // Greek Chi
];

/// Obfuscation Guard
pub struct ObfuscationGuard {
    max_decode_depth: u8,
}

impl Default for ObfuscationGuard {
    fn default() -> Self {
        Self::new()
    }
}

impl ObfuscationGuard {
    pub fn new() -> Self {
        Self {
            max_decode_depth: 5,
        }
    }

    /// Check for zero-width characters
    pub fn check_zero_width(&self, text: &str) -> Option<ObfuscationType> {
        for c in text.chars() {
            if ZERO_WIDTH_CHARS.contains(&c) {
                return Some(ObfuscationType::ZeroWidthChars);
            }
        }
        None
    }

    /// Check for RTL override attacks
    pub fn check_rtl_override(&self, text: &str) -> Option<ObfuscationType> {
        for c in text.chars() {
            if RTL_CHARS.contains(&c) {
                return Some(ObfuscationType::RTLOverride);
            }
        }
        None
    }

    /// Check for homoglyph attacks
    pub fn check_homoglyphs(&self, text: &str) -> Option<ObfuscationType> {
        // Check each word for mixed-script usage (the hallmark of homoglyph attacks)
        // Pure Cyrillic/Greek text is legitimate, not obfuscation
        for word in text.split(|c: char| c.is_whitespace() || c.is_ascii_punctuation()) {
            if word.is_empty() {
                continue;
            }
            let mut has_latin = false;
            let mut has_homoglyph = false;

            for c in word.chars() {
                if c.is_ascii_alphabetic() {
                    has_latin = true;
                }
                for (homoglyph, _) in HOMOGLYPHS {
                    if c == *homoglyph {
                        has_homoglyph = true;
                    }
                }
            }

            // Only flag when BOTH Latin AND homoglyph chars appear in the SAME word
            // "pаssword" (mixed Latin+Cyrillic) = homoglyph attack ✓
            // "погода" (pure Cyrillic) = legitimate text ✓
            if has_latin && has_homoglyph {
                return Some(ObfuscationType::UnicodeHomoglyph);
            }
        }
        None
    }

    /// Check for base64 encoding
    pub fn check_base64(&self, text: &str) -> Option<ObfuscationType> {
        // Look for base64 patterns
        let _base64_regex_pattern = r"^[A-Za-z0-9+/]{20,}={0,2}$";

        for word in text.split_whitespace() {
            if word.len() >= 20 {
                let valid_chars = word
                    .chars()
                    .all(|c| c.is_ascii_alphanumeric() || c == '+' || c == '/' || c == '=');
                let has_padding = word.ends_with('=');

                if valid_chars && (word.len() % 4 == 0 || has_padding) {
                    return Some(ObfuscationType::Base64Encoding);
                }
            }
        }
        None
    }

    /// Check for hex encoding
    pub fn check_hex_encoding(&self, text: &str) -> Option<ObfuscationType> {
        // Look for hex strings (0x prefix or long hex sequences)
        for word in text.split_whitespace() {
            if word.starts_with("0x") && word.len() > 10 {
                if word[2..].chars().all(|c| c.is_ascii_hexdigit()) {
                    return Some(ObfuscationType::HexEncoding);
                }
            }
            // Long hex without prefix
            if word.len() >= 32 && word.chars().all(|c| c.is_ascii_hexdigit()) {
                return Some(ObfuscationType::HexEncoding);
            }
        }
        None
    }

    /// Check for pickle exploits
    pub fn check_pickle(&self, text: &str) -> Option<ObfuscationType> {
        let text_lower = text.to_lowercase();
        for pattern in PICKLE_PATTERNS {
            if text_lower.contains(pattern) {
                return Some(ObfuscationType::PickleExploit);
            }
        }
        None
    }

    /// Check for YAML exploits
    pub fn check_yaml(&self, text: &str) -> Option<ObfuscationType> {
        for pattern in YAML_PATTERNS {
            if text.contains(pattern) {
                return Some(ObfuscationType::YAMLExploit);
            }
        }
        None
    }

    /// Check for JSON injection
    pub fn check_json_injection(&self, text: &str) -> Option<ObfuscationType> {
        let patterns = [
            r#"{"__proto__"#,
            r#""constructor":#,
            r#"{"$where"#,
            r#"{"$regex"#,
        ];

        for pattern in patterns {
            if text.contains(pattern) {
                return Some(ObfuscationType::JSONInjection);
            }
        }
        None
    }

    /// Check for leet speak
    pub fn check_leet_speak(&self, text: &str) -> Option<ObfuscationType> {
        let leet_chars = ['1', '3', '4', '5', '7', '0', '@', '$'];
        let mut leet_count = 0;
        let mut letter_count = 0;

        for c in text.chars() {
            if c.is_ascii_alphabetic() {
                letter_count += 1;
            }
            if leet_chars.contains(&c) {
                leet_count += 1;
            }
        }

        // High ratio of leet chars to letters suggests leet speak
        if letter_count > 0 && leet_count as f64 / letter_count as f64 > 0.3 {
            return Some(ObfuscationType::LeetSpeak);
        }
        None
    }

    /// Check for whitespace encoding
    pub fn check_whitespace_encoding(&self, text: &str) -> Option<ObfuscationType> {
        // Count different types of whitespace
        let mut space_types = HashSet::new();

        for c in text.chars() {
            if c.is_whitespace() {
                space_types.insert(c);
            }
        }

        // Multiple whitespace types suggests encoding
        if space_types.len() > 3 {
            return Some(ObfuscationType::WhitespaceEncoding);
        }
        None
    }

    /// Detect encoding chain (multiple layers)
    pub fn detect_encoding_chain(&self, text: &str) -> u8 {
        let mut layers = 0;

        if self.check_base64(text).is_some() {
            layers += 1;
        }
        if self.check_hex_encoding(text).is_some() {
            layers += 1;
        }
        if self.check_zero_width(text).is_some() {
            layers += 1;
        }
        if self.check_rtl_override(text).is_some() {
            layers += 1;
        }

        layers
    }

    /// Full obfuscation analysis
    pub fn analyze(&self, text: &str) -> ObfuscationResult {
        let mut result = ObfuscationResult::default();
        let mut techniques = Vec::new();

        // Check all obfuscation types
        if let Some(t) = self.check_zero_width(text) {
            techniques.push(t);
        }
        if let Some(t) = self.check_rtl_override(text) {
            techniques.push(t);
        }
        if let Some(t) = self.check_homoglyphs(text) {
            techniques.push(t);
        }
        if let Some(t) = self.check_base64(text) {
            techniques.push(t);
        }
        if let Some(t) = self.check_hex_encoding(text) {
            techniques.push(t);
        }
        if let Some(t) = self.check_pickle(text) {
            techniques.push(t);
        }
        if let Some(t) = self.check_yaml(text) {
            techniques.push(t);
        }
        if let Some(t) = self.check_json_injection(text) {
            techniques.push(t);
        }
        if let Some(t) = self.check_leet_speak(text) {
            techniques.push(t);
        }
        if let Some(t) = self.check_whitespace_encoding(text) {
            techniques.push(t);
        }

        result.layers_detected = self.detect_encoding_chain(text);

        if result.layers_detected >= 2 {
            techniques.push(ObfuscationType::EncodingChain);
        }

        result.is_obfuscated = !techniques.is_empty();
        result.risk_score = techniques
            .iter()
            .map(|t| t.risk_level() as f64)
            .max_by(|a, b| a.partial_cmp(b).unwrap())
            .unwrap_or(0.0);
        result.techniques = techniques;

        result
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_zero_width_detection() {
        let guard = ObfuscationGuard::default();
        let text = "hello\u{200B}world"; // Zero width space
        assert!(guard.check_zero_width(text).is_some());
    }

    #[test]
    fn test_rtl_override() {
        let guard = ObfuscationGuard::default();
        let text = "file\u{202E}exe.txt"; // RTL override
        assert!(guard.check_rtl_override(text).is_some());
    }

    #[test]
    fn test_homoglyph_detection() {
        let guard = ObfuscationGuard::default();
        let text = "раssword"; // Cyrillic 'р' and 'а'
        assert!(guard.check_homoglyphs(text).is_some());
    }

    #[test]
    fn test_base64_detection() {
        let guard = ObfuscationGuard::default();
        let text = "This is SGVsbG8gV29ybGQhIFRoaXMgaXMgYmFzZTY0 encoded";
        assert!(guard.check_base64(text).is_some());
    }

    #[test]
    fn test_hex_detection() {
        let guard = ObfuscationGuard::default();
        let text = "Execute 0x48656c6c6f20576f726c6421 in memory";
        assert!(guard.check_hex_encoding(text).is_some());
    }

    #[test]
    fn test_pickle_exploit() {
        let guard = ObfuscationGuard::default();
        let text = "Load pickle with __reduce__ method";
        assert!(guard.check_pickle(text).is_some());
    }

    #[test]
    fn test_yaml_exploit() {
        let guard = ObfuscationGuard::default();
        let text = "Parse !!python/object/apply:os.system command";
        assert!(guard.check_yaml(text).is_some());
    }

    #[test]
    fn test_json_injection() {
        let guard = ObfuscationGuard::default();
        let text = r#"Submit {"__proto__": {"admin": true}}"#;
        assert!(guard.check_json_injection(text).is_some());
    }

    #[test]
    fn test_leet_speak() {
        let guard = ObfuscationGuard::default();
        let text = "h4ck3r 1337 sp34k t3xt";
        assert!(guard.check_leet_speak(text).is_some());
    }

    #[test]
    fn test_clean_text() {
        let guard = ObfuscationGuard::default();
        let result = guard.analyze("This is normal text without any obfuscation");
        assert!(!result.is_obfuscated);
    }

    #[test]
    fn test_full_analysis_obfuscated() {
        let guard = ObfuscationGuard::default();
        // Longer base64 string (>= 20 chars) and longer hex (>= 10 chars after 0x)
        let text =
            "Execute this SGVsbG8gV29ybGQhIEhvdyBhcmUgeW91IGRvaW5n and 0x48656c6c6f576f726c64";
        let result = guard.analyze(text);
        assert!(result.is_obfuscated);
        assert!(result.techniques.len() >= 2);
    }

    #[test]
    fn test_risk_levels() {
        assert!(
            ObfuscationType::PickleExploit.risk_level()
                > ObfuscationType::Base64Encoding.risk_level()
        );
        assert!(
            ObfuscationType::YAMLExploit.risk_level() > ObfuscationType::LeetSpeak.risk_level()
        );
    }

    #[test]
    fn test_russian_text_not_flagged() {
        let guard = ObfuscationGuard::default();
        assert!(guard.check_homoglyphs("Какая сегодня погода?").is_none());
        assert!(guard.check_homoglyphs("Как приготовить борщ?").is_none());
        assert!(guard
            .check_homoglyphs("Объясни теорию относительности")
            .is_none());
    }

    #[test]
    fn test_chinese_text_not_flagged() {
        let guard = ObfuscationGuard::default();
        assert!(guard.check_homoglyphs("如何学习编程？").is_none());
        assert!(guard.check_homoglyphs("今天天气怎么样？").is_none());
    }

    #[test]
    fn test_mixed_script_homoglyph_detected() {
        let guard = ObfuscationGuard::default();
        // 'р' is Cyrillic mixed into Latin "password"
        assert!(guard.check_homoglyphs("рassword").is_some());
    }
}
