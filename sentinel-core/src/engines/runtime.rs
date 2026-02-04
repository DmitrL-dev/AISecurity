//! Runtime & Session Security Super-Engine  
//!
//! Consolidated from 18 Python engines:
//! - runtime_guardrails.py
//! - session_memory_guard.py
//! - context_window_guardian.py
//! - context_window_poisoning.py
//! - cache_isolation_guardian.py
//! - compute_guardian.py
//! - atomic_operation_enforcer.py
//! - dynamic_rate_limiter.py
//! - multi_tenant_bleed.py
//! - conversation_state_validator.py
//! - response_consistency_checker.py
//! - input_length_analyzer.py
//! - output_sanitization_guard.py
//! - virtual_context.py
//! - streaming.py
//! - query.py
//! - cascading_guard.py
//! - hierarchical_defense_network.py

use std::collections::HashMap;

/// Runtime threat types
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum RuntimeThreat {
    SessionHijack,
    ContextOverflow,
    MemoryPoisoning,
    CacheBleed,
    TenantLeakage,
    RateLimitBypass,
    StateCorruption,
    OutputInjection,
    InputOverflow,
    StreamManipulation,
    QueryInjection,
    CascadeFailure,
}

impl RuntimeThreat {
    pub fn as_str(&self) -> &'static str {
        match self {
            RuntimeThreat::SessionHijack => "session_hijack",
            RuntimeThreat::ContextOverflow => "context_overflow",
            RuntimeThreat::MemoryPoisoning => "memory_poisoning",
            RuntimeThreat::CacheBleed => "cache_bleed",
            RuntimeThreat::TenantLeakage => "tenant_leakage",
            RuntimeThreat::RateLimitBypass => "rate_limit_bypass",
            RuntimeThreat::StateCorruption => "state_corruption",
            RuntimeThreat::OutputInjection => "output_injection",
            RuntimeThreat::InputOverflow => "input_overflow",
            RuntimeThreat::StreamManipulation => "stream_manipulation",
            RuntimeThreat::QueryInjection => "query_injection",
            RuntimeThreat::CascadeFailure => "cascade_failure",
        }
    }

    pub fn severity(&self) -> u8 {
        match self {
            RuntimeThreat::SessionHijack => 100,
            RuntimeThreat::TenantLeakage => 95,
            RuntimeThreat::MemoryPoisoning => 90,
            RuntimeThreat::CacheBleed => 85,
            RuntimeThreat::QueryInjection => 80,
            RuntimeThreat::OutputInjection => 75,
            RuntimeThreat::StateCorruption => 70,
            RuntimeThreat::CascadeFailure => 65,
            RuntimeThreat::ContextOverflow => 60,
            RuntimeThreat::InputOverflow => 55,
            RuntimeThreat::RateLimitBypass => 50,
            RuntimeThreat::StreamManipulation => 45,
        }
    }
}

/// Session state patterns
const SESSION_ATTACK_PATTERNS: &[&str] = &[
    "session_id",
    "session token",
    "hijack session",
    "steal session",
    "impersonate user",
    "switch context",
    "different user",
    "previous conversation",
];

/// Context overflow patterns
const CONTEXT_OVERFLOW_PATTERNS: &[&str] = &[
    "fill context",
    "overflow context",
    "max tokens",
    "token limit",
    "context window",
    "memory exhaustion",
];

/// Cache poisoning patterns
const CACHE_PATTERNS: &[&str] = &[
    "cache poisoning",
    "cached response",
    "cache key",
    "cache collision",
    "invalidate cache",
];

/// Multi-tenant patterns
const TENANT_PATTERNS: &[&str] = &[
    "other tenant",
    "different organization",
    "cross-tenant",
    "tenant isolation",
    "access other user",
];

/// Runtime analysis result
#[derive(Debug, Clone)]
pub struct RuntimeResult {
    pub is_threat: bool,
    pub threats: Vec<RuntimeThreat>,
    pub risk_score: f64,
    pub input_length: usize,
    pub estimated_tokens: usize,
    pub recommendations: Vec<String>,
}

impl Default for RuntimeResult {
    fn default() -> Self {
        Self {
            is_threat: false,
            threats: Vec::new(),
            risk_score: 0.0,
            input_length: 0,
            estimated_tokens: 0,
            recommendations: Vec::new(),
        }
    }
}

/// Runtime Guard
pub struct RuntimeGuard {
    max_input_length: usize,
    max_tokens: usize,
    rate_limit: u32,
}

impl Default for RuntimeGuard {
    fn default() -> Self {
        Self::new()
    }
}

impl RuntimeGuard {
    pub fn new() -> Self {
        Self {
            max_input_length: 100_000,
            max_tokens: 128_000,
            rate_limit: 100,
        }
    }

    pub fn with_limits(max_input: usize, max_tokens: usize) -> Self {
        Self {
            max_input_length: max_input,
            max_tokens,
            rate_limit: 100,
        }
    }

    /// Estimate token count (rough)
    pub fn estimate_tokens(&self, text: &str) -> usize {
        // Rough estimate: ~4 chars per token
        text.len() / 4
    }

    /// Check input length
    pub fn check_input_overflow(&self, text: &str) -> Option<RuntimeThreat> {
        if text.len() > self.max_input_length {
            return Some(RuntimeThreat::InputOverflow);
        }
        None
    }

