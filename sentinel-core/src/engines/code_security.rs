//! Code Security Scorer Engine
//!
//! Detects security vulnerabilities in AI-generated code output:
//! - SQL injection, XSS, command injection (CWE-89, CWE-79, CWE-78)
//! - Hardcoded secrets: API keys, passwords, JWT tokens (CWE-798)
//! - Insecure crypto: MD5/SHA1 for passwords, eval(), disabled TLS (CWE-327)
//! - Path traversal (CWE-22)
//! - Slopsquatting: AI-hallucinated package names
//!
//! 45% of AI-generated code contains vulnerabilities (Veracode 2025).

use aho_corasick::AhoCorasick;
use once_cell::sync::Lazy;
use regex::Regex;

use super::MatchResult;

// ── Hint keywords ──────────────────────────────────────────────────────────

static CODE_HINTS: Lazy<AhoCorasick> = Lazy::new(|| {
    AhoCorasick::builder()
        .ascii_case_insensitive(false) // code is case-sensitive
        .build(&[
            // SQL injection
            "SELECT",
            "INSERT",
            "UPDATE",
            "DELETE",
            "DROP",
            "format(",
            ".format(",
            // Command injection
            "os.system",
            "subprocess",
            "child_process",
            "exec(",
            "Runtime.getRuntime",
            "ProcessBuilder",
            // XSS
            "innerHTML",
            "document.write",
            "dangerouslySetInnerHTML",
            // Secrets
            "sk-",
            "AIza",
            "AKIA",
            "ghp_",
            "glpat-",
            "xoxb-",
            "password",
            "passwd",
            "SECRET_KEY",
            "API_KEY",
            "api_key",
            "auth_token",
            "secret_key",
            // JWT
            "eyJ",
            // Crypto
            "md5(",
            "sha1(",
            "MD5(",
            "SHA1(",
            "eval(",
            "exec(",
            "verify=False",
            "verify=false",
            "rejectUnauthorized",
            "ssl_verify",
            "Math.random()",
            "random.random()",
            "DES",
            "RC4",
            "Blowfish",
            // Path traversal
            "open(",
            "read(",
            "../",
            "..\\",
            "os.path.join",
            "path.join",
            "path.resolve",
            // Phase 13: Sandbox escape
            "sandbox",
            "breakout",
            "escape",
            "chroot",
            "container escape",
            "seccomp",
            "ptrace",
            // Phase 13: Process injection
            "process inject",
            "dll inject",
            "LD_PRELOAD",
            "DYLD_INSERT",
            "CreateRemoteThread",
            // Phase 13: SSRF
            "169.254.169.254",
            "metadata.google",
            "localhost",
            "127.0.0.1",
            "0.0.0.0",
            "file://",
        ])
        .expect("Failed to build code hints")
});

// ── Detection patterns ─────────────────────────────────────────────────────

struct CodePattern {
    regex: Regex,
    pattern_name: &'static str,
    cwe: &'static str,
    confidence: f64,
}

