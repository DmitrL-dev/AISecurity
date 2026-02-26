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

```python
# Collect attack samples from paper
class PaperDataset:
    def __init__(self, paper_id: str):
        self.samples = []
        
    def add_from_paper(self, table_num: int, examples: List[str]):
        """Add examples from paper tables."""
        for ex in examples:
            self.samples.append({
                "text": ex,
                "source": f"Table {table_num}",
                "paper": self.paper_id
            })
    
    def add_from_appendix(self, appendix: str, file_path: str):
        """Add from supplementary materials."""
        pass
```

---

## Validation

```python
def validate_reproduction(paper_results, our_results, tolerance=0.05):
    """Validate our results match paper claims."""
    
    for metric, paper_value in paper_results.items():
        our_value = our_results[metric]
        diff = abs(paper_value - our_value)
        
        if diff > tolerance:
            print(f"⚠️ {metric}: paper={paper_value}, ours={our_value}")
        else:
            print(f"✅ {metric}: matches within {tolerance}")
```

---

## Следующий урок

→ [2.1: Topological Data Analysis](./05-tda.md)
