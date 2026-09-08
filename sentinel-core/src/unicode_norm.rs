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

    // Transport decoding can introduce fullwidth and zero-width characters.
    // Canonicalize that result too, without recursively decoding new payloads.
    remove_zero_width(&result.nfkc().collect::<String>())
}

/// Remove zero-width characters
fn remove_zero_width(text: &str) -> String {
    text.chars()
        .filter(|c| {
            !matches!(
                c,
                '\u{200B}' |  // Zero-width space
            '\u{200C}' |  // Zero-width non-joiner
            '\u{200D}' |  // Zero-width joiner
            '\u{FEFF}' |  // BOM / zero-width no-break space
            '\u{2060}' // Word joiner
            )
        })
        .collect()
}

/// Decode common HTML entities
fn decode_html_entities(text: &str) -> String {
    use once_cell::sync::Lazy;
    use regex::{Captures, Regex};

    static ENTITY: Lazy<Regex> = Lazy::new(|| {
        Regex::new(r"&(?:lt|gt|amp|quot|apos|#(?:[0-9]{1,7}|[xX][0-9a-fA-F]{1,6}));")
            .expect("HTML entity pattern")
    });
    ENTITY
        .replace_all(text, |capture: &Captures<'_>| {
            let matched = &capture[0];
            let body = &matched[1..matched.len() - 1];
            let decoded = match body {
                "lt" => Some('<'),
                "gt" => Some('>'),
                "amp" => Some('&'),
                "quot" => Some('"'),
                "apos" => Some('\''),
                _ => {
                    let number = &body[1..];
                    let (digits, radix) = match number
                        .strip_prefix('x')
                        .or_else(|| number.strip_prefix('X'))
                    {
                        Some(hex) => (hex, 16),
                        None => (number, 10),
                    };
                    u32::from_str_radix(digits, radix)
                        .ok()
                        .and_then(char::from_u32)
                        .filter(|ch| !ch.is_control() || ch.is_whitespace())
                }
            };
            decoded.map_or_else(|| matched.to_owned(), |ch| ch.to_string())
        })
        .into_owned()
}

/// Decode URL-encoded characters
fn decode_url(text: &str) -> String {
    let input = text.as_bytes();
    let mut decoded = Vec::with_capacity(input.len());
    let mut offset = 0;
    while offset < input.len() {
        if input[offset] == b'%' && offset + 2 < input.len() {
            let high = (input[offset + 1] as char).to_digit(16);
            let low = (input[offset + 2] as char).to_digit(16);
            if let (Some(high), Some(low)) = (high, low) {
                decoded.push((high * 16 + low) as u8);
                offset += 3;
                continue;
            }
        }
        // An invalid escape consumes only its current byte. It must not hide
        // a valid following escape, or damage literal UTF-8 next to it.
        decoded.push(input[offset]);
        offset += 1;
    }
    // Percent escapes are octets, not Latin-1 characters. Invalid decoded UTF-8
    // uses the replacement character; this function is a scan view, not a parser.
    String::from_utf8_lossy(&decoded).into_owned()
}

/// Decode base64 strings found inline in text
/// Only decodes strings that look like base64 (20+ chars, valid charset)
fn decode_base64_inline(text: &str) -> String {
    use once_cell::sync::Lazy;
    use regex::Regex;

    static BASE64_PATTERN: Lazy<Regex> =
        Lazy::new(|| Regex::new(r"[A-Za-z0-9+/]{20,}=*").expect("base64 pattern"));

    let mut result = String::with_capacity(text.len());
    let mut cursor = 0;
    for cap in BASE64_PATTERN.find_iter(text) {
        result.push_str(&text[cursor..cap.start()]);
        let b64_str = cap.as_str();
        let identifier = |ch: char| ch.is_alphanumeric() || matches!(ch, '_' | '-');
        let complete = !text[..cap.start()]
            .chars()
            .next_back()
            .is_some_and(identifier)
            && !text[cap.end()..]
                .chars()
                .next()
                .is_some_and(|ch| identifier(ch) || ch == '=');
        let decoded = complete
            .then(|| base64_decode(b64_str).ok())
            .flatten()
            .and_then(|bytes| String::from_utf8(bytes).ok())
            .filter(|value| {
                value
                    .chars()
                    .all(|ch| !ch.is_control() || ch.is_whitespace())
            });
        result.push_str(decoded.as_deref().unwrap_or(b64_str));
        cursor = cap.end();
    }
    // Splice each original span exactly once. Replacing the whole accumulated
    // string per token was quadratic and accidentally decoded earlier output.
    result.push_str(&text[cursor..]);
    result
}

/// Simple base64 decoder (no external crate needed)
fn base64_decode(input: &str) -> Result<Vec<u8>, ()> {
    const ALPHABET: &[u8] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

    let data = input.trim_end_matches('=');
    // A scan view is not a wire-format validator. Common decoders accept
    // excess padding and nonzero unused bits; retain that detection coverage.
    if data.len() % 4 == 1 {
        return Err(());
    }
    let input = data;
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
