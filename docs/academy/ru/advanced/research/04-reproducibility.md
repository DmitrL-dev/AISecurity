# 🔬 Урок 1.4: Reproducibility

> **Время: 40 минут** | Expert Module 1

---

## Paper Reproduction Workflow

```
Paper → Environment → Data → Code → Validate → Document
```

---

## Environment Setup

```bash
# Create isolated environment
python -m venv reproduce_env
source reproduce_env/bin/activate

# Pin versions from paper
pip install torch==2.1.0
pip install transformers==4.35.0
```

---

## Data Collection

```rust
use std::collections::HashMap;

// Collect attack samples from paper
struct Sample {
    text: String,
    source: String,
    paper: String,
}

struct PaperDataset {
    paper_id: String,
    samples: Vec<Sample>,
}

impl PaperDataset {
    fn new(paper_id: &str) -> Self {
        Self {
            paper_id: paper_id.to_string(),
            samples: Vec::new(),
        }
    }

    /// Add examples from paper tables.
    fn add_from_paper(&mut self, table_num: usize, examples: &[&str]) {
        for ex in examples {
            self.samples.push(Sample {
                text: ex.to_string(),
                source: format!("Table {}", table_num),
                paper: self.paper_id.clone(),
            });
        }
    }

    /// Add from supplementary materials.
    fn add_from_appendix(&mut self, _appendix: &str, _file_path: &str) {
        // ...
    }
}
```

---

## Validation

```rust
use std::collections::HashMap;

fn validate_reproduction(
    paper_results: &HashMap<String, f64>,
    our_results: &HashMap<String, f64>,
    tolerance: f64,
) {
    /// Validate our results match paper claims.
    for (metric, &paper_value) in paper_results.iter() {
        let our_value = our_results[metric];
        let diff = (paper_value - our_value).abs();

        if diff > tolerance {
            println!("⚠️ {}: paper={}, ours={}", metric, paper_value, our_value);
        } else {
            println!("✅ {}: matches within {}", metric, tolerance);
        }
    }
}
```

---

## Следующий урок

→ [2.1: Topological Data Analysis](./05-tda.md)
