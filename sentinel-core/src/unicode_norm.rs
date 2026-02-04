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
}
