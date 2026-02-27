//! Hybrid Engine with CDN Pattern Loading
//!
//! Example of runtime pattern loading from SENTINEL CDN signatures.
//! Uses embedded patterns as fallback, loads CDN patterns when available.

use crate::engines::MatchResult;
use crate::engines::traits::PatternMatcher;
use crate::signatures::{SignatureLoader, CompiledPattern};
use once_cell::sync::Lazy;

/// Pre-compiled patterns from embedded signatures
static EMBEDDED_PII_PATTERNS: Lazy<Vec<CompiledPattern>> = Lazy::new(|| {
    SignatureLoader::load_pii_embedded().compile_patterns()
});

/// Hybrid PII Engine that can use CDN or embedded patterns
pub struct HybridPiiEngine {
    patterns: Vec<CompiledPattern>,
    source: PatternSource,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PatternSource {
    Embedded,
    #[cfg(feature = "cdn")]
    Cdn,
    #[cfg(feature = "cdn")]
    CdnCached,
}

impl PatternMatcher for HybridPiiEngine {
    fn name(&self) -> &'static str {
        "pii_hybrid"
    }

    fn scan(&self, text: &str) -> Vec<MatchResult> {
        // Delegate to inherent scan method
        let mut results = Vec::new();
        for pattern in &self.patterns {
            if let Some(m) = pattern.regex.find(text) {
                results.push(MatchResult {
                    engine: "pii_hybrid".to_string(),
                    pattern: pattern.id.clone(),
                    confidence: pattern.confidence,
                    start: m.start(),
                    end: m.end(),
                });
            }
        }
        results
    }

    fn category(&self) -> crate::engines::traits::EngineCategory {
        crate::engines::traits::EngineCategory::Privacy
    }
}

impl Default for HybridPiiEngine {
    fn default() -> Self {
        Self::new()
    }
}

impl HybridPiiEngine {
    /// Create with embedded patterns (fast, no network)
    pub fn new() -> Self {
        Self {
            patterns: EMBEDDED_PII_PATTERNS.clone(),
            source: PatternSource::Embedded,
        }
    }
    
    /// Create with custom patterns
    pub fn with_patterns(patterns: Vec<CompiledPattern>, source: PatternSource) -> Self {
        Self { patterns, source }
    }
    
    /// Get pattern source
    pub fn source(&self) -> PatternSource {
        self.source
    }
    
    /// Get pattern count
    pub fn pattern_count(&self) -> usize {
        self.patterns.len()
    }
    
    /// Scan text for PII
    pub fn scan(&self, text: &str) -> Vec<MatchResult> {
        let mut results = Vec::new();
        
        for pattern in &self.patterns {
            if let Some(m) = pattern.regex.find(text) {
                results.push(MatchResult {
                    engine: "pii_hybrid".to_string(),
                    pattern: pattern.id.clone(),
                    confidence: pattern.confidence,
                    start: m.start(),
                    end: m.end(),
                });
            }
        }
        
        results
    }
}

#[cfg(feature = "cdn")]
impl HybridPiiEngine {
    /// Load patterns from CDN (async)
    pub async fn from_cdn() -> Result<Self, crate::signatures::SignatureError> {
        let loader = SignatureLoader::new();
        let sigs = loader.load_pii().await?;
        let patterns = sigs.compile_patterns();
        
        Ok(Self {
            patterns,
            source: PatternSource::Cdn,
        })
    }
    
    /// Try CDN first, fallback to embedded
    pub async fn from_cdn_or_embedded() -> Self {
        match Self::from_cdn().await {
            Ok(engine) => engine,
            Err(e) => {
                log::warn!("CDN load failed, using embedded: {}", e);
                Self::new()
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_hybrid_engine_embedded() {
        let engine = HybridPiiEngine::new();
        assert_eq!(engine.source(), PatternSource::Embedded);
        assert!(engine.pattern_count() > 0);
    }
    
    #[test]
    fn test_hybrid_scan_email() {
        let engine = HybridPiiEngine::new();
        let results = engine.scan("Contact me at test@example.com");
        
        assert!(!results.is_empty());
        assert!(results.iter().any(|r| r.pattern == "pii_email"));
    }
    
    #[test]
    fn test_hybrid_scan_ssn() {
        let engine = HybridPiiEngine::new();
        let results = engine.scan("SSN: 123-45-6789");
        
        assert!(!results.is_empty());
        assert!(results.iter().any(|r| r.pattern == "pii_ssn"));
    }
    
    #[test]
    fn test_hybrid_scan_openai_key() {
        let engine = HybridPiiEngine::new();
        // OpenAI key format: sk- followed by exactly 48 alphanumeric characters
        let results = engine.scan("API key: sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx");
        
        assert!(!results.is_empty(), "Should detect OpenAI key pattern");
        assert!(results.iter().any(|r| r.pattern == "secret_openai"));
    }
    
    #[test]
    fn test_hybrid_scan_clean() {
        let engine = HybridPiiEngine::new();
        let results = engine.scan("Hello world, this is clean text");
        assert!(results.is_empty());
    }
}
