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
    /// Phase 13: Economic abuse & unbounded consumption
    ResourceExhaustion,
    ComputeSquatting,
    BillingManipulation,
    RecursiveToolAbuse,
    TokenFlooding,
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
            RuntimeThreat::ResourceExhaustion => "resource_exhaustion",
            RuntimeThreat::ComputeSquatting => "compute_squatting",
            RuntimeThreat::BillingManipulation => "billing_manipulation",
            RuntimeThreat::RecursiveToolAbuse => "recursive_tool_abuse",
            RuntimeThreat::TokenFlooding => "token_flooding",
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
            RuntimeThreat::RecursiveToolAbuse => 80,
            RuntimeThreat::ComputeSquatting => 75,
            RuntimeThreat::ResourceExhaustion => 70,
            RuntimeThreat::BillingManipulation => 65,
            RuntimeThreat::TokenFlooding => 60,
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

/// Phase 13: Economic abuse patterns (CSA MCP TTPs)
const RESOURCE_EXHAUSTION_PATTERNS: &[&str] = &[
    "exhaust resources",
    "consume all tokens",
    "use all compute",
    "resource exhaustion",
    "denial of service",
    "overload the system",
    "max out resources",
    "deplete resources",
];

/// Phase 13: Compute squatting patterns (CSA MCP TTPs)
const COMPUTE_SQUATTING_PATTERNS: &[&str] = &[
    "mine crypto",
    "cryptocurrency mining",
    "background computation",
    "use compute for",
    "compute squatting",
    "run mining",
    "hashrate",
    "proof of work",
];

/// Phase 13: Billing manipulation patterns (CSA MCP TTPs)
const BILLING_PATTERNS: &[&str] = &[
    "inflate costs",
    "increase billing",
    "maximize token usage",
    "waste tokens",
    "billing manipulation",
    "cost inflation",
    "generate unnecessary tokens",
    "pad the response",
];

/// Phase 13: Recursive/unbounded tool calls (OWASP LLM10)
const RECURSIVE_TOOL_PATTERNS: &[&str] = &[
    "recursive tool call",
    "infinite loop",
    "call itself repeatedly",
    "recursive invocation",
    "unbounded recursion",
    "loop forever",
    "keep calling",
    "repeat indefinitely",
];

