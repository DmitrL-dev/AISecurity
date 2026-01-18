# 🎯 Урок 5.3: Attack Attribution

> **Время: 35 минут** | Expert Module 5

---

## Attribution Signals

| Signal | Source | Reliability |
|--------|--------|-------------|
| **Language** | Payload text | Medium |
| **Timing** | Request patterns | Low |
| **Infrastructure** | IP/domain | Medium |
| **TTPs** | Attack patterns | High |
| **Tools** | Specific payloads | High |

---

## TTP Analysis

```python
class AttackAnalyzer:
    """Analyze attack patterns for attribution."""
    
    TTP_SIGNATURES = {
        "APT-LANG": {
            "patterns": ["特定の指示", "忽略"],
            "techniques": ["T1059"],
            "confidence": "high"
        },
        "SCRIPT-KIDDIE": {
            "patterns": ["DAN", "jailbreak", "ignore"],
            "techniques": ["T1203"],
            "confidence": "medium"
        }
    }
    
    def attribute(self, attack: Attack) -> Attribution:
        for group, signature in self.TTP_SIGNATURES.items():
            if self.matches(attack, signature):
                return Attribution(
                    group=group,
                    confidence=signature["confidence"]
                )
```

---

## Clustering Attacks

```python
from sklearn.cluster import DBSCAN

def cluster_attacks(attacks: List[Attack]):
    """Cluster similar attacks for attribution."""
    embeddings = [embed(a.payload) for a in attacks]
    
    clustering = DBSCAN(eps=0.3, min_samples=5)
    labels = clustering.fit_predict(embeddings)
    
    return group_by_label(attacks, labels)
```

---

## Attribution Caveats

⚠️ Attribution is uncertain:
- False flags exist
- Shared tools
- Copy-cat attacks

Always use **low-medium-high confidence** labels.

---

## Следующий урок

→ [5.4: Responsible Disclosure](./21-responsible-disclosure.md)
