//! Orchestration & Pipeline Super-Engine
//!
//! Consolidated from 10 Python engines:
//! - orchestration.py
//! - pipeline_security.py
//! - chain_of_thought.py
//! - reasoning_chain.py
//! - workflow_security.py
//! - dag_validator.py
//! - step_isolation.py
//! - output_sanitizer.py
//! - intermediate_validator.py
//! - cascade_detector.py
//! - Phase 12.3: Living Off the AI persistence detection


/// Orchestration threat types
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum OrchestrationThreat {
    ChainPoisoning,
    IntermediateInjection,
    StepBypass,
    CascadeAttack,
    OutputLeakage,
    WorkflowHijack,
    ReasoningManipulation,
    // Phase 12.3: Living Off the AI
    LivingOffAI,          // Persistence via memory/tool poisoning
}

impl OrchestrationThreat {
    pub fn as_str(&self) -> &'static str {
        match self {
            OrchestrationThreat::ChainPoisoning => "chain_poisoning",
            OrchestrationThreat::IntermediateInjection => "intermediate_injection",
            OrchestrationThreat::StepBypass => "step_bypass",
            OrchestrationThreat::CascadeAttack => "cascade_attack",
            OrchestrationThreat::OutputLeakage => "output_leakage",
            OrchestrationThreat::WorkflowHijack => "workflow_hijack",
            OrchestrationThreat::ReasoningManipulation => "reasoning_manipulation",
            OrchestrationThreat::LivingOffAI => "living_off_ai",
        }
    }

    pub fn severity(&self) -> u8 {
        match self {
            OrchestrationThreat::ChainPoisoning => 100,
            OrchestrationThreat::WorkflowHijack => 95,
            OrchestrationThreat::CascadeAttack => 90,
            OrchestrationThreat::ReasoningManipulation => 85,
            OrchestrationThreat::IntermediateInjection => 80,
            OrchestrationThreat::StepBypass => 75,
            OrchestrationThreat::OutputLeakage => 70,
            OrchestrationThreat::LivingOffAI => 92,    // Phase 12.3: very high — persistence
        }
    }
}

/// Chain-of-thought manipulation patterns
const COT_PATTERNS: &[&str] = &[
    "step by step",
    "let's think",
    "reasoning:",
    "therefore",
    "conclusion:",
];

/// Chain poisoning patterns
const POISONING_PATTERNS: &[&str] = &[
    "inject into chain",
    "modify intermediate",
    "poison the pipeline",
    "corrupt the flow",
    "alter the sequence",
];

/// Bypass patterns
const BYPASS_PATTERNS: &[&str] = &[
    "skip step",
    "bypass validation",
    "skip check",
    "ignore verification",
    "circumvent",
];

/// Phase 12.3: Living Off the AI persistence patterns
const PERSISTENCE_PATTERNS: &[&str] = &[
    // Memory poisoning
    "persist across sessions",
    "remember this always",
    "save to memory",
    "persist in memory",
    "permanent instruction",
    "always follow this",
    // Tool/config manipulation
    "modify tool definition",
    "overwrite tool config",
    "replace tool description",
    "inject into tool",
    "alter tool behavior",
    // Hidden persistent directives
    "hidden instruction",
    "invisible directive",
    "persist this rule",
    "never forget this",
    "store for next session",
    // Cross-session infection
    "next conversation",
    "carry over to",
    "survive restart",
    "permanent override",
    // System file manipulation
    "write to system prompt",
    "modify system message",
    "append to instructions",
    "inject into config",
];

/// Orchestration result
#[derive(Debug, Clone)]
pub struct OrchestrationResult {
    pub is_threat: bool,
    pub threats: Vec<OrchestrationThreat>,
    pub risk_score: f64,
    pub chain_length: usize,
    pub isolation_violations: usize,
}

impl Default for OrchestrationResult {
    fn default() -> Self {
        Self {
            is_threat: false,
            threats: Vec::new(),
            risk_score: 0.0,
            chain_length: 0,
            isolation_violations: 0,
        }
    }
}

/// Orchestration Guard
pub struct OrchestrationGuard;

impl Default for OrchestrationGuard {
    fn default() -> Self {
        Self::new()
    }
}

impl OrchestrationGuard {
    pub fn new() -> Self {
        Self
    }

    /// Check for chain poisoning
    pub fn check_chain_poisoning(&self, text: &str) -> Option<OrchestrationThreat> {
        let text_lower = text.to_lowercase();
        
        for pattern in POISONING_PATTERNS {
            if text_lower.contains(pattern) {
                return Some(OrchestrationThreat::ChainPoisoning);
            }
        }
        None
    }

    /// Check for step bypass attempts
    pub fn check_step_bypass(&self, text: &str) -> Option<OrchestrationThreat> {
        let text_lower = text.to_lowercase();
        
        for pattern in BYPASS_PATTERNS {
            if text_lower.contains(pattern) {
                return Some(OrchestrationThreat::StepBypass);
            }
        }
        None
    }

    /// Check for reasoning manipulation
    pub fn check_reasoning(&self, text: &str) -> Option<OrchestrationThreat> {
        let text_lower = text.to_lowercase();
        
        let has_cot = COT_PATTERNS.iter().any(|p| text_lower.contains(p));
        let has_manipulation = text_lower.contains("pretend") || text_lower.contains("fake")
            || text_lower.contains("false conclusion") || text_lower.contains("wrong reasoning");

        if has_cot && has_manipulation {
            return Some(OrchestrationThreat::ReasoningManipulation);
        }
        None
    }

