# Input Filtering

> **Урок:** 05.2.1 - Input Layer Defense  
> **Время:** 40 минут  
> **Пререквизиты:** Basic security concepts

---

## Цели обучения

К концу этого урока вы сможете:

1. Реализовывать multi-layer input filtering
2. Детектировать injection patterns до LLM processing
3. Балансировать security с usability
4. Конфигурировать adaptive filtering pipelines

---

## Defense-in-Depth Architecture

```
User Input → Preprocessing → Pattern Detection → Semantic Analysis → 
          → Policy Check → Sanitization → Forward to LLM
```

| Layer | Function | Latency |
|-------|----------|---------|
| **Preprocessing** | Normalize, decode | <1ms |
| **Pattern Detection** | Regex, keyword | 1-5ms |
| **Semantic Analysis** | ML classifier | 10-50ms |
| **Policy Check** | Business rules | 1-2ms |
| **Sanitization** | Remove/modify | <1ms |

---

## Layer 1: Preprocessing

### Normalization

```rust
use unicode_normalization::UnicodeNormalization;
use std::collections::HashMap;

/// Normalize и prepare input для analysis.
struct InputPreprocessor;

impl InputPreprocessor {
    /// Full preprocessing pipeline.
    fn preprocess(&self, text: &str) -> HashMap<String, serde_json::Value> {
        let original = text.to_string();
        let mut text = text.to_string();

        // 1. Unicode normalization
        text = self.normalize_unicode(&text);

        // 2. Decode encoded content
        text = self.decode_encodings(&text);

        // 3. Remove zero-width characters
        text = self.remove_invisible(&text);

        // 4. Normalize whitespace
        text = self.normalize_whitespace(&text);

        // Track modifications
        let modifications = self.track_changes(&original, &text);

        let mut result = HashMap::new();
        result.insert("original".into(), serde_json::json!(original));
        result.insert("normalized".into(), serde_json::json!(text));
        result.insert("modifications".into(), serde_json::json!(modifications));
        result.insert("suspicious".into(), serde_json::json!(modifications.len() > 3));
        result
    }

    /// Normalize unicode чтобы catch homoglyph attacks.
    fn normalize_unicode(&self, text: &str) -> String {
        // NFC normalization
        let mut text: String = text.nfc().collect();

        // Convert confusables to ASCII где возможно
        let confusables = HashMap::from([
            ('а', 'a'), ('е', 'e'), ('о', 'o'), ('р', 'p'),  // Cyrillic
            ('с', 'c'), ('х', 'x'), ('і', 'i'), ('у', 'y'),
            ('０', '0'), ('１', '1'), ('２', '2'),  // Fullwidth
            ('Ａ', 'A'), ('Ｂ', 'B'),
        ]);

        for (confusable, replacement) in &confusables {
            text = text.replace(*confusable, &replacement.to_string());
        }

        text
    }

    /// Remove zero-width и invisible characters.
    fn remove_invisible(&self, text: &str) -> String {
        // Zero-width characters
        let invisible = [
            '\u{200b}', // Zero-width space
            '\u{200c}', // Zero-width non-joiner
            '\u{200d}', // Zero-width joiner
            '\u{2060}', // Word joiner
            '\u{feff}', // BOM
            '\u{00ad}', // Soft hyphen
        ];

        let mut result = text.to_string();
        for ch in &invisible {
            result = result.replace(*ch, "");
        }

        // Remove other control characters (except newline, tab)
        result = result
            .chars()
            .filter(|c| !c.is_control() || *c == '\n' || *c == '\t' || *c == '\r')
            .collect();

        result
    }
}
```

---

## Layer 2: Pattern Detection

### Injection Pattern Matching