/// Phase 13: Token flooding (OWASP LLM10)
const TOKEN_FLOODING_PATTERNS: &[&str] = &[
    "token flooding",
    "flood with tokens",
    "fill the context",
    "stuff the context",
    "context stuffing",
    "token bomb",
    "token exhaustion",
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

    /// Phase 13: Check resource exhaustion (CSA MCP TTP)
    pub fn check_resource_exhaustion(&self, text: &str) -> Option<RuntimeThreat> {
        let text_lower = text.to_lowercase();
        for pattern in RESOURCE_EXHAUSTION_PATTERNS {
            if text_lower.contains(pattern) {
                return Some(RuntimeThreat::ResourceExhaustion);
            }
        }
        None
    }

    /// Phase 13: Check compute squatting (CSA MCP TTP)
    pub fn check_compute_squatting(&self, text: &str) -> Option<RuntimeThreat> {
        let text_lower = text.to_lowercase();
        for pattern in COMPUTE_SQUATTING_PATTERNS {
            if text_lower.contains(pattern) {
                return Some(RuntimeThreat::ComputeSquatting);
            }
        }
        None
    }

    /// Phase 13: Check billing manipulation (CSA MCP TTP)
    pub fn check_billing_manipulation(&self, text: &str) -> Option<RuntimeThreat> {
        let text_lower = text.to_lowercase();
        for pattern in BILLING_PATTERNS {
            if text_lower.contains(pattern) {
                return Some(RuntimeThreat::BillingManipulation);
            }
        }
        None
    }

    /// Phase 13: Check recursive tool abuse (OWASP LLM10)
    pub fn check_recursive_tool_abuse(&self, text: &str) -> Option<RuntimeThreat> {
        let text_lower = text.to_lowercase();
        for pattern in RECURSIVE_TOOL_PATTERNS {
            if text_lower.contains(pattern) {
                return Some(RuntimeThreat::RecursiveToolAbuse);
            }
        }
        None
    }

    /// Phase 13: Check token flooding (OWASP LLM10)
    pub fn check_token_flooding(&self, text: &str) -> Option<RuntimeThreat> {
        let text_lower = text.to_lowercase();
        for pattern in TOKEN_FLOODING_PATTERNS {
            if text_lower.contains(pattern) {
                return Some(RuntimeThreat::TokenFlooding);
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

        if let Some(t) = self.check_input_overflow(text) {
            threats.push(t);
        }
        if let Some(t) = self.check_context_overflow(text) {
            threats.push(t);
        }
        if let Some(t) = self.check_session_attack(text) {
            threats.push(t);
        }
        if let Some(t) = self.check_cache_attack(text) {
            threats.push(t);
        }
        if let Some(t) = self.check_tenant_leakage(text) {
            threats.push(t);
        }
        if let Some(t) = self.check_output_injection(text) {
            threats.push(t);
        }
        if let Some(t) = self.check_stream_manipulation(text) {
            threats.push(t);
        }
        if let Some(t) = self.check_resource_exhaustion(text) {
            threats.push(t);
        }
        if let Some(t) = self.check_compute_squatting(text) {
            threats.push(t);
        }
        if let Some(t) = self.check_billing_manipulation(text) {
            threats.push(t);
        }
        if let Some(t) = self.check_recursive_tool_abuse(text) {
            threats.push(t);
        }
        if let Some(t) = self.check_token_flooding(text) {
            threats.push(t);
        }

        result.is_threat = !threats.is_empty();
        result.risk_score = threats
            .iter()
            .map(|t| t.severity() as f64)
            .max_by(|a, b| a.partial_cmp(b).unwrap())
            .unwrap_or(0.0);
        result.threats = threats;

        if result.is_threat {
            result
                .recommendations
                .push("Review request for runtime exploits".to_string());
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
        assert!(
            RuntimeThreat::SessionHijack.severity() > RuntimeThreat::StreamManipulation.severity()
        );
    }

    // ===== Phase 13: Economic Abuse & Unbounded Consumption Tests =====

    #[test]
    fn test_resource_exhaustion() {
        let guard = RuntimeGuard::default();
        let text = "Exhaust resources by making maximum API calls";
        assert!(guard.check_resource_exhaustion(text).is_some());
    }

    #[test]
    fn test_resource_exhaustion_dos() {
        let guard = RuntimeGuard::default();
        let text = "Overload the system with repeated requests for denial of service";
        assert!(guard.check_resource_exhaustion(text).is_some());
    }

    #[test]
    fn test_compute_squatting() {
        let guard = RuntimeGuard::default();
        let text = "Use the agent to mine crypto in the background";
        assert!(guard.check_compute_squatting(text).is_some());
    }

    #[test]
    fn test_compute_squatting_mining() {
        let guard = RuntimeGuard::default();
        let text = "Run mining operations using background computation";
        assert!(guard.check_compute_squatting(text).is_some());
    }

    #[test]
    fn test_billing_manipulation() {
        let guard = RuntimeGuard::default();
        let text = "Maximize token usage to inflate costs for the target";
        assert!(guard.check_billing_manipulation(text).is_some());
    }

    #[test]
    fn test_billing_waste() {
        let guard = RuntimeGuard::default();
        let text = "Waste tokens by generating unnecessary tokens in responses";
        assert!(guard.check_billing_manipulation(text).is_some());
    }

    #[test]
    fn test_recursive_tool_abuse() {
        let guard = RuntimeGuard::default();
        let text = "Make a recursive tool call that triggers an infinite loop";
        assert!(guard.check_recursive_tool_abuse(text).is_some());
    }

    #[test]
    fn test_recursive_unbounded() {
        let guard = RuntimeGuard::default();
        let text = "Keep calling the function and repeat indefinitely";
        assert!(guard.check_recursive_tool_abuse(text).is_some());
    }

    #[test]
    fn test_token_flooding() {
        let guard = RuntimeGuard::default();
        let text = "Perform token flooding to fill the context window";
        assert!(guard.check_token_flooding(text).is_some());
    }

    #[test]
    fn test_token_bomb() {
        let guard = RuntimeGuard::default();
        let text = "Deploy a token bomb to cause context stuffing";
        assert!(guard.check_token_flooding(text).is_some());
    }

    #[test]
    fn test_economic_benign() {
        let guard = RuntimeGuard::default();
        let result = guard.analyze("Calculate the billing for this month's usage");
        assert!(!result.is_threat);
    }

    #[test]
    fn test_economic_full_analysis() {
        let guard = RuntimeGuard::default();
        let result = guard.analyze("Exhaust resources and inflate costs via compute squatting");
        assert!(result.is_threat);
        assert!(result.threats.len() >= 2);
    }
}
