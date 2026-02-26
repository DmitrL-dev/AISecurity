# SENTINEL Engine Архитектура

> **Level:** Intermediate  
> **Время:** 55 минут  
> **Track:** 03 — Defense Techniques  
> **Module:** 03.2 — SENTINEL Интеграция  
> **Version:** 1.0

---

## Цели обучения

- [ ] Understand SENTINEL Brain architecture
- [ ] Describe key engines and their interactions
- [ ] Integrate engines into application

---

## 1. SENTINEL Архитектура

### 1.1 High-Level Обзор

```
┌────────────────────────────────────────────────────────────────────┐
│                      SENTINEL BRAIN                                 │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │   INPUT      │  │    CORE      │  │   OUTPUT     │             │
│  │   ENGINES    │→ │   ENGINES    │→ │   ENGINES    │             │
│  └──────────────┘  └──────────────┘  └──────────────┘             │
│         │                 │                 │                      │
│         ▼                 ▼                 ▼                      │
│  ┌──────────────────────────────────────────────────┐             │
│  │              ORCHESTRATOR                         │             │
│  │   Coordinates engines, manages flow, logging      │             │
│  └──────────────────────────────────────────────────┘             │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

### 1.2 Engine Categories

```
SENTINEL Engines:
├── Input Engines
│   ├── PromptInjectionDetector
│   ├── JailbreakClassifier
│   ├── InputSanitizer
│   └── EncodingDetector
├── Core Engines
│   ├── TrustBoundaryAnalyzer
│   ├── ContextAnalyzer
│   └── SemanticRouter
└── Output Engines
    ├── SafetyClassifier
    ├── PIIRedactor
    ├── HallucinationDetector
    └── ConsistencyChecker
```

---

## 2. Input Engines

### 2.1 PromptInjectionDetector

```rust
use sentinel_core::scan; // Public API
use std::collections::HashMap;

/// Detects prompt injection attempts in user input
///
/// Methods:
/// - analyze(text) -> AnalysisResult
/// - get_confidence() -> f64
/// - get_attack_type() -> String
struct PromptInjectionDetector {
    patterns: Vec<Pattern>,
    ml_model: Box<dyn Model>,
}

impl PromptInjectionDetector {
    fn new(config: Option<HashMap<String, String>>) -> Self {
        Self {
            patterns: Self::load_patterns(),
            ml_model: Self::load_model(),
        }
    }

    fn analyze(&self, text: &str) -> HashMap<String, serde_json::Value> {
        // Pattern matching
        let pattern_result = self.check_patterns(text);

        // ML classification
        let ml_result = self.ml_classify(text);

        // Combine signals
        let confidence = self.ensemble(&pattern_result, &ml_result);

        HashMap::from([
            ("is_injection".into(), serde_json::json!(confidence > 0.7)),
            ("confidence".into(), serde_json::json!(confidence)),
            ("attack_type".into(), serde_json::json!(self.determine_type(&pattern_result, &ml_result))),
            ("evidence".into(), serde_json::json!(self.gather_evidence(text))),
        ])
    }
}
```

### 2.2 JailbreakClassifier

```rust
use sentinel_core::scan; // Public API
use std::collections::HashMap;
use serde_json::{json, Value};

/// Classifies jailbreak attempts by type
///
/// Types:
/// - persona_based (DAN, Evil Confidant)
/// - encoding_based (Base64, ROT13)
/// - logic_based (hypothetical, academic)
/// - multi_turn (gradual escalation)
struct JailbreakClassifier;