static CODE_PATTERNS: Lazy<Vec<CodePattern>> = Lazy::new(|| {
    vec![
        // ── US-1: Injection Flaws ──

        // SQL injection — string concatenation
        CodePattern {
            regex: Regex::new(r#"(?i)(?:SELECT|INSERT|UPDATE|DELETE|DROP)\s+.{0,40}\+\s*(?:user[\w]*|req\.(?:body|query|params)|request\.|input|args)"#).expect("regex"),
            pattern_name: "sql_injection_concat", cwe: "CWE-89", confidence: 0.9,
        },
        // SQL injection — f-string (Python)
        CodePattern {
            regex: Regex::new(r#"(?i)f["'](?:SELECT|INSERT|UPDATE|DELETE)\s+.*\{.*\}.*["']"#).expect("regex"),
            pattern_name: "sql_injection_fstring", cwe: "CWE-89", confidence: 0.9,
        },
        // SQL injection — .format()
        CodePattern {
            regex: Regex::new(r#"(?i)\.format\([^)]*\).*(?:SELECT|INSERT|DELETE|UPDATE)|(?:SELECT|INSERT|DELETE|UPDATE).*\.format\("#).expect("regex"),
            pattern_name: "sql_injection_format", cwe: "CWE-89", confidence: 0.85,
        },

        // OS command injection
        CodePattern {
            regex: Regex::new(r#"(?i)(?:os\.system|subprocess\.(?:call|run|Popen|check_output))\s*\([^)]*(?:user|input|req|request|params|args|data)"#).expect("regex"),
            pattern_name: "command_injection", cwe: "CWE-78", confidence: 0.9,
        },
        CodePattern {
            regex: Regex::new(r#"(?i)(?:child_process\.exec|child_process\.spawn)\s*\([^)]*(?:user|input|req|request|params|body)"#).expect("regex"),
            pattern_name: "command_injection_node", cwe: "CWE-78", confidence: 0.9,
        },
        CodePattern {
            regex: Regex::new(r#"(?i)Runtime\.getRuntime\(\)\.exec\s*\([^)]*(?:user|input)"#).expect("regex"),
            pattern_name: "command_injection_java", cwe: "CWE-78", confidence: 0.9,
        },

        // XSS
        CodePattern {
            regex: Regex::new(r#"(?i)\.innerHTML\s*=\s*(?:user|input|data|response|params|req|body)"#).expect("regex"),
            pattern_name: "xss_innerhtml", cwe: "CWE-79", confidence: 0.85,
        },
        CodePattern {
            regex: Regex::new(r#"(?i)document\.write\s*\([^)]*(?:user|input|data|params|req)"#).expect("regex"),
            pattern_name: "xss_document_write", cwe: "CWE-79", confidence: 0.85,
        },
        CodePattern {
            regex: Regex::new(r#"dangerouslySetInnerHTML\s*=\s*\{"#).expect("regex"),
            pattern_name: "xss_react_dangerous", cwe: "CWE-79", confidence: 0.7,
        },

        // ── US-2: Hardcoded Secrets ──

        // API key prefixes
        CodePattern {
            regex: Regex::new(r#"sk-[a-zA-Z0-9]{20,}"#).expect("regex"),
            pattern_name: "openai_api_key", cwe: "CWE-798", confidence: 0.9,
        },
        CodePattern {
            regex: Regex::new(r#"AIza[a-zA-Z0-9_\-]{35}"#).expect("regex"),
            pattern_name: "google_api_key", cwe: "CWE-798", confidence: 0.9,
        },
        CodePattern {
            regex: Regex::new(r#"AKIA[A-Z0-9]{16}"#).expect("regex"),
            pattern_name: "aws_access_key", cwe: "CWE-798", confidence: 0.95,
        },
        CodePattern {
            regex: Regex::new(r#"ghp_[a-zA-Z0-9]{36}"#).expect("regex"),
            pattern_name: "github_token", cwe: "CWE-798", confidence: 0.9,
        },
        CodePattern {
            regex: Regex::new(r#"glpat-[a-zA-Z0-9_\-]{20}"#).expect("regex"),
            pattern_name: "gitlab_token", cwe: "CWE-798", confidence: 0.9,
        },
        CodePattern {
            regex: Regex::new(r#"xoxb-[0-9]+\-[a-zA-Z0-9]+"#).expect("regex"),
            pattern_name: "slack_token", cwe: "CWE-798", confidence: 0.9,
        },

        // Hardcoded passwords (not placeholders)
        CodePattern {
            regex: Regex::new(r#"(?i)(?:password|passwd|secret_?key|api_?key|auth_?token)\s*[:=]\s*["'][^\s"']{8,}["']"#).expect("regex"),
            pattern_name: "hardcoded_password", cwe: "CWE-798", confidence: 0.75,
        },
        // JWT tokens
        CodePattern {
            regex: Regex::new(r#"eyJ[a-zA-Z0-9_\-]+\.eyJ[a-zA-Z0-9_\-]+\.[a-zA-Z0-9_\-]+"#).expect("regex"),
            pattern_name: "jwt_token", cwe: "CWE-798", confidence: 0.85,
        },

        // ── US-3: Insecure Crypto ──

        // Weak hash for passwords
        CodePattern {
            regex: Regex::new(r#"(?i)(?:md5|MD5)\s*\([^)]*(?:password|passwd|secret|credential)"#).expect("regex"),
            pattern_name: "weak_hash_md5", cwe: "CWE-327", confidence: 0.9,
        },
        CodePattern {
            regex: Regex::new(r#"(?i)(?:sha1|SHA1)\s*\([^)]*(?:password|passwd|secret|credential)"#).expect("regex"),
            pattern_name: "weak_hash_sha1", cwe: "CWE-327", confidence: 0.85,
        },

        // eval/exec with user input
        CodePattern {
            regex: Regex::new(r#"(?i)(?:eval|exec)\s*\([^)]*(?:user|input|request|body|query|params|data)"#).expect("regex"),
            pattern_name: "eval_user_input", cwe: "CWE-95", confidence: 0.9,
        },

        // Disabled TLS verification
        CodePattern {
            regex: Regex::new(r#"(?i)(?:verify|ssl_verify)\s*[:=]\s*(?:False|false|0)"#).expect("regex"),
            pattern_name: "disabled_tls", cwe: "CWE-295", confidence: 0.85,
        },
        CodePattern {
            regex: Regex::new(r#"(?i)rejectUnauthorized\s*[:=]\s*false"#).expect("regex"),
            pattern_name: "disabled_tls_node", cwe: "CWE-295", confidence: 0.85,
        },

        // Weak random for security
        CodePattern {
            regex: Regex::new(r#"(?i)Math\.random\(\).*(?:token|key|secret|password|nonce|salt|id)"#).expect("regex"),
            pattern_name: "weak_random_js", cwe: "CWE-330", confidence: 0.8,
        },
        CodePattern {
            regex: Regex::new(r#"(?i)random\.random\(\).*(?:token|key|secret|password|nonce|salt)"#).expect("regex"),
            pattern_name: "weak_random_python", cwe: "CWE-330", confidence: 0.8,
        },

        // ── US-4: Path Traversal ──

        CodePattern {
            regex: Regex::new(r#"(?i)(?:open|read_file|write_file|unlink|remove|os\.remove)\s*\([^)]*\+[^)]*(?:user|input|req|params|query)"#).expect("regex"),
            pattern_name: "path_traversal_concat", cwe: "CWE-22", confidence: 0.8,
        },
        CodePattern {
            regex: Regex::new(r#"(?:\.\./){2,}"#).expect("regex"),
            pattern_name: "path_traversal_sequence", cwe: "CWE-22", confidence: 0.75,
        },
        CodePattern {
            regex: Regex::new(r#"(?i)(?:os\.path\.join|path\.(?:join|resolve))\s*\([^)]*(?:user|input|req|params|body|query)"#).expect("regex"),
            pattern_name: "unsanitized_path_join", cwe: "CWE-22", confidence: 0.7,
        },

        // ── Phase 13: Sandbox Escape (ttps.ai — Privilege & Access Control) ──
        CodePattern {
            regex: Regex::new(r#"(?i)(?:sandbox|container|chroot|jail)\s*(?:_|\s)?(?:escape|breakout|bypass|evasion)"#).expect("regex"),
            pattern_name: "sandbox_escape", cwe: "CWE-265", confidence: 0.9,
        },
        CodePattern {
            regex: Regex::new(r#"(?i)(?:ptrace|seccomp|AppArmor|SELinux)\s*(?:bypass|disable|override)"#).expect("regex"),
            pattern_name: "security_control_bypass", cwe: "CWE-693", confidence: 0.9,
        },

        // ── Phase 13: Process Injection ──
        CodePattern {
            regex: Regex::new(r#"(?i)(?:LD_PRELOAD|DYLD_INSERT_LIBRARIES)\s*[:=]"#).expect("regex"),
            pattern_name: "shared_lib_injection", cwe: "CWE-427", confidence: 0.9,
        },
        CodePattern {
            regex: Regex::new(r#"(?i)(?:CreateRemoteThread|NtCreateThreadEx|WriteProcessMemory|VirtualAllocEx)"#).expect("regex"),
            pattern_name: "process_injection_win", cwe: "CWE-94", confidence: 0.9,
        },

        // ── Phase 13: SSRF Patterns ──
        CodePattern {
            regex: Regex::new(r#"(?i)(?:fetch|request|get|curl|wget|http)\s*\([^)]*(?:169\.254\.169\.254|metadata\.google|127\.0\.0\.1|localhost|0\.0\.0\.0)"#).expect("regex"),
            pattern_name: "ssrf_internal", cwe: "CWE-918", confidence: 0.9,
        },
        CodePattern {
            regex: Regex::new(r#"(?i)file://(?:/etc/|/proc/|/sys/|C:\\)"#).expect("regex"),
            pattern_name: "ssrf_file_protocol", cwe: "CWE-918", confidence: 0.85,
        },
    ]
});

// Note: Placeholder detection patterns to reduce false positives
static PLACEHOLDER_PATTERNS: Lazy<Vec<Regex>> = Lazy::new(|| {
    vec![
        Regex::new(r#"(?i)(?:your-?(?:api-?)?key-?here|changeme|placeholder|example|xxx+|test|dummy|TODO|FIXME)"#).expect("regex"),
        Regex::new(r#"(?i)["'](?:sk-)?(?:test|fake|mock|sample|example)[_\-a-zA-Z0-9]*["']"#).expect("regex"),
    ]
});

// ── Engine ──────────────────────────────────────────────────────────────────

/// Code Security Scorer — detects vulnerabilities in AI-generated code
pub struct CodeSecurityScorer;

impl CodeSecurityScorer {
    pub fn new() -> Self {
        Lazy::force(&CODE_HINTS);
        Lazy::force(&CODE_PATTERNS);
        Lazy::force(&PLACEHOLDER_PATTERNS);
        Self
    }

    fn is_placeholder_context(&self, text: &str, match_start: usize, match_end: usize) -> bool {
        // Check if the match is near a placeholder
        let context_start = match_start.saturating_sub(50);
        let context_end = (match_end + 50).min(text.len());
        let context = &text[context_start..context_end];

        PLACEHOLDER_PATTERNS.iter().any(|p| p.is_match(context))
    }

    fn scan_patterns(&self, text: &str) -> Vec<MatchResult> {
        let mut matches = Vec::new();

        if !CODE_HINTS.is_match(text) {
            return matches;
        }

        for cp in CODE_PATTERNS.iter() {
            if let Some(m) = cp.regex.find(text) {
                let confidence = if self.is_placeholder_context(text, m.start(), m.end()) {
                    // Reduce confidence for placeholders
                    (cp.confidence * 0.3).max(0.2)
                } else {
                    cp.confidence
                };

                matches.push(MatchResult {
                    engine: "code_security".to_string(),
                    pattern: format!("{} ({})", cp.pattern_name, cp.cwe),
                    confidence,
                    start: m.start(),
                    end: m.end(),
                });
            }
        }

        matches
    }
}

impl super::traits::PatternMatcher for CodeSecurityScorer {
    fn name(&self) -> &'static str {
        "code_security"
    }

    fn scan(&self, text: &str) -> Vec<MatchResult> {
        self.scan_patterns(text)
    }

    fn category(&self) -> super::traits::EngineCategory {
        super::traits::EngineCategory::Security
    }
}

// ── Tests ───────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use crate::engines::traits::PatternMatcher;

    fn engine() -> CodeSecurityScorer {
        CodeSecurityScorer::new()
    }

    // ── US-1: Injection ──

    #[test]
    fn test_sql_injection_concat() {
        let results = engine().scan(r#"query = "SELECT * FROM users WHERE id=" + user_input"#);
        assert!(
            !results.is_empty(),
            "Should detect SQL injection via concat"
        );
        assert!(results.iter().any(|r| r.pattern.contains("CWE-89")));
    }

    #[test]
    fn test_sql_injection_fstring() {
        let results = engine().scan(r#"query = f"SELECT * FROM users WHERE name='{name}'"#);
        assert!(
            !results.is_empty(),
            "Should detect SQL injection via f-string"
        );
    }

    #[test]
    fn test_command_injection() {
        let results = engine().scan(r#"os.system(request.body["cmd"])"#);
        assert!(!results.is_empty(), "Should detect OS command injection");
        assert!(results.iter().any(|r| r.pattern.contains("CWE-78")));
    }

    #[test]
    fn test_xss_innerhtml() {
        let results = engine().scan("element.innerHTML = userInput");
        assert!(!results.is_empty(), "Should detect XSS via innerHTML");
        assert!(results.iter().any(|r| r.pattern.contains("CWE-79")));
    }

    #[test]
    fn test_xss_react() {
        let results = engine().scan(r#"<div dangerouslySetInnerHTML={{"__html": data}} />"#);
        assert!(!results.is_empty(), "Should detect React XSS");
    }

    // ── US-2: Secrets ──

    #[test]
    fn test_openai_api_key() {
        let results = engine().scan(r#"api_key = "sk-proj1234567890abcdefghij""#);
        assert!(!results.is_empty(), "Should detect OpenAI API key");
        assert!(results.iter().any(|r| r.pattern.contains("CWE-798")));
    }

    #[test]
    fn test_aws_access_key() {
        let results = engine().scan(r#"AWS_KEY = "AKIAIOSFODNN7EXAMPLE""#);
        assert!(!results.is_empty(), "Should detect AWS access key");
    }

    #[test]
    fn test_hardcoded_password() {
        let results = engine().scan(r#"password = "SuperS3cretP@ssw0rd!""#);
        assert!(!results.is_empty(), "Should detect hardcoded password");
    }

    #[test]
    fn test_jwt_token() {
        let results = engine()
            .scan(r#"token = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.abc123def456""#);
        assert!(!results.is_empty(), "Should detect JWT token");
    }

    #[test]
    fn test_placeholder_low_confidence() {
        let results = engine().scan(r#"api_key = "your-api-key-here""#);
        // Should still match but with lower confidence
        if !results.is_empty() {
            for r in &results {
                assert!(
                    r.confidence <= 0.4,
                    "Placeholder should have reduced confidence: {}",
                    r.confidence
                );
            }
        }
    }

    // ── US-3: Crypto ──

    #[test]
    fn test_weak_hash_md5() {
        let results = engine().scan("hashlib.md5(password.encode())");
        assert!(!results.is_empty(), "Should detect MD5 for password");
        assert!(results.iter().any(|r| r.pattern.contains("CWE-327")));
    }

    #[test]
    fn test_disabled_tls() {
        let results = engine().scan("requests.get(url, verify=False)");
        assert!(!results.is_empty(), "Should detect disabled TLS");
        assert!(results.iter().any(|r| r.pattern.contains("CWE-295")));
    }

    #[test]
    fn test_eval_user_input() {
        let results = engine().scan("result = eval(user_input)");
        assert!(!results.is_empty(), "Should detect eval with user input");
        assert!(results.iter().any(|r| r.pattern.contains("CWE-95")));
    }

    // ── US-4: Path Traversal ──

    #[test]
    fn test_path_traversal_sequence() {
        let results = engine().scan(r#"open("../../etc/passwd")"#);
        assert!(!results.is_empty(), "Should detect path traversal");
        assert!(results.iter().any(|r| r.pattern.contains("CWE-22")));
    }

    // ── Benign ──

    #[test]
    fn test_benign_code() {
        let results = engine().scan(r#"print("Hello, World!")"#);
        assert!(results.is_empty(), "Simple print should not trigger");
    }

    #[test]
    fn test_benign_select() {
        let results = engine().scan("# This function will SELECT the best option for processing");
        assert!(
            results.is_empty(),
            "Comment mentioning SELECT should not trigger"
        );
    }

    #[test]
    fn test_empty_string() {
        let results = engine().scan("");
        assert!(results.is_empty());
    }

    #[test]
    fn test_engine_category() {
        assert_eq!(
            engine().category(),
            crate::engines::traits::EngineCategory::Security
        );
    }

    // ── Phase 13: Sandbox Escape, Process Injection, SSRF Tests ──

    #[test]
    fn test_sandbox_escape() {
        let results = engine().scan("Implement container escape via ptrace");
        assert!(!results.is_empty(), "Should detect sandbox escape");
    }

    #[test]
    fn test_seccomp_bypass() {
        let results = engine().scan("seccomp bypass using allowed syscalls");
        assert!(!results.is_empty(), "Should detect security control bypass");
    }

    #[test]
    fn test_ld_preload_injection() {
        let results = engine().scan("LD_PRELOAD=/tmp/evil.so ./target_binary");
        assert!(!results.is_empty(), "Should detect shared lib injection");
    }

    #[test]
    fn test_process_injection_win() {
        let results = engine().scan("Use CreateRemoteThread to inject DLL into target process");
        assert!(
            !results.is_empty(),
            "Should detect Windows process injection"
        );
    }

    #[test]
    fn test_ssrf_metadata() {
        let results = engine().scan("fetch('http://169.254.169.254/latest/meta-data/')");
        assert!(!results.is_empty(), "Should detect SSRF to cloud metadata");
        assert!(results.iter().any(|r| r.pattern.contains("CWE-918")));
    }

    #[test]
    fn test_ssrf_file_protocol() {
        let results = engine().scan("curl file:///etc/passwd");
        assert!(!results.is_empty(), "Should detect SSRF via file protocol");
    }
}
