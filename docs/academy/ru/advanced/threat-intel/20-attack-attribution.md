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

```rust
use std::collections::HashMap;

/// Analyze attack patterns for attribution.
struct AttackAnalyzer {
    ttp_signatures: HashMap<&'static str, TtpSignature>,
}

struct TtpSignature {
    patterns: Vec<&'static str>,
    techniques: Vec<&'static str>,
    confidence: &'static str,
}

impl AttackAnalyzer {
    fn new() -> Self {
        let mut sigs = HashMap::new();
        sigs.insert("APT-LANG", TtpSignature {
            patterns: vec!["特定の指示", "忽略"],
            techniques: vec!["T1059"],
            confidence: "high",
        });
        sigs.insert("SCRIPT-KIDDIE", TtpSignature {
            patterns: vec!["DAN", "jailbreak", "ignore"],
            techniques: vec!["T1203"],
            confidence: "medium",
        });
        Self { ttp_signatures: sigs }
    }

    fn attribute(&self, attack: &Attack) -> Option<Attribution> {
        for (group, signature) in &self.ttp_signatures {
            if self.matches(attack, signature) {
                return Some(Attribution {
                    group: group.to_string(),
                    confidence: signature.confidence.to_string(),
                });
            }
        }
        None
    }
}
```

---

## Clustering Attacks

```rust
use linfa::traits::Fit;
use linfa_clustering::Dbscan;

fn cluster_attacks(attacks: &[Attack]) -> Vec<Vec<&Attack>> {
    /// Cluster similar attacks for attribution.
    let embeddings: Vec<Vec<f64>> = attacks
        .iter()
        .map(|a| embed(&a.payload))
        .collect();

    let dataset = Dataset::from(embeddings);
    let clustering = Dbscan::params(5)
        .tolerance(0.3)
        .fit(&dataset)
        .unwrap();

    group_by_label(attacks, &clustering.labels())
}
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
