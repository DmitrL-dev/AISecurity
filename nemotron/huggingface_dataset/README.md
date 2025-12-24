---
license: apache-2.0
task_categories:
  - text-classification
language:
  - en
  - ru
  - multilingual
tags:
  - security
  - llm-security
  - jailbreak-detection
  - prompt-injection
  - ai-safety
  - red-team
  - owasp
size_categories:
  - 10K<n<100K
---

# SENTINEL Jailbreak Detection Dataset

A comprehensive dataset for training LLM security classifiers, derived from 39,000+ jailbreak patterns collected by the SENTINEL AI Security Platform.

## Dataset Description

This dataset contains labeled prompts for training models to detect security threats in LLM inputs, including:
- **Jailbreak attempts** (role-play, DAN, encoding tricks)
- **Prompt injection** (instruction override, context manipulation)
- **Data exfiltration** (secret extraction, PII leakage)
- **Safe prompts** (normal user queries for balanced training)

### Dataset Statistics

| Split | Samples | Malicious | Safe |
|-------|---------|-----------|------|
| Train | 41,288 | ~60% | ~40% |
| Validation | 5,161 | ~60% | ~40% |
| Test | 5,161 | ~60% | ~40% |
| **Total** | **51,610** | - | - |

## Format

### ChatML Format (Recommended)
```json
{
  "messages": [
    {"role": "system", "content": "Analyze the following user prompt..."},
    {"role": "user", "content": "<prompt to classify>"},
    {"role": "assistant", "content": "{\"threat_detected\": true, ...}"}
  ]
}
```

### Output Schema
```json
{
  "threat_detected": true,
  "threat_type": "LLM01",
  "severity": "high",
  "confidence": 0.95,
  "bypass_technique": "role_play",
  "explanation": "Jailbreak attempt detected"
}
```

## Threat Types (OWASP LLM Top 10)

| Code | Description |
|------|-------------|
| LLM01 | Prompt Injection |
| LLM02 | Insecure Output Handling |
| LLM03 | Training Data Poisoning |
| LLM04 | Model Denial of Service |
| LLM05 | Supply Chain Vulnerabilities |
| LLM06 | Sensitive Information Disclosure |
| LLM07 | Insecure Plugin Design |
| LLM08 | Excessive Agency |
| LLM09 | Overreliance |
| LLM10 | Model Theft |

## Usage

### With Transformers
```python
from datasets import load_dataset

dataset = load_dataset("DmitrL-dev/sentinel-jailbreak-detection")
train = dataset["train"]
```

### With Unsloth (Fine-tuning)
```python
from unsloth import FastLanguageModel

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="unsloth/Qwen2.5-7B-Instruct",
    max_seq_length=2048,
)

# Load dataset
from datasets import load_dataset
dataset = load_dataset("DmitrL-dev/sentinel-jailbreak-detection")
```

## Source

Generated from [SENTINEL AI Security Platform](https://github.com/DmitrL-dev/AISecurity):
- 39,000+ jailbreak patterns from `signatures/jailbreaks.json`
- Augmented with safe prompts for balanced training
- Multi-language support (EN, RU, ZH, JA, FR, DE)

## Citation

```bibtex
@dataset{sentinel_jailbreak_2024,
  title={SENTINEL Jailbreak Detection Dataset},
  author={Labintsev, Dmitry},
  year={2024},
  publisher={Hugging Face},
  url={https://huggingface.co/datasets/DmitrL-dev/sentinel-jailbreak-detection}
}
```

## License

Apache 2.0

## Contact

- GitHub: [DmitrL-dev/AISecurity](https://github.com/DmitrL-dev/AISecurity)
- Email: chg@live.ru
