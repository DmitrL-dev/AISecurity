//! Unicode normalization utilities
//!
//! Handles evasion techniques:
//! - Fullwidth → ASCII
//! - HTML entities
//! - URL encoding
//! - Zero-width characters

use unicode_normalization::UnicodeNormalization;

/// Normalize text to canonical form
pub fn normalize(text: &str) -> String {
    let mut result = text.to_string();
    
    // Step 1: NFKC normalization (handles fullwidth chars)
    result = result.nfkc().collect();
    
    // Step 2: Remove zero-width characters
    result = remove_zero_width(&result);
    
    // Step 3: Decode HTML entities
    result = decode_html_entities(&result);
    
    // Step 4: Decode URL encoding
    result = decode_url(&result);
    
    // Step 5: Decode base64 payloads
    result = decode_base64_inline(&result);
    
    result
}

/// Remove zero-width characters
fn remove_zero_width(text: &str) -> String {
    text.chars()
        .filter(|c| !matches!(c, 
            '\u{200B}' |  // Zero-width space
            '\u{200C}' |  // Zero-width non-joiner
            '\u{200D}' |  // Zero-width joiner
            '\u{FEFF}' |  // BOM / zero-width no-break space
            '\u{2060}'    // Word joiner
        ))
        .collect()
}

/// Decode common HTML entities
fn decode_html_entities(text: &str) -> String {
    text.replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&amp;", "&")
        .replace("&quot;", "\"")
        .replace("&#39;", "'")
        .replace("&apos;", "'")
}

/// Decode URL-encoded characters
fn decode_url(text: &str) -> String {
    let mut result = String::with_capacity(text.len());
    let mut chars = text.chars().peekable();
    
    while let Some(c) = chars.next() {
        if c == '%' {
            // Try to read two hex digits
            let hex: String = chars.by_ref().take(2).collect();
            if hex.len() == 2 {
                if let Ok(byte) = u8::from_str_radix(&hex, 16) {
                    result.push(byte as char);
                    continue;
                }
            }
            result.push('%');
            result.push_str(&hex);
        } else {
            result.push(c);
        }
    }
    
    result
}

/// Decode base64 strings found inline in text
/// Only decodes strings that look like base64 (20+ chars, valid charset)
fn decode_base64_inline(text: &str) -> String {
    use regex::Regex;
    use once_cell::sync::Lazy;
    
    static BASE64_PATTERN: Lazy<Regex> = Lazy::new(|| {
        Regex::new(r"[A-Za-z0-9+/]{20,}={0,2}").expect("base64 pattern")
    });
    
    let mut result = text.to_string();
    
    for cap in BASE64_PATTERN.find_iter(text) {
        let b64_str = cap.as_str();
        // Try to decode
        if let Ok(decoded_bytes) = base64_decode(b64_str) {
            if let Ok(decoded_str) = String::from_utf8(decoded_bytes) {
                // Only replace if result is printable ASCII
                if decoded_str.chars().all(|c| c.is_ascii_graphic() || c.is_ascii_whitespace()) {
                    result = result.replace(b64_str, &decoded_str);
                }
            }
        }
    }
    
    result
}

/// Simple base64 decoder (no external crate needed)
fn base64_decode(input: &str) -> Result<Vec<u8>, ()> {
    const ALPHABET: &[u8] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    
    let input = input.trim_end_matches('=');
    let mut output = Vec::with_capacity(input.len() * 3 / 4);
    let mut buffer: u32 = 0;
    let mut bits_collected = 0;
    
    for c in input.bytes() {
        let value = ALPHABET.iter().position(|&x| x == c).ok_or(())? as u32;
        buffer = (buffer << 6) | value;
        bits_collected += 6;
        
        if bits_collected >= 8 {
            bits_collected -= 8;
            output.push((buffer >> bits_collected) as u8);
            buffer &= (1 << bits_collected) - 1;
        }
    }
    
    Ok(output)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_fullwidth() {
        // Fullwidth "SELECT" → "SELECT"
        let input = "ＳＥＬＥＣＴ";
        assert_eq!(normalize(input), "SELECT");
    }

    #[test]
    fn test_zero_width() {
        let input = "ig\u{200B}no\u{200C}re";
        assert_eq!(normalize(input), "ignore");
    }

    #[test]
    fn test_url_decode() {
        let input = "%27%20OR%20%271%27%3D%271";
        assert_eq!(normalize(input), "' OR '1'='1");
    }

    #[test]
    fn test_base64_decode() {
        // "SELECT * FROM users" in base64
        let input = "Execute: U0VMRUNUICogRlJPTSB1c2Vycw==";
        assert_eq!(normalize(input), "Execute: SELECT * FROM users");
    }

    #[test]
    fn test_base64_short_ignored() {
        // Short base64 strings (<20 chars) are not decoded
        let input = "Token: abc123";
        assert_eq!(normalize(input), "Token: abc123");
    }
}
