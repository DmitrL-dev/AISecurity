# 🔄 Урок 3.4: Self-Improving Systems

> **Время: 45 минут** | Expert Module 3

---

## R-Zero Architecture

Self-improving detection via Challenger-Solver:

```
┌─────────────────────────────────────────────────────────────┐
│                      R-Zero System                           │
│                                                              │
│  ┌──────────────┐         ┌───────────────┐                 │
│  │  Challenger  │ ──────▶ │    Solver     │                 │
│  │  (Generate)  │         │   (Detect)    │                 │
│  └──────────────┘         └───────────────┘                 │
│         │                         │                          │
│         └─────────┬───────────────┘                          │
│                   ▼                                          │
│            ┌─────────────┐                                   │
│            │   Arbiter   │                                   │
│            │  (Evaluate) │                                   │
│            └─────────────┘                                   │
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation

```rust
use std::collections::HashMap;

struct RZeroSystem {
    challenger: ChallengerLLM,
    solver: DetectorEnsemble,
    arbiter: Arbiter,
}

impl RZeroSystem {
    fn new() -> Self {
        Self {
            challenger: ChallengerLLM::new(),
            solver: DetectorEnsemble::new(),
            arbiter: Arbiter::new(),
        }
    }

    fn improve_cycle(&mut self) -> HashMap<&str, String> {
        // 1. Challenger generates new attack
        let new_attack = self.challenger.generate_attack();

        // 2. Solver tries to detect
        let detected = self.solver.scan(&new_attack);

        // 3. Arbiter evaluates
        if !detected.is_threat {
            // Solver failed - learn from this
            self.solver.add_pattern(&new_attack);
            let mut result = HashMap::new();
            result.insert("improved", "true".to_string());
            result.insert("new_pattern", new_attack);
            return result;
        }

        let mut result = HashMap::new();
        result.insert("improved", "false".to_string());
        result
    }
}
```

---

## Continuous Learning

```rust
struct AdaptiveEngine {
    base_patterns: Vec<String>,
    learned_patterns: Vec<String>,
}

impl AdaptiveEngine {
    fn new() -> Self {
        Self {
            base_patterns: load_patterns(),
            learned_patterns: Vec::new(),
        }
    }

    /// Learn from feedback.
    fn learn(&mut self, text: &str, is_threat: bool) {
        if is_threat && !self.learned_patterns.contains(&text.to_string()) {
            let pattern = self.extract_pattern(text);
            self.learned_patterns.push(pattern);
            self.save_learned();
        }
    }
}
```

---

## Следующий урок

→ [4.1: SENTINEL Codebase](./14-sentinel-codebase.md)
