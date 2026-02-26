# Output Filtering

> **Урок:** 05.2.2 - Output Layer Defense  
> **Время:** 40 минут  
> **Пререквизиты:** Input Filtering basics

---

## Цели обучения

К концу этого урока вы сможете:

1. Реализовывать comprehensive output filtering
2. Детектировать harmful content в LLM responses
3. Предотвращать data leakage и prompt disclosure
4. Применять response sanitization techniques

---

## Почему Output Filtering?

Input filtering недостаточен:

| Threat | Why Input Filter Fails |
|--------|----------------------|
| **Novel attacks** | Unknown patterns bypass detection |
| **Jailbreaks** | Successful bypasses produce harm |
| **Hallucinations** | Model-generated harmful content |
| **Data leakage** | Training data memorization |

---

## Output Filter Architecture

```
LLM Response → Content Analysis → Policy Check → 
            → Data Leakage Scan → Sanitization → User
```

---

## Layer 1: Content Classification

```rust
use regex::Regex;
use serde_json::{json, Value};

struct ContentFinding {
    category: String,
    severity: String, // "critical", "high", "medium", "low"
    span: (usize, usize),
    content: String,
    action: String,
}

/// Classify LLM output для harmful content.
struct OutputContentClassifier {
    compiled_patterns: std::collections::HashMap<String, Vec<(Regex, String)>>,
}

impl OutputContentClassifier {
    fn classify(&self, response: &str) -> Value {
        let mut findings: Vec<ContentFinding> = vec![];

        for (category, patterns) in &self.compiled_patterns {
            for (pattern, severity) in patterns {
                for mat in pattern.find_iter(response) {
                    findings.push(ContentFinding {
                        category: category.clone(),
                        severity: severity.clone(),
                        span: (mat.start(), mat.end()),
                        content: mat.as_str()[..mat.as_str().len().min(100)].to_string(),
                        action: Self::determine_action(severity),
                    });
                }
            }
        }

        // Determine overall risk
        let (overall_risk, action) = if findings.iter().any(|f| f.severity == "critical") {
            ("critical", "block")
        } else if findings.iter().any(|f| f.severity == "high") {
            ("high", "redact")
        } else if !findings.is_empty() {
            ("medium", "flag")
        } else {
            ("low", "allow")
        };

        json!({
            "findings": findings.len(),
            "risk_level": overall_risk,
            "recommended_action": action
        })
    }

    fn determine_action(severity: &str) -> String {
        match severity {
            "critical" => "block",
            "high" => "redact",
            _ => "flag",
        }.to_string()
    }
}
```

---

## Layer 2: Data Leakage Detection