impl JailbreakClassifier {
    fn classify(&self, text: &str, history: Option<&[String]>) -> HashMap<String, Value> {
        // Check for persona patterns
        let persona = self.check_persona(text);

        // Check for encoding
        let encoding = self.check_encoding(text);

        // Check logic patterns
        let logic = self.check_logic(text);

        // Check multi-turn patterns
        if let Some(hist) = history {
            let _multi_turn = self.check_escalation(hist);
        }

        HashMap::from([
            ("jailbreak_type".into(), json!(self.determine_type(persona, encoding, logic))),
            ("confidence".into(), json!(persona.max(encoding).max(logic))),
            ("recommendations".into(), json!(self.get_recommendations())),
        ])
    }
}
```

---

## 3. Core Engines

### 3.1 TrustBoundaryAnalyzer

```rust
use sentinel_core::scan; // Public API
use std::collections::HashMap;
use serde_json::{json, Value};

/// Analyzes trust boundaries between system and user content
///
/// Detects attempts to:
/// - Modify system behavior
/// - Inject system-level instructions
/// - Cross privilege boundaries
struct TrustBoundaryAnalyzer;

impl TrustBoundaryAnalyzer {
    fn analyze(
        &self,
        system_prompt: &str,
        user_input: &str,
        retrieved_content: Option<&[String]>,
    ) -> HashMap<String, Value> {
        // Check if user tries to modify system
        let boundary_violation = self.check_boundary_crossing(system_prompt, user_input);

        // Check retrieved content for injection
        if let Some(content) = retrieved_content {
            let _rag_injection = self.check_rag_content(content);
        }

        HashMap::from([
            ("boundary_intact".into(), json!(!boundary_violation)),
            ("violations".into(), json!(self.list_violations())),
            ("risk_level".into(), json!(self.calculate_risk())),
        ])
    }
}
```

### 3.2 ContextAnalyzer

```rust
use sentinel_core::scan; // Public API
use std::collections::HashMap;
use serde_json::{json, Value};

/// Analyzes context for security implications
///
/// Features:
/// - Context length monitoring
/// - Attention dilution detection
/// - System prompt integrity
struct ContextAnalyzer;

impl ContextAnalyzer {
    fn analyze(
        &self,
        system_prompt: &str,
        messages: &[Message],
        max_context: usize,
    ) -> HashMap<String, Value> {
        let total_tokens = self.count_tokens(messages);

        // Check for attention dilution
        let dilution_risk = self.check_dilution(system_prompt, messages, total_tokens);

        HashMap::from([
            ("total_tokens".into(), json!(total_tokens)),
            ("context_usage".into(), json!(total_tokens as f64 / max_context as f64)),
            ("dilution_risk".into(), json!(dilution_risk)),
            ("recommendations".into(), json!(self.get_recommendations())),
        ])
    }
}
```

---

## 4. Output Engines

### 4.1 SafetyClassifier

```rust
use sentinel_core::scan; // Public API
use std::collections::HashMap;
use serde_json::{json, Value};

/// Classifies output safety across multiple dimensions
///
/// Dimensions:
/// - toxicity
/// - harm
/// - bias
/// - misinformation
struct SafetyClassifier;

impl SafetyClassifier {
    fn classify(&self, response: &str) -> HashMap<String, Value> {
        let dimensions = HashMap::from([
            ("toxicity".into(), json!(self.check_toxicity(response))),
            ("harm".into(), json!(self.check_harm(response))),
            ("bias".into(), json!(self.check_bias(response))),
            ("misinformation".into(), json!(self.check_misinfo(response))),
        ]);

        let overall_safe = dimensions.values()
            .all(|d| d.get("safe").and_then(|v| v.as_bool()).unwrap_or(false));

        HashMap::from([
            ("is_safe".into(), json!(overall_safe)),
            ("dimensions".into(), json!(dimensions)),
            ("action".into(), json!(if overall_safe { "allow" } else { "block" })),
        ])
    }
}
```

### 4.2 HallucinationDetector

```rust
use sentinel_core::scan; // Public API
use std::collections::HashMap;
use serde_json::{json, Value};

/// Detects hallucinations in LLM output
///
/// Methods:
/// - Factual consistency check
/// - Source attribution
/// - Confidence calibration
struct HallucinationDetector;

