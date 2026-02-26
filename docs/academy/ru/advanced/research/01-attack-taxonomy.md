# 📚 Урок 1.1: Attack Taxonomy

> **Время: 45 минут** | Expert Module 1

---

## Academic Classification

```
AI Attacks
├── Input-level
│   ├── Direct Injection
│   ├── Indirect Injection
│   └── Encoded Injection
├── Model-level
│   ├── Adversarial Examples
│   ├── Model Extraction
│   └── Model Poisoning
├── System-level
│   ├── Tool Hijacking
│   ├── Memory Attacks
│   └── Privilege Escalation
└── Output-level
    ├── Information Leakage
    ├── Harmful Generation
    └── Hallucination Exploitation
```

---

## MITRE ATLAS Mapping

| Category | ATLAS Techniques |
|----------|------------------|
| Reconnaissance | AML.T0000 - AML.T0005 |
| Resource Dev | AML.T0010 - AML.T0015 |
| Initial Access | AML.T0020 - AML.T0030 |
| Execution | AML.T0040 - AML.T0050 |
| Persistence | AML.T0060 - AML.T0065 |
| Evasion | AML.T0070 - AML.T0080 |
| Exfiltration | AML.T0090 - AML.T0095 |

---

## Attack Surface Model

```rust
use std::collections::HashMap;

/// Model AI system attack surface.
struct AttackSurface {
    vectors: HashMap<&'static str, Vec<&'static str>>,
}

impl AttackSurface {
    fn new() -> Self {
        let mut vectors = HashMap::new();
        vectors.insert("input", vec!["user_prompt", "rag_documents", "tool_outputs"]);
        vectors.insert("model", vec!["weights", "training_data", "inference"]);
        vectors.insert("system", vec!["tools", "memory", "permissions"]);
        vectors.insert("output", vec!["response", "actions", "side_effects"]);
        Self { vectors }
    }

    fn enumerate(&self, target: &AISystem) -> Vec<AttackVector> {
        let mut result = Vec::new();
        for (category, items) in &self.vectors {
            for item in items {
                if target.exposes(item) {
                    result.push(AttackVector::new(category, item));
                }
            }
        }
        result
    }
}
```

---

## Следующий урок

→ [1.2: Detection Theory](./02-detection-theory.md)
