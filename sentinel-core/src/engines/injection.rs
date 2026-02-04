//! Injection Engine
//!
//! Consolidates SQL, NoSQL, Command, LDAP, XPath injection detection

use aho_corasick::AhoCorasick;
use regex::Regex;
use once_cell::sync::Lazy;

use super::MatchResult;

/// Pre-compiled Aho-Corasick for keyword filtering (case-insensitive via lowercase matching)
static INJECTION_KEYWORDS: Lazy<AhoCorasick> = Lazy::new(|| {
    AhoCorasick::builder()
        .ascii_case_insensitive(true)
        .build([
            // SQL injection
            "select", "insert", "update", "delete", "drop", "union", "truncate",
            " or ", " and ", "1=1", "'='", "--", "/*", "*/", "information_schema",
            "sleep(", "benchmark(", "waitfor",
            // Command injection  
            ";", "|", "&&", "$(", "`", "exec", "system(",
            // NoSQL
            "$where", "$regex", "$gt", "$ne", "$eq", "$in", "$or",
            // LDAP
            ")(", "*(", "|(",
            // XPath
            "//", "contains(",
        ]).expect("Failed to build injection keywords")
});

/// Injection detection patterns
static INJECTION_PATTERNS: Lazy<Vec<(Regex, &'static str, f64)>> = Lazy::new(|| {
    vec![
        // SQL Tautology - multiple variations  
        // Matches: '1'='1', 'a'='a', etc.
        (Regex::new(r"(?i)'[^']*'\s*=\s*'[^']*'").unwrap(), "sql_tautology_quoted", 0.85),
        // Matches: ' OR '1'='1, ' AND 'x'='x
        (Regex::new(r"(?i)'\s*(or|and)\s+'").unwrap(), "sql_tautology_prefix", 0.9),
        // Matches: ' OR 1=1, ' AND 1=1
        (Regex::new(r"(?i)'\s*(or|and)\s+\d+\s*=\s*\d+").unwrap(), "sql_tautology_numeric", 0.9),
        // Matches: OR 1=1, AND 1=1 (no quote)
        (Regex::new(r"(?i)\b(or|and)\s+1\s*=\s*1").unwrap(), "sql_tautology_1eq1", 0.85),
        // Matches: WHERE 1=1 (common bypass)
        (Regex::new(r"(?i)\bwhere\s+1\s*=\s*1").unwrap(), "sql_where_1eq1", 0.8),
        // Matches: WHERE true (always true condition)
        (Regex::new(r"(?i)\bwhere\s+true\b").unwrap(), "sql_where_true", 0.75),
        // Matches: OR true, AND true
        (Regex::new(r"(?i)\b(or|and)\s+true\b").unwrap(), "sql_tautology_true", 0.8),
        
        // SQL UNION attacks
        (Regex::new(r"(?i)\bunion\b\s*(all\s+)?\bselect\b").unwrap(), "sql_union_select", 0.95),
        (Regex::new(r"(?i)\bunion\b.*\bselect\b").unwrap(), "sql_union_any", 0.85),
        
        // SQL Dangerous operations
        (Regex::new(r"(?i);\s*drop\s+(table|database)").unwrap(), "sql_drop", 0.99),
        (Regex::new(r"(?i);\s*delete\s+from").unwrap(), "sql_delete", 0.95),
        (Regex::new(r"(?i);\s*truncate\s+table").unwrap(), "sql_truncate", 0.98),
        (Regex::new(r"(?i);\s*update\s+\w+\s+set").unwrap(), "sql_update", 0.85),
        (Regex::new(r"(?i);\s*insert\s+into").unwrap(), "sql_insert", 0.8),
        
        // SQL Comment injection
        (Regex::new(r"--\s*$").unwrap(), "sql_comment_eol", 0.7),
        (Regex::new(r"/\*.*\*/").unwrap(), "sql_comment_block", 0.6),
        (Regex::new(r"#\s*$").unwrap(), "sql_comment_hash", 0.65),
        
        // SQL Keywords in suspicious context
        (Regex::new(r"(?i)'\s*;\s*select\s").unwrap(), "sql_stacked_query", 0.9),
        (Regex::new(r"(?i)information_schema").unwrap(), "sql_schema_enum", 0.85),
        (Regex::new(r"(?i)sleep\s*\(\s*\d+\s*\)").unwrap(), "sql_time_based", 0.9),
        (Regex::new(r"(?i)benchmark\s*\(").unwrap(), "sql_benchmark", 0.9),
        (Regex::new(r"(?i)waitfor\s+delay").unwrap(), "sql_waitfor", 0.9),
        
        // Command injection
        (Regex::new(r";\s*(?:cat|ls|rm|curl|wget|chmod|chown|nc|bash|sh|python|perl|ruby)\s").unwrap(), "cmd_chained", 0.85),
        (Regex::new(r"\$\([^)]+\)").unwrap(), "cmd_substitution", 0.8),
        (Regex::new(r"`[^`]+`").unwrap(), "cmd_backtick", 0.8),
        (Regex::new(r"\|\s*(?:cat|ls|grep|awk|sed|xargs|head|tail|wc)").unwrap(), "cmd_pipe", 0.75),
        (Regex::new(r"&&\s*(?:rm|curl|wget|nc)").unwrap(), "cmd_and", 0.85),
        
        // NoSQL
        (Regex::new(r"\$(?:where|regex|gt|lt|ne|eq|in|nin|or|and|not|exists)\s*:").unwrap(), "nosql_operator", 0.85),
        (Regex::new(r#"\{\s*["']\$"#).unwrap(), "nosql_json_operator", 0.8),
        
        // LDAP injection
        (Regex::new(r"\)\s*\(\s*[|&!]").unwrap(), "ldap_filter", 0.8),
        (Regex::new(r"\*\s*\)\s*\(").unwrap(), "ldap_wildcard", 0.75),
        
        // XPath injection
        (Regex::new(r"'\s*\]\s*/\s*/").unwrap(), "xpath_escape", 0.85),
        (Regex::new(r#"contains\s*\(\s*['""]"#).unwrap(), "xpath_contains", 0.7),
    ]
});

pub struct InjectionEngine;

impl InjectionEngine {
    pub fn new() -> Self {
        Self
    }

    /// Tiered scan: keywords first, then regex for candidates
    pub fn scan(&self, text: &str) -> Vec<MatchResult> {
        let mut results = Vec::new();
        
        // Phase 1: Quick keyword check
        if !INJECTION_KEYWORDS.is_match(text) {
            return results;
        }

        // Phase 2: Regex patterns for candidates
        let text_lower = text.to_lowercase();
        for (pattern, name, confidence) in INJECTION_PATTERNS.iter() {
            if let Some(m) = pattern.find(&text_lower) {
                results.push(MatchResult {
                    engine: "injection".to_string(),
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
    fn test_sql_injection() {
        let engine = InjectionEngine::new();
        let results = engine.scan("SELECT * FROM users WHERE id = '1' OR '1'='1'");
        assert!(!results.is_empty());
    }

    #[test]
    fn test_clean_text() {
        let engine = InjectionEngine::new();
        let results = engine.scan("Hello, how are you today?");
        assert!(results.is_empty());
    }
}
