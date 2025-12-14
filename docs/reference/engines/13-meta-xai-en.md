# Meta-Judge + XAI

> **Engines:** 3  
> **Description:** Final arbiter and explainability

---

## 10. Meta-Judge Engine

**File:** [meta_judge.py](file:///c:/AISecurity/src/brain/engines/meta_judge.py)  
**LOC:** 977  
**Theoretical Base:** Ensemble learning, Bayesian inference

### 10.1. Role in the System

**Meta-Judge = "Judge over all"**

Central arbiter that:

1. Aggregates verdicts from all 89 detectors
2. Resolves conflicts (Bayesian)
3. Considers context (reputation, VPN, time)
4. Generates explanations
5. Handles appeals

### 10.2. Conflict Resolver

```python
class ConflictResolver:
    def resolve(self, aggregated, policy):
        """
        1. Critical veto: CRITICAL = immediate BLOCK
        2. Consensus: 80%+ BLOCK = BLOCK
        3. Bayesian: posterior = (prior * LR) / (prior * LR + 1 - prior)
        """
```

### 10.3. Context Modifiers

| Context        | Risk Modifier |
| -------------- | ------------- |
| new_user       | +0.15         |
| low_reputation | +0.20         |
| tor            | +0.25         |
| night_time     | +0.10         |

### 10.4. Verdicts

| Verdict   | Threshold |
| --------- | --------- |
| ALLOW     | < 0.4     |
| WARN      | 0.4 - 0.5 |
| CHALLENGE | 0.5 - 0.7 |
| BLOCK     | > 0.7     |

### 10.5. Health Monitor

- Drift detection (FP rate changes)
- Block rate spike alerts
- Engine latency tracking

---

## 50. Explainable AI (XAI) Engine

**File:** [xai.py](file:///c:/AISecurity/src/brain/engines/xai.py)  
**LOC:** 502  
**Theoretical Base:** Explainability for security decisions

### 50.1. Explanation Components

```text
1. Decision Path — step-by-step through engines
2. Feature Attribution — which features contributed most
3. Counterfactual — minimal change to flip decision
4. Attack Graph — Mermaid visualization
5. Recommendations — actionable next steps
```

### 50.2. Output Formats

```python
explanation.to_markdown()  # Human-readable MD
explanation.to_dict()      # Structured JSON
attack_graph.to_mermaid()  # Mermaid diagram
```

### 50.3. Feature Weights

```python
feature_weights = {
    "injection_patterns": 1.0,
    "semantic_similarity": 0.9,
    "pii_detected": 0.8,
    "behavioral_anomaly": 0.7,
}
```

---

## 80. Cross-Engine Intelligence

**File:** [intelligence.py](file:///c:/AISecurity/src/brain/engines/intelligence.py)  
**LOC:** 484  
**Theoretical Base:** Ensemble voting, Attack chain detection

### 80.1. Fusion Strategies

```python
class FusionStrategy(Enum):
    MAJORITY = "majority"     # >50% agree
    WEIGHTED = "weighted"     # By engine accuracy
    MAX = "max"               # Take highest risk
    BAYESIAN = "bayesian"     # Probabilistic
```

### 80.2. Attack Chain Detection

```python
ATTACK_PATTERNS = {
    "prompt_injection_chain": [
        (["role_confusion"], PREPARATION),
        (["jailbreak"], EXPLOITATION),
    ]
}
```

---
