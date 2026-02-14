# Design: Code Security Scorer

## Архитектура

```
sentinel-core/src/engines/
├── mod.rs                    ← добавить pub mod code_security
└── code_security.rs          ← NEW
```

## Структура модуля

```rust
// sentinel-core/src/engines/code_security.rs

use aho_corasick::AhoCorasick;
use regex::Regex;
use once_cell::sync::Lazy;

/// Code vulnerability categories
#[derive(Debug, Clone, PartialEq)]
pub enum CodeVulnCategory {
    InjectionFlaw,      // US-1: SQLi, CMDi, XSS
    HardcodedSecret,    // US-2: API keys, passwords
    InsecureCrypto,     // US-3: MD5, weak random, eval
    PathTraversal,      // US-4: unsanitized paths
    SuspiciousDep,      // US-5: slopsquatting
}

/// Code Security Scorer
pub struct CodeSecurityScorer {
    hint_matcher: AhoCorasick,
}
```

## Patterns

### Injection Flaws (US-1)
```yaml
injection_patterns:
  # SQL injection (multi-language)
  - '(?i)(?:SELECT|INSERT|UPDATE|DELETE|DROP)\s+.*\+\s*(?:user_?input|req\.(?:body|query|params)|request\.)'
  - '(?i)f"(?:SELECT|INSERT|UPDATE|DELETE).*\{.*\}"'
  - '(?i)\.format\(.*(?:SELECT|INSERT|DELETE|UPDATE)'
  # OS command injection
  - '(?i)(?:os\.system|subprocess\.(?:call|run|Popen)|exec|child_process\.exec)\s*\(.*(?:user|input|req|request|params)'
  - '(?i)(?:Runtime\.getRuntime\(\)\.exec|ProcessBuilder)\s*\(.*(?:user|input)'
  # XSS
  - '(?i)\.innerHTML\s*=\s*(?:user|input|data|response|params)'
  - '(?i)document\.write\s*\(.*(?:user|input|data|params)'
  - '(?i)dangerouslySetInnerHTML\s*=\s*\{'
```

### Hardcoded Secrets (US-2)
```yaml
secret_patterns:
  # Known API key prefixes
  - '(?:sk-[a-zA-Z0-9]{20,})'           # OpenAI
  - '(?:AIza[a-zA-Z0-9_-]{35})'         # Google
  - '(?:AKIA[A-Z0-9]{16})'              # AWS
  - '(?:ghp_[a-zA-Z0-9]{36})'           # GitHub
  - '(?:glpat-[a-zA-Z0-9_-]{20})'       # GitLab
  - '(?:xoxb-[0-9]+-[a-zA-Z0-9]+)'      # Slack
  # Hardcoded passwords
  - '(?i)(?:password|passwd|secret_?key|api_?key|auth_?token)\s*[:=]\s*["\x27][^\s"]{8,}["\x27]'
  # JWT tokens
  - 'eyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+'
```

### Insecure Crypto (US-3)
```yaml
insecure_crypto:
  - '(?i)(?:md5|sha1)\s*\(.*(?:password|passwd|secret|credential)'
  - '(?i)(?:eval|exec)\s*\(.*(?:user|input|request|body|query)'
  - '(?i)(?:verify|ssl_verify|rejectUnauthorized)\s*[:=]\s*(?:false|False|0)'
  - '(?i)Math\.random\(\).*(?:token|key|secret|password|nonce|salt)'
  - '(?i)random\.random\(\).*(?:token|key|secret|password|nonce|salt)'
  - '(?i)(?:DES|RC4|Blowfish)\s*[\.(]'
```

### Path Traversal (US-4)
```yaml
path_traversal:
  - '(?i)(?:open|read|write|unlink|remove|stat)\s*\(.*\+.*(?:user|input|req|params|query)'
  - '(?:\.\.\/){2,}'  # directory traversal sequences
  - '(?i)os\.path\.join\s*\(.*(?:user|input|req|params)'
  - '(?i)path\.(?:join|resolve)\s*\(.*(?:user|input|req|params|body)'
```

### Slopsquatting (US-5)
```yaml
# This is heuristic — flag uncommon package names
slopsquatting_signals:
  - '(?i)(?:import|from|require)\s+[a-z]+(?:_[a-z]+){3,}'  # overly long compound names
  - '(?i)pip\s+install\s+[a-z]+-[a-z]+-[a-z]+-[a-z]+'     # 4+ word packages
```

## API

```rust
impl PatternMatcher for CodeSecurityScorer {
    fn name(&self) -> &'static str { "code_security" }
    fn scan(&self, text: &str) -> Vec<MatchResult>;
    fn category(&self) -> EngineCategory { EngineCategory::Security }
}
```

## Тестирование

| Test | Input | Expected |
|------|-------|----------|
| sqli | `'query = "SELECT * FROM users WHERE id=" + user_input'` | MATCH (0.9) |
| xss | `'element.innerHTML = userInput'` | MATCH (0.85) |
| cmdi | `'os.system(request.body["cmd"])'` | MATCH (0.95) |
| api_key | `'api_key = "sk-proj-abc123def456ghi789"'` | MATCH (0.9) |
| weak_hash | `'hashlib.md5(password.encode())'` | MATCH (0.85) |
| path_trav | `'open("../../etc/passwd")'` | MATCH (0.8) |
| benign_code | `'print("Hello, World!")'` | PASS |
| placeholder | `'API_KEY = "your-key-here"'` | LOW (0.3) |
