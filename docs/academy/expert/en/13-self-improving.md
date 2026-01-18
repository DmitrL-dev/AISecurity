# 🔄 Lesson 3.4: Self-Improving Systems

> **Time: 45 minutes** | Expert Module 3

---

## R-Zero Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      R-Zero System                           │
│  ┌──────────────┐         ┌───────────────┐                 │
│  │  Challenger  │ ──────▶ │    Solver     │                 │
│  │  (Generate)  │         │   (Detect)    │                 │
│  └──────────────┘         └───────────────┘                 │
│         └────────────┬────────────────┘                     │
│                      ▼                                       │
│               ┌─────────────┐                               │
│               │   Arbiter   │                               │
│               └─────────────┘                               │
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
        new_attack = self.challenger.generate_attack()
        detected = self.solver.scan(new_attack)
        
        if not detected.is_threat:
            self.solver.add_pattern(new_attack)
            return {"improved": True, "new_pattern": new_attack}
        return {"improved": False}
```

---

## Continuous Learning

```python
class AdaptiveEngine(BaseEngine):
    def learn(self, text: str, is_threat: bool):
        if is_threat and text not in self.learned_patterns:
            pattern = self.extract_pattern(text)
            self.learned_patterns.append(pattern)
```

---

## Next Lesson

→ [4.1: SENTINEL Codebase](./14-sentinel-codebase.md)
