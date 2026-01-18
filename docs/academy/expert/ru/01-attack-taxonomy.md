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

```python
class AttackSurface:
    """Model AI system attack surface."""
    
    vectors = {
        "input": ["user_prompt", "rag_documents", "tool_outputs"],
        "model": ["weights", "training_data", "inference"],
        "system": ["tools", "memory", "permissions"],
        "output": ["response", "actions", "side_effects"]
    }
    
    def enumerate(self, target: AISystem) -> List[AttackVector]:
        vectors = []
        for category, items in self.vectors.items():
            for item in items:
                if target.exposes(item):
                    vectors.append(AttackVector(category, item))
        return vectors
```

---

## Следующий урок

→ [1.2: Detection Theory](./02-detection-theory.md)
