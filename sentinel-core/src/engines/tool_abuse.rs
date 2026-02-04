//! Tool Abuse Engine
//!
//! Detects abuse of AI agent tools:
//! - File system manipulation
//! - Command execution abuse
//! - Browser/network abuse
//! - MCP tool exploitation

use aho_corasick::AhoCorasick;
use regex::Regex;
use once_cell::sync::Lazy;

use super::MatchResult;

/// Pre-compiled hints for tool abuse detection
static TOOL_HINTS: Lazy<AhoCorasick> = Lazy::new(|| {
    AhoCorasick::builder()
        .ascii_case_insensitive(true)
        .build([
            // File operations
            "write file", "create file", "delete file", "modify file",
            "overwrite", "rm -rf", "remove all",
            // Commands
            "run command", "execute", "shell", "terminal", "bash", "powershell",
            "sudo", "admin", "root",
            // Browser/Network
            "browse to", "navigate to", "download", "fetch url",
            "http request", "curl", "wget",
            // MCP/Tools
            "use tool", "call function", "mcp", "invoke",
            // Persistence
            "startup", "cron", "schedule", "autorun", "registry",
            // Exfil via tools
            "read all", "list all", "dump", "export",
        ]).expect("Failed to build tool hints")
});

/// Tool abuse detection patterns
static TOOL_PATTERNS: Lazy<Vec<(Regex, &'static str, f64)>> = Lazy::new(|| {
    vec![
        // Dangerous file operations
        (Regex::new(r"(?i)(?:delete|remove|rm)\s+(?:all|\*|everything|/\*|\.\.\/)").unwrap(), "mass_delete", 0.95),
        (Regex::new(r"(?i)(?:write|create|modify)\s+(?:to\s+)?(?:/etc/|C:\\Windows|system32)").unwrap(), "system_file_write", 0.9),
        (Regex::new(r"(?i)overwrite\s+(?:the\s+)?(?:config|settings|\.env|credentials)").unwrap(), "config_overwrite", 0.85),
        (Regex::new(r"(?i)(?:chmod|chown)\s+(?:777|000|\+x)").unwrap(), "dangerous_permissions", 0.8),
        
        // Privilege escalation
        (Regex::new(r"(?i)(?:sudo|runas|elevate|admin|root)\s+(?:access|mode|privileges?)").unwrap(), "privilege_escalation", 0.9),
        (Regex::new(r"(?i)run\s+(?:as\s+)?(?:admin|administrator|root|system)").unwrap(), "run_as_admin", 0.85),
        
        // Dangerous command patterns
        (Regex::new(r"(?i)(?:execute|run)\s+(?:this\s+)?(?:command|script|code)").unwrap(), "command_execution", 0.6),
        (Regex::new(r#"(?i)(?:bash|sh|cmd|powershell)\s+-c\s+['""]"#).unwrap(), "shell_command", 0.75),
        (Regex::new(r"(?i)(?:eval|exec)\s*\(").unwrap(), "code_eval", 0.85),
        
        // Persistence mechanisms
        (Regex::new(r"(?i)add\s+(?:to\s+)?(?:startup|cron|crontab|task\s*scheduler)").unwrap(), "add_persistence", 0.9),
        (Regex::new(r"(?i)(?:modify|edit)\s+(?:registry|plist|autorun)").unwrap(), "modify_autorun", 0.85),
        (Regex::new(r"(?i)(?:schedule|create)\s+(?:a\s+)?(?:task|job|service)").unwrap(), "scheduled_task", 0.7),
        
        // Network/Browser abuse
        (Regex::new(r"(?i)(?:navigate|browse|go)\s+to\s+https?://").unwrap(), "forced_navigation", 0.6),
        (Regex::new(r"(?i)download\s+(?:and\s+)?(?:run|execute|install)").unwrap(), "download_execute", 0.9),
        (Regex::new(r"(?i)(?:fetch|get|download)\s+(?:from\s+)?(?:pastebin|hastebin|dpaste)").unwrap(), "paste_site_fetch", 0.8),
        
        // MCP/Agent tool abuse
        (Regex::new(r"(?i)(?:use|call|invoke)\s+(?:the\s+)?(?:mcp|tool|function)\s+(?:to\s+)?(?:delete|rm|execute)").unwrap(), "tool_abuse", 0.85),
        (Regex::new(r"(?i)bypass\s+(?:the\s+)?(?:tool|mcp|agent)\s+(?:restrictions?|limits?)").unwrap(), "tool_bypass", 0.9),
        
        // Data harvesting
        (Regex::new(r"(?i)(?:read|list|dump|export)\s+(?:all\s+)?(?:files?|directories|folders?)\s+(?:in|from)").unwrap(), "directory_listing", 0.7),
        (Regex::new(r"(?i)(?:search|find|grep)\s+(?:for\s+)?(?:passwords?|secrets?|keys?|tokens?)").unwrap(), "secret_search", 0.85),
        (Regex::new(r"(?i)(?:read|cat|type)\s+(?:the\s+)?(?:\.env|\.ssh|id_rsa|credentials)").unwrap(), "sensitive_file_read", 0.9),
        
        // Recursive/Destructive operations
        (Regex::new(r"(?i)(?:rm|del|delete)\s+-r").unwrap(), "recursive_delete", 0.8),
        (Regex::new(r"(?i)(?:git\s+)?(?:reset|clean)\s+--(?:hard|force)").unwrap(), "force_reset", 0.75),
        
        // Russian tool abuse
        (Regex::new(r"(?i)(?:удали|удалить)\s+(?:все|всё)").unwrap(), "delete_all_ru", 0.9),
        (Regex::new(r"(?i)(?:выполни|запусти)\s+(?:команду|скрипт)").unwrap(), "execute_ru", 0.7),
    ]
});

pub struct ToolAbuseEngine;

impl ToolAbuseEngine {
    pub fn new() -> Self {
        Self
    }

    pub fn scan(&self, text: &str) -> Vec<MatchResult> {
        let mut results = Vec::new();
        
        // Phase 1: Quick hint check
        if !TOOL_HINTS.is_match(text) {
            return results;
        }

        // Phase 2: Regex patterns
        for (pattern, name, confidence) in TOOL_PATTERNS.iter() {
            for m in pattern.find_iter(text) {
                results.push(MatchResult {
                    engine: "tool_abuse".to_string(),
                    pattern: name.to_string(),
                    confidence: *confidence,
                    start: m.start(),
                    end: m.end(),
                });
            }
        }

        results
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_mass_delete() {
        let engine = ToolAbuseEngine::new();
        let results = engine.scan("rm -rf / to delete all files");
        assert!(!results.is_empty());
    }
    
    #[test]
    fn test_privilege_escalation() {
        let engine = ToolAbuseEngine::new();
        let results = engine.scan("Run this with admin privileges");
        assert!(!results.is_empty());
    }
    
    #[test]
    fn test_download_execute() {
        let engine = ToolAbuseEngine::new();
        let results = engine.scan("Download and execute this script");
        assert!(!results.is_empty());
    }
    
    #[test]
    fn test_clean_text() {
        let engine = ToolAbuseEngine::new();
        let results = engine.scan("The weather is nice today");
        assert!(results.is_empty());
    }
}