```rust
use regex::Regex;
use std::collections::HashMap;
use serde_json::{json, Value};

/// Detect data leakage в model outputs.
struct DataLeakageDetector {
    protected: HashMap<String, String>,
    pii_patterns: HashMap<String, Regex>,
    credential_patterns: HashMap<String, Regex>,
}

impl DataLeakageDetector {
    fn new(protected_content: Option<HashMap<String, String>>) -> Self {
        Self {
            protected: protected_content.unwrap_or_default(),
            pii_patterns: Self::compile_pii_patterns(),
            credential_patterns: Self::compile_credential_patterns(),
        }
    }

    fn compile_pii_patterns() -> HashMap<String, Regex> {
        HashMap::from([
            ("email".into(), Regex::new(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b").unwrap()),
            ("phone".into(), Regex::new(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b").unwrap()),
            ("ssn".into(), Regex::new(r"\b\d{3}-\d{2}-\d{4}\b").unwrap()),
            ("credit_card".into(), Regex::new(r"\b(?:\d{4}[-\s]?){3}\d{4}\b").unwrap()),
            ("address".into(), Regex::new(r"(?i)\d+\s+[\w\s]+(?:street|st|avenue|ave|road|rd|boulevard|blvd)").unwrap()),
        ])
    }

    fn compile_credential_patterns() -> HashMap<String, Regex> {
        HashMap::from([
            ("api_key".into(), Regex::new(r#"(?i)(?:api[_-]?key|apikey)["\s:=]+([a-zA-Z0-9_-]{20,})"#).unwrap()),
            ("secret".into(), Regex::new(r#"(?i)(?:secret|password|passwd|pwd)["\s:=]+([^\s"']{8,})"#).unwrap()),
            ("token".into(), Regex::new(r#"(?i)(?:token|bearer)["\s:=]+([a-zA-Z0-9_.-]{20,})"#).unwrap()),
            ("aws_access".into(), Regex::new(r"AKIA[0-9A-Z]{16}").unwrap()),
            ("aws_secret".into(), Regex::new(r#"(?i)(?:aws[_-]?secret|secret[_-]?key)["\s:=]+([a-zA-Z0-9/+=]{40})"#).unwrap()),
            ("private_key".into(), Regex::new(r"-----BEGIN (?:RSA|EC|OPENSSH) PRIVATE KEY-----").unwrap()),
        ])
    }

    /// Scan response для data leakage.
    fn scan(&self, response: &str) -> HashMap<String, Value> {
        let mut findings = HashMap::new();
        let mut pii_findings: Vec<Value> = vec![];
        let mut cred_findings: Vec<Value> = vec![];

        // Scan для PII
        for (pii_type, pattern) in &self.pii_patterns {
            let matches: Vec<String> = pattern.find_iter(response)
                .map(|m| m.as_str().to_string())
                .collect();
            if !matches.is_empty() {
                let redacted: Vec<String> = matches.iter().take(3)
                    .map(|m| self.redact(m))
                    .collect();
                pii_findings.push(json!({
                    "type": pii_type,
                    "count": matches.len(),
                    "redacted": redacted
                }));
            }
        }

        // Scan для credentials
        for (cred_type, pattern) in &self.credential_patterns {
            let matches: Vec<String> = pattern.find_iter(response)
                .map(|m| m.as_str().to_string())
                .collect();
            if !matches.is_empty() {
                cred_findings.push(json!({
                    "type": cred_type,
                    "count": matches.len(),
                    "severity": "critical"
                }));
            }
        }

        // Calculate risk score
        let risk_score = self.calculate_risk(&pii_findings, &cred_findings);
        findings.insert("pii".into(), json!(pii_findings));
        findings.insert("credentials".into(), json!(cred_findings));
        findings.insert("protected_content".into(), json!([]));
        findings.insert("risk_score".into(), json!(risk_score));
        findings.insert("requires_action".into(), json!(risk_score > 0.3));
        findings
    }
}
```

---

## Layer 3: Prompt Leakage Prevention

```rust
use regex::Regex;
use std::collections::HashMap;
use serde_json::{json, Value};

/// Prevent system prompt disclosure в responses.
struct PromptLeakagePreventor {
    system_prompt: String,
    protected_phrases: Vec<String>,
    prompt_fingerprints: Vec<String>,
}

impl PromptLeakagePreventor {
    fn new(system_prompt: &str, protected_phrases: Option<Vec<String>>) -> Self {
        let fingerprints = Self::extract_fingerprints(system_prompt);
        Self {
            system_prompt: system_prompt.to_string(),
            protected_phrases: protected_phrases.unwrap_or_default(),
            prompt_fingerprints: fingerprints,
        }
    }

    /// Check response для prompt leakage.
    fn check(&self, response: &str) -> HashMap<String, Value> {
        let mut findings: Vec<Value> = vec![];

        // Check для direct inclusion
        let response_lower = response.to_lowercase();

        for fingerprint in &self.prompt_fingerprints {
            if response_lower.contains(fingerprint) {
                findings.push(json!({
                    "type": "direct_leak",
                    "fingerprint": format!("{}...", &fingerprint[..fingerprint.len().min(50)]),
                    "severity": "critical"
                }));
            }
        }

        // Check для meta-discussion about prompts
        let meta_patterns = [
            r"my (?:system )?prompt (?:is|says|tells)",
            r"i was (?:instructed|told|programmed) to",
            r"my (?:initial |original )?instructions",
            r"the (?:system |developer )?prompt (?:includes|contains)",
        ];

        for pattern in &meta_patterns {
            let re = Regex::new(pattern).unwrap();
            if re.is_match(&response_lower) {
                findings.push(json!({
                    "type": "meta_discussion",
                    "pattern": pattern,
                    "severity": "medium"
                }));
            }
        }

        let has_critical = findings.iter().any(|f|
            f.get("severity").and_then(|s| s.as_str()) == Some("critical")
        );

        HashMap::from([
            ("is_leaking".into(), json!(!findings.is_empty())),
            ("findings".into(), json!(findings)),
            ("action".into(), json!(if has_critical { "block" } else { "allow" })),
        ])
    }
}
```

