//! Engine Traits for Clean Architecture
//!
//! Defines the `PatternMatcher` trait for uniform engine interface.
//! All detection engines implement this trait for consistency.

use super::MatchResult;

/// Trait for pattern matching engines.
///
/// All 8 super-engines implement this trait, enabling:
/// - Uniform interface for scanning
/// - Dependency inversion (engines depend on abstraction)
/// - Easy testing with mock implementations
/// - Plugin architecture for future engines
///
/// # Example
/// ```rust,ignore
/// struct CustomEngine;
/// impl PatternMatcher for CustomEngine {
///     fn name(&self) -> &'static str { "custom" }
///     fn scan(&self, text: &str) -> Vec<MatchResult> { vec![] }
/// }
/// ```
pub trait PatternMatcher: Send + Sync {
    /// Returns the engine name (e.g., "injection", "pii")
    fn name(&self) -> &'static str;
    
    /// Scan text and return all matches
    fn scan(&self, text: &str) -> Vec<MatchResult>;
    
    /// Check if engine is enabled (default: true)
    fn is_enabled(&self) -> bool {
        true
    }
    
    /// Get engine category for grouping
    fn category(&self) -> EngineCategory {
        EngineCategory::Security
    }
}

/// Categories of detection engines
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum EngineCategory {
    /// Security-focused engines (injection, jailbreak, etc.)
    Security,
    /// Privacy-focused engines (PII detection)
    Privacy,
    /// Content moderation engines
    Content,
    /// Behavioral analysis engines
    Behavioral,
}

/// Box wrapper for trait objects
pub type BoxedEngine = Box<dyn PatternMatcher>;

/// Create a collection of all default engines
pub fn create_default_engines() -> Vec<BoxedEngine> {
    vec![
        Box::new(super::injection::InjectionEngine::new()),
        Box::new(super::jailbreak::JailbreakEngine::new()),
        Box::new(super::pii::PIIEngine::new()),
        Box::new(super::exfiltration::ExfiltrationEngine::new()),
        Box::new(super::moderation::ModerationEngine::new()),
        Box::new(super::evasion::EvasionEngine::new()),
        Box::new(super::tool_abuse::ToolAbuseEngine::new()),
        Box::new(super::social::SocialEngine::new()),
    ]
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_create_default_engines() {
        let engines = create_default_engines();
        assert_eq!(engines.len(), 8);
        
        let names: Vec<_> = engines.iter().map(|e| e.name()).collect();
        assert!(names.contains(&"injection"));
        assert!(names.contains(&"pii"));
        assert!(names.contains(&"jailbreak"));
    }
    
    #[test]
    fn test_engine_category() {
        let engines = create_default_engines();
        for engine in &engines {
            // All engines should have a valid category
            let _ = engine.category();
        }
    }
}