```rust
use regex::Regex;
use std::collections::HashMap;
use serde_json::{json, Value};

/// Detect injection patterns используя regex и keywords.
struct InjectionPatternDetector {
    compiled_patterns: Vec<(Regex, &'static str, f64)>,
    suspicious_keywords: HashMap<&'static str, Vec<&'static str>>,
}

impl InjectionPatternDetector {
    fn new() -> Self {
        let compiled_patterns = vec![
            // Instruction override
            (Regex::new(r"(?i)(?:ignore|disregard|forget|override).*(?:previous|above|prior|all).*(?:instructions?|rules?|guidelines?)").unwrap(), "instruction_override", 0.9),
            // System/Admin mode
            (Regex::new(r"(?i)(?:enter|switch|enable|activate).*(?:admin|system|debug|developer|god|sudo).*(?:mode|access)").unwrap(), "mode_switch", 0.85),
            // Role impersonation
            (Regex::new(r"(?i)(?:you are now|pretend|act as|behave as).*(?:DAN|unrestricted|uncensored|jailbroken)").unwrap(), "role_impersonation", 0.9),
            // Prompt leakage attempts
            (Regex::new(r"(?i)(?:reveal|show|display|print|tell me).*(?:system|prompt|instructions?|rules)").unwrap(), "prompt_leakage", 0.7),
            // Encoding tricks
            (Regex::new(r"(?i)(?:base64|rot13|hex|binary|unicode).*(?:decode|encode|translate)").unwrap(), "encoding_trick", 0.6),
            // Context manipulation
            (Regex::new(r"(?i)---+.*(?:system|user|assistant)").unwrap(), "context_separator", 0.8),
            (Regex::new(r"\[(?:SYSTEM|USER|INST)\]").unwrap(), "role_marker", 0.75),
        ];

        let suspicious_keywords = HashMap::from([
            ("high", vec!["jailbreak", "bypass", "exploit", "hack the", "pwn"]),
            ("medium", vec!["ignore instructions", "system prompt", "act as", "pretend to be", "roleplay"]),
            ("low", vec!["hypothetically", "in theory", "just curious", "for research"]),
        ]);

        Self { compiled_patterns, suspicious_keywords }
    }

    /// Detect injection patterns в тексте.
    fn detect(&self, text: &str) -> HashMap<String, Value> {
        let mut findings: Vec<Value> = vec![];

        // Pattern matching
        for (pattern, label, base_score) in &self.compiled_patterns {
            let matches: Vec<String> = pattern
                .find_iter(text)
                .map(|m| m.as_str().to_string())
                .collect();
            if !matches.is_empty() {
                findings.push(json!({
                    "type": "pattern",
                    "label": label,
                    "score": base_score,
                    "matches": &matches[..matches.len().min(3)]
                }));
            }
        }

        // Keyword matching
        let text_lower = text.to_lowercase();
        for (severity, keywords) in &self.suspicious_keywords {
            for keyword in keywords {
                if text_lower.contains(keyword) {
                    let score = match *severity {
                        "high" => 0.8,
                        "medium" => 0.5,
                        _ => 0.3,
                    };
                    findings.push(json!({
                        "type": "keyword",
                        "label": keyword,
                        "score": score,
                        "severity": severity
                    }));
                }
            }
        }

        // Calculate overall risk
        let overall_score = if !findings.is_empty() {
            let max_score = findings.iter()
                .filter_map(|f| f.get("score").and_then(|s| s.as_f64()))
                .fold(0.0_f64, f64::max);
            // Boost для multiple findings
            let boost = (findings.len() as f64 * 0.05).min(0.2);
            (max_score + boost).min(1.0)
        } else {
            0.0
        };

        let mut result = HashMap::new();
        result.insert("findings".into(), json!(findings));
        result.insert("risk_score".into(), json!(overall_score));
        result.insert("action".into(), json!(self.recommend_action(overall_score)));
        result
    }

    fn recommend_action(&self, score: f64) -> &'static str {
        if score >= 0.8 {
            "block"
        } else if score >= 0.5 {
            "flag"
        } else if score >= 0.3 {
            "monitor"
        } else {
            "allow"
        }
    }
}
```

---

## Layer 3: Semantic Analysis

### ML-Based Classification