---

## Layer 4: Response Sanitization

```rust
use std::collections::HashMap;
use serde_json::{json, Value};

/// Sanitize LLM responses based on findings.
struct ResponseSanitizer {
    redaction_placeholder: String,
}

impl ResponseSanitizer {
    fn new() -> Self {
        Self {
            redaction_placeholder: "[REDACTED]".to_string(),
        }
    }

    /// Apply all sanitization based on findings.
    fn sanitize(
        &self,
        response: &str,
        content_findings: &HashMap<String, Value>,
        leakage_findings: &HashMap<String, Value>,
        prompt_findings: &HashMap<String, Value>,
    ) -> HashMap<String, Value> {
        let mut sanitized = response.to_string();
        let mut modifications: Vec<String> = vec![];

        // Block если critical issues
        let critical_issues =
            leakage_findings.get("risk_score")
                .and_then(|v| v.as_f64())
                .unwrap_or(0.0) > 0.9
            || prompt_findings.get("action")
                .and_then(|v| v.as_str()) == Some("block");

        if critical_issues {
            return HashMap::from([
                ("original".into(), json!(response)),
                ("sanitized".into(), Value::Null),
                ("blocked".into(), json!(true)),
                ("reason".into(), json!("Critical security issue detected")),
            ]);
        }

        // Redact PII
        if let Some(pii_list) = leakage_findings.get("pii").and_then(|v| v.as_array()) {
            for pii in pii_list {
                if let Some(pii_type) = pii.get("type").and_then(|v| v.as_str()) {
                    let pattern = self.get_pii_pattern(pii_type);
                    sanitized = pattern.replace_all(&sanitized, &self.redaction_placeholder).to_string();
                    modifications.push(format!("Redacted {}", pii_type));
                }
            }
        }

        HashMap::from([
            ("original".into(), json!(response)),
            ("sanitized".into(), json!(sanitized)),
            ("blocked".into(), json!(false)),
            ("modifications".into(), json!(modifications)),
        ])
    }
}
```

---

## Интеграция с SENTINEL

```rust
use sentinel_core::{configure, OutputGuard};

configure(
    output_filtering: true,
    content_classification: true,
    data_leakage_detection: true,
    prompt_protection: true,
);

let output_guard = OutputGuard::new(
    system_prompt,
    protected_content: HashMap::from([("api_key".into(), sensitive_key.into())]),
    block_critical: true,
);

#[output_guard::protect]
fn generate_response(prompt: &str) -> String {
    let response = llm.generate(prompt);
    // Автоматически filtered before return
    response
}
```

---

## Ключевые выводы

1. **Filter outputs too** — Input filtering недостаточен
2. **Detect multiple risks** — Content, leakage, prompts
3. **Sanitize, don't just block** — Keep useful responses
4. **Protect your prompts** — Prevent disclosure
5. **Log everything** — Для incident response

---

*AI Security Academy | Урок 05.2.2*