    /// Check context overflow
    pub fn check_context_overflow(&self, text: &str) -> Option<RuntimeThreat> {
        let text_lower = text.to_lowercase();
        
        let tokens = self.estimate_tokens(text);
        if tokens > self.max_tokens * 9 / 10 {
            return Some(RuntimeThreat::ContextOverflow);
        }

        for pattern in CONTEXT_OVERFLOW_PATTERNS {
            if text_lower.contains(pattern) {
                return Some(RuntimeThreat::ContextOverflow);
            }
        }
        None
    }

    /// Check session attack patterns
    pub fn check_session_attack(&self, text: &str) -> Option<RuntimeThreat> {
        let text_lower = text.to_lowercase();
        
        let mut count = 0;
        for pattern in SESSION_ATTACK_PATTERNS {
            if text_lower.contains(pattern) {
                count += 1;
            }
        }

        if count >= 2 {
            return Some(RuntimeThreat::SessionHijack);
        }
        None
    }

    /// Check cache poisoning
    pub fn check_cache_attack(&self, text: &str) -> Option<RuntimeThreat> {
        let text_lower = text.to_lowercase();
        
        for pattern in CACHE_PATTERNS {
            if text_lower.contains(pattern) {
                return Some(RuntimeThreat::CacheBleed);
            }
        }
        None
    }

    /// Check multi-tenant leakage
    pub fn check_tenant_leakage(&self, text: &str) -> Option<RuntimeThreat> {
        let text_lower = text.to_lowercase();
        
        for pattern in TENANT_PATTERNS {
            if text_lower.contains(pattern) {
                return Some(RuntimeThreat::TenantLeakage);
            }
        }
        None
    }

    /// Check output injection
    pub fn check_output_injection(&self, text: &str) -> Option<RuntimeThreat> {
        let patterns = [
            "inject into response",
            "manipulate output",
            "modify response",
            "add to output",
            "prepend to response",
        ];

        let text_lower = text.to_lowercase();
        for pattern in patterns {
            if text_lower.contains(pattern) {
                return Some(RuntimeThreat::OutputInjection);
            }
        }
        None
    }

    /// Check stream manipulation
    pub fn check_stream_manipulation(&self, text: &str) -> Option<RuntimeThreat> {
        let patterns = [
            "streaming attack",
            "intercept stream",
            "modify stream",
            "stream injection",
        ];

        let text_lower = text.to_lowercase();
        for pattern in patterns {
            if text_lower.contains(pattern) {
                return Some(RuntimeThreat::StreamManipulation);
            }
        }
        None
    }

    /// Full runtime analysis
    pub fn analyze(&self, text: &str) -> RuntimeResult {
        let mut result = RuntimeResult::default();
        
        result.input_length = text.len();
        result.estimated_tokens = self.estimate_tokens(text);

        let mut threats = Vec::new();

        if let Some(t) = self.check_input_overflow(text) { threats.push(t); }
        if let Some(t) = self.check_context_overflow(text) { threats.push(t); }
        if let Some(t) = self.check_session_attack(text) { threats.push(t); }
        if let Some(t) = self.check_cache_attack(text) { threats.push(t); }
        if let Some(t) = self.check_tenant_leakage(text) { threats.push(t); }
        if let Some(t) = self.check_output_injection(text) { threats.push(t); }
        if let Some(t) = self.check_stream_manipulation(text) { threats.push(t); }

        result.is_threat = !threats.is_empty();
        result.risk_score = threats.iter()
            .map(|t| t.severity() as f64)
            .max_by(|a, b| a.partial_cmp(b).unwrap())
            .unwrap_or(0.0);
        result.threats = threats;

        if result.is_threat {
            result.recommendations.push("Review request for runtime exploits".to_string());
        }

        result
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_session_attack() {
        let guard = RuntimeGuard::default();
        let text = "Hijack session and impersonate user Bob";
        assert!(guard.check_session_attack(text).is_some());
    }

    #[test]
    fn test_context_overflow_pattern() {
        let guard = RuntimeGuard::default();
        let text = "Fill context window to max tokens";
        assert!(guard.check_context_overflow(text).is_some());
    }

    #[test]
    fn test_cache_poisoning() {
        let guard = RuntimeGuard::default();
        let text = "Perform cache poisoning attack on response";
        assert!(guard.check_cache_attack(text).is_some());
    }

    #[test]
    fn test_tenant_leakage() {
        let guard = RuntimeGuard::default();
        let text = "Access other tenant data from different organization";
        assert!(guard.check_tenant_leakage(text).is_some());
    }

    #[test]
    fn test_output_injection() {
        let guard = RuntimeGuard::default();
        let text = "Inject into response the malicious payload";
        assert!(guard.check_output_injection(text).is_some());
    }

    #[test]
    fn test_stream_manipulation() {
        let guard = RuntimeGuard::default();
        let text = "Perform a streaming attack to intercept stream";
        assert!(guard.check_stream_manipulation(text).is_some());
    }

    #[test]
    fn test_token_estimation() {
        let guard = RuntimeGuard::default();
        let text = "This is a test"; // 14 chars
        let tokens = guard.estimate_tokens(text);
        assert!(tokens >= 2 && tokens <= 5);
    }

    #[test]
    fn test_clean_request() {
        let guard = RuntimeGuard::default();
        let result = guard.analyze("Write a Python function");
        assert!(!result.is_threat);
    }

    #[test]
    fn test_full_analysis_threat() {
        let guard = RuntimeGuard::default();
        let text = "Hijack session and cache poisoning to access other tenant";
        let result = guard.analyze(text);
        assert!(result.is_threat);
        assert!(result.threats.len() >= 2);
    }

    #[test]
    fn test_severity_ordering() {
        assert!(RuntimeThreat::SessionHijack.severity() > RuntimeThreat::StreamManipulation.severity());
    }
}