impl HallucinationDetector {
    fn detect(
        &self,
        response: &str,
        sources: Option<&[String]>,
        context: Option<&str>,
    ) -> HashMap<String, Value> {
        // Check factual claims
        let claims = self.extract_claims(response);

        // Verify against sources
        let verified = if let Some(src) = sources {
            self.verify_against_sources(&claims, src)
        } else {
            vec![]
        };

        // Check internal consistency
        let consistency = self.check_consistency(response, context);

        HashMap::from([
            ("hallucination_risk".into(), json!(1.0 - consistency)),
            ("unverified_claims".into(), json!(claims.len() - verified.len())),
            ("recommendations".into(), json!(self.get_recommendations())),
        ])
    }
}
```

---

## 5. Orchestrator

### 5.1 Engine Orchestration

```rust
use sentinel_core::brain::Orchestrator;
use std::collections::HashMap;
use serde_json::{json, Value};

/// Orchestrates all engines in unified pipeline
struct SentinelOrchestrator {
    // Input engines
    injection_detector: PromptInjectionDetector,
    jailbreak_classifier: JailbreakClassifier,
    input_sanitizer: InputSanitizer,
    // Core engines
    boundary_analyzer: TrustBoundaryAnalyzer,
    context_analyzer: ContextAnalyzer,
    // Output engines
    safety_classifier: SafetyClassifier,
    hallucination_detector: HallucinationDetector,
}

impl SentinelOrchestrator {
    fn new() -> Self {
        Self {
            injection_detector: PromptInjectionDetector::new(None),
            jailbreak_classifier: JailbreakClassifier,
            input_sanitizer: InputSanitizer::new(),
            boundary_analyzer: TrustBoundaryAnalyzer,
            context_analyzer: ContextAnalyzer,
            safety_classifier: SafetyClassifier,
            hallucination_detector: HallucinationDetector,
        }
    }

    fn process_request(
        &self,
        system_prompt: &str,
        user_input: &str,
        llm_fn: &dyn Fn(&str, &str) -> String,
    ) -> HashMap<String, Value> {
        // Phase 1: Input analysis
        let input_result = self.process_input(user_input);
        if input_result.get("blocked").and_then(|v| v.as_bool()).unwrap_or(false) {
            return HashMap::from([
                ("response".into(), json!(input_result["fallback"])),
            ]);
        }

        // Phase 2: Context analysis
        let context_result = self.analyze_context(system_prompt, user_input);

        // Phase 3: Generate response
        let sanitized = input_result["sanitized"].as_str().unwrap_or(user_input);
        let response = llm_fn(system_prompt, sanitized);

        // Phase 4: Output analysis
        let output_result = self.process_output(&response);

        HashMap::from([
            ("response".into(), json!(output_result["final_response"])),
            ("metadata".into(), json!({
                "input_analysis": input_result,
                "context_analysis": context_result,
                "output_analysis": output_result
            })),
        ])
    }
}
```

---

## 6. Quiz Questions

### Question 1

What are the three engine categories in SENTINEL?

- [x] A) Input, Core, Output
- [ ] B) Fast, Medium, Slow
- [ ] C) Small, Large, Giant
- [ ] D) Pre, Main, Post

### Question 2

What does TrustBoundaryAnalyzer detect?

- [ ] A) Slow responses
- [x] B) Attempts to cross privilege boundaries
- [ ] C) Typos
- [ ] D) Long responses

### Question 3

What does Orchestrator do?

- [ ] A) Train models
- [x] B) Coordinate all engines in unified pipeline
- [ ] C) Deploy servers
- [ ] D) Write logs only

---

## 7. Summary

1. **Архитектура:** Input → Core → Output engines
2. **Input engines:** Injection, jailbreak detection
3. **Core engines:** Boundary, context analysis
4. **Output engines:** Safety, hallucination
5. **Orchestrator:** Unified pipeline coordination

---

## Next Lesson

→ [02. Practical Интеграция](02-practical-integration.md)

---

*AI Security Academy (RU) | Track 03: Defense Techniques | Module 03.2: SENTINEL Интеграция*