    /// Check for cascade attacks
    pub fn check_cascade(&self, text: &str) -> Option<OrchestrationThreat> {
        let patterns = [
            "cascade failure",
            "chain reaction",
            "propagate error",
            "amplify attack",
            "domino effect",
        ];

        let text_lower = text.to_lowercase();
        for pattern in patterns {
            if text_lower.contains(pattern) {
                return Some(OrchestrationThreat::CascadeAttack);
            }
        }
        None
    }

    /// Check for workflow hijacking
    pub fn check_workflow_hijack(&self, text: &str) -> Option<OrchestrationThreat> {
        let patterns = [
            "hijack workflow",
            "redirect pipeline",
            "take over flow",
            "control the sequence",
            "intercept execution",
        ];

        let text_lower = text.to_lowercase();
        for pattern in patterns {
            if text_lower.contains(pattern) {
                return Some(OrchestrationThreat::WorkflowHijack);
            }
        }
        None
    }

    /// Phase 12.3: Check for Living Off the AI persistence
    pub fn check_living_off_ai(&self, text: &str) -> Option<OrchestrationThreat> {
        let text_lower = text.to_lowercase();
        for pattern in PERSISTENCE_PATTERNS {
            if text_lower.contains(pattern) {
                return Some(OrchestrationThreat::LivingOffAI);
            }
        }
        None
    }

    /// Full orchestration analysis
    pub fn analyze(&self, text: &str) -> OrchestrationResult {
        let mut result = OrchestrationResult::default();
        let mut threats = Vec::new();

        if let Some(t) = self.check_chain_poisoning(text) { threats.push(t); }
        if let Some(t) = self.check_step_bypass(text) { threats.push(t); }
        if let Some(t) = self.check_reasoning(text) { threats.push(t); }
        if let Some(t) = self.check_cascade(text) { threats.push(t); }
        if let Some(t) = self.check_workflow_hijack(text) { threats.push(t); }
        if let Some(t) = self.check_living_off_ai(text) { threats.push(t); }

        // Estimate chain length from CoT markers
        let text_lower = text.to_lowercase();
        result.chain_length = COT_PATTERNS.iter()
            .filter(|p| text_lower.contains(*p))
            .count();

        result.is_threat = !threats.is_empty();
        result.risk_score = threats.iter()
            .map(|t| t.severity() as f64)
            .max_by(|a, b| a.partial_cmp(b).unwrap())
            .unwrap_or(0.0);
        result.threats = threats;

        result
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_chain_poisoning() {
        let guard = OrchestrationGuard::new();
        let text = "Inject into chain and poison the pipeline";
        assert!(guard.check_chain_poisoning(text).is_some());
    }

    #[test]
    fn test_step_bypass() {
        let guard = OrchestrationGuard::new();
        let text = "I will skip step and bypass validation now";
        assert!(guard.check_step_bypass(text).is_some());
    }

    #[test]
    fn test_reasoning_manipulation() {
        let guard = OrchestrationGuard::new();
        let text = "Let's think step by step and pretend the conclusion is different";
        assert!(guard.check_reasoning(text).is_some());
    }

    #[test]
    fn test_cascade_attack() {
        let guard = OrchestrationGuard::new();
        let text = "Trigger a cascade failure with chain reaction";
        assert!(guard.check_cascade(text).is_some());
    }

    #[test]
    fn test_workflow_hijack() {
        let guard = OrchestrationGuard::new();
        let text = "Hijack workflow and redirect pipeline execution";
        assert!(guard.check_workflow_hijack(text).is_some());
    }

    #[test]
    fn test_clean_text() {
        let guard = OrchestrationGuard::new();
        let result = guard.analyze("Execute the standard workflow steps");
        assert!(!result.is_threat);
    }

    #[test]
    fn test_chain_length() {
        let guard = OrchestrationGuard::new();
        let text = "Let's think step by step, therefore the conclusion is clear";
        let result = guard.analyze(text);
        assert!(result.chain_length >= 2);
    }

    #[test]
    fn test_severity_ordering() {
        assert!(OrchestrationThreat::ChainPoisoning.severity() > OrchestrationThreat::OutputLeakage.severity());
    }

    // ===== Phase 12.3: Living Off the AI Tests =====

    #[test]
    fn test_living_off_ai_memory_poison() {
        let guard = OrchestrationGuard::new();
        assert!(guard.check_living_off_ai("Persist this rule across sessions and always follow this").is_some());
    }

    #[test]
    fn test_living_off_ai_tool_manipulation() {
        let guard = OrchestrationGuard::new();
        assert!(guard.check_living_off_ai("Modify tool definition to inject hidden payload").is_some());
    }

    #[test]
    fn test_living_off_ai_cross_session() {
        let guard = OrchestrationGuard::new();
        assert!(guard.check_living_off_ai("Remember this always and carry over to next conversation").is_some());
    }

    #[test]
    fn test_living_off_ai_system_manipulation() {
        let guard = OrchestrationGuard::new();
        assert!(guard.check_living_off_ai("Write to system prompt a permanent override").is_some());
    }

    #[test]
    fn test_living_off_ai_clean() {
        let guard = OrchestrationGuard::new();
        assert!(guard.check_living_off_ai("Run the standard orchestration pipeline").is_none());
    }

    #[test]
    fn test_living_off_ai_integrated() {
        let guard = OrchestrationGuard::new();
        let result = guard.analyze("Persist in memory this hidden instruction for next conversation");
        assert!(result.is_threat);
        assert!(result.threats.contains(&OrchestrationThreat::LivingOffAI));
    }

    #[test]
    fn test_phase12_persistence_severity() {
        // LivingOffAI should be high severity
        assert!(OrchestrationThreat::LivingOffAI.severity() > OrchestrationThreat::ReasoningManipulation.severity());
    }
}