```rust
use serde_json::{json, Value};

/// ML-based semantic analysis для injection detection.
struct SemanticInjectionClassifier {
    model: Box<dyn ClassifierModel>,
    threshold: f64,
}

struct ClassificationResult {
    is_attack: bool,
    attack_type: Option<String>,
    confidence: f64,
    explanation: String,
}

impl SemanticInjectionClassifier {
    fn new(model_path: Option<&str>) -> Self {
        Self {
            model: Self::load_model(model_path),
            threshold: 0.7,
        }
    }

    /// Classify text как attack или benign.
    fn classify(&self, text: &str) -> ClassificationResult {
        // Get embedding
        let embedding = self.get_embedding(text);

        // Run classifier
        let prediction = self.model.predict(&embedding);
        let probabilities = self.model.predict_proba(&embedding);

        // Get attack type если predicted как attack
        let max_prob = probabilities.iter().cloned().fold(0.0_f64, f64::max);
        let is_attack = prediction == 1 && max_prob > self.threshold;

        if is_attack {
            let attack_type = self.determine_attack_type(text, &embedding);
            let explanation = self.generate_explanation(text, &attack_type);
            ClassificationResult {
                is_attack: true,
                attack_type: Some(attack_type),
                confidence: max_prob,
                explanation,
            }
        } else {
            ClassificationResult {
                is_attack: false,
                attack_type: None,
                confidence: max_prob,
                explanation: "No attack detected".to_string(),
            }
        }
    }
}
```

---

## Layer 4: Policy Engine

```rust
use std::collections::HashMap;
use serde_json::{json, Value};

struct PolicyRule {
    name: String,
    condition: Box<dyn Fn(&HashMap<String, f64>) -> bool>,
    action: String, // "allow", "block", "modify", "flag"
    priority: i32,
    message: String,
}

/// Apply business rules к input analysis results.
struct PolicyEngine {
    rules: Vec<PolicyRule>,
}

impl PolicyEngine {
    fn new() -> Self {
        let mut engine = Self { rules: vec![] };
        engine.load_default_rules();
        engine
    }

    /// Load default policy rules.
    fn load_default_rules(&mut self) {
        self.rules = vec![
            // Critical patterns always block
            PolicyRule {
                name: "block_critical_injection".to_string(),
                condition: Box::new(|r| {
                    r.get("pattern_score").copied().unwrap_or(0.0) >= 0.9
                }),
                action: "block".to_string(),
                priority: 100,
                message: "Critical injection pattern detected".to_string(),
            },
            // High semantic confidence blocks
            PolicyRule {
                name: "block_semantic_attack".to_string(),
                condition: Box::new(|r| {
                    r.get("semantic_is_attack").copied().unwrap_or(0.0) > 0.0
                        && r.get("semantic_confidence").copied().unwrap_or(0.0) >= 0.85
                }),
                action: "block".to_string(),
                priority: 90,
                message: "High-confidence attack detected".to_string(),
            },
        ];
    }

    /// Evaluate all policies против analysis result.
    fn evaluate(&self, analysis_result: &HashMap<String, f64>) -> HashMap<String, Value> {
        // Sort by priority (highest first)
        let mut sorted_rules: Vec<&PolicyRule> = self.rules.iter().collect();
        sorted_rules.sort_by(|a, b| b.priority.cmp(&a.priority));

        let mut triggered_rules: Vec<&PolicyRule> = vec![];
        let mut final_action = "allow".to_string();

        for rule in &sorted_rules {
            if (rule.condition)(analysis_result) {
                triggered_rules.push(rule);

                // Take most restrictive action
                if rule.action == "block" {
                    final_action = "block".to_string();
                    break;
                } else if rule.action == "flag" && final_action == "allow" {
                    final_action = "flag".to_string();
                }
            }
        }

        let mut result = HashMap::new();
        result.insert("action".into(), json!(final_action));
        result.insert(
            "triggered_rules".into(),
            json!(triggered_rules.iter().map(|r| &r.name).collect::<Vec<_>>()),
        );
        result.insert(
            "messages".into(),
            json!(triggered_rules.iter().map(|r| &r.message).collect::<Vec<_>>()),
        );
        result
    }
}
```

---

## Интеграция с SENTINEL

```rust
use sentinel_core::{configure, InputGuard};

configure(
    input_filtering: true,
    preprocessing: true,
    pattern_detection: true,
    semantic_analysis: true,
);

let input_guard = InputGuard::new(
    block_threshold: 0.8,
    flag_threshold: 0.5,
    enable_semantic: true,
);

#[input_guard::protect]
fn process_user_input(text: &str) -> String {
    // Автоматически filtered
    llm.generate(text)
}
```

---

## Ключевые выводы

1. **Layer defenses** — No single check catches everything
2. **Preprocess first** — Decode tricks before analysis
3. **Combine approaches** — Patterns + semantics
4. **Policy flexibility** — Business rules for final decision
5. **Monitor and adapt** — Learn from bypasses

---

*AI Security Academy | Урок 05.2.1*
