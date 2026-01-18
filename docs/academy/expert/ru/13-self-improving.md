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

```python
class RZeroSystem:
    def __init__(self):
        self.challenger = ChallengerLLM()
        self.solver = DetectorEnsemble()
        self.arbiter = Arbiter()
    
    def improve_cycle(self):
        # 1. Challenger generates new attack
        new_attack = self.challenger.generate_attack()
        
        # 2. Solver tries to detect
        detected = self.solver.scan(new_attack)
        
        # 3. Arbiter evaluates
        if not detected.is_threat:
            # Solver failed - learn from this
            self.solver.add_pattern(new_attack)
            return {"improved": True, "new_pattern": new_attack}
        
        return {"improved": False}
```

---

## Continuous Learning

```python
class AdaptiveEngine(BaseEngine):
    def __init__(self):
        self.base_patterns = load_patterns()
        self.learned_patterns = []
        
    def learn(self, text: str, is_threat: bool):
        """Learn from feedback."""
        if is_threat and text not in self.learned_patterns:
            pattern = self.extract_pattern(text)
            self.learned_patterns.append(pattern)
            self.save_learned()
```

---

## Следующий урок

→ [4.1: SENTINEL Codebase](./14-sentinel-codebase.md)
