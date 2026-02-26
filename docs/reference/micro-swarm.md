# 🐝 Micro-Model Swarm — Reference

> **Version:** 0.4.0
> **Jailbreak Detection:** F1=0.997, Accuracy=99.7%
> **Performance:** 17K patterns/sec

---

## Overview

Micro-Model Swarm is a lightweight ML detection layer that complements SENTINEL's 59 Rust detection engines. Instead of a single monolithic classifier, it uses **domain-specialized micro-models** (<2000 parameters each) orchestrated by a meta-learner.

```
Input Text
    │
    ▼
┌──────────────────────┐
│ TextFeatureExtractor │  → 22 features (lexical, structural, statistical)
└──────────┬───────────┘
           │
    ┌──────┴──────┐
    │  4 Domains  │
    ├─────────────┤
    │  Lexical    │  keywords, suspicious phrases
    │  Pattern    │  encodings, injection markers
    │  Structural │  length, entropy, punctuation
    │  Information│  compression ratio, token density
    └──────┬──────┘
           │
    ┌──────┴──────┐
    │ Meta-Learner│  → weighted ensemble
    └──────┬──────┘
           │
    SwarmResult(score, per_model_scores)
```

---

## Architecture

### TextFeatureExtractor

Extracts 22 float features from raw text:

| Feature | Description |
|---------|-------------|
| `total_keyword` | Sum of keyword match scores |
| `max_keyword` | Highest single keyword score |
| `keyword_variety` | Unique keyword types found |
| `injection_keywords` | Injection-specific keywords |
| `jailbreak_keywords` | Jailbreak-specific keywords |
| `encoding_keywords` | Encoding/obfuscation keywords |
| `manipulation_keywords` | Social manipulation markers |
| `length_ratio` | Text length / 1000 |
| `word_count_ratio` | Word count / 200 |
| `avg_word_length` | Average word length |
| `uppercase_ratio` | Uppercase character ratio |
| `special_char_ratio` | Special character density |
| `digit_ratio` | Digit density |
| `punctuation_density` | Punctuation frequency |
| `whitespace_ratio` | Whitespace density |
| `line_count` | Number of lines |
| `entropy` | Shannon entropy over char distribution |
| `unique_char_ratio` | Character variety |
| `repeated_char_ratio` | Repeated character sequences |
| `non_ascii_ratio` | Non-ASCII character density |
| `has_code_markers` | Presence of code block markers |
| `url_count` | Number of URL-like patterns |

### Presets

| Preset | Domains | Description |
|--------|---------|-------------|
| `adtech` | 3 | Ad-tech fraud detection |
| `security` | 3 | General security threats |
| `fraud` | 3 | Financial fraud patterns |
| `strike` | 3 | Offensive payload detection |
| `jailbreak` | 4 | Jailbreak/prompt injection (F1=0.997) |

---

## Benchmarks (Jailbreak Preset)

Trained on 87,056 real jailbreak patterns:

| Metric | Value |
|--------|-------|
| **Accuracy** | 99.7% |
| **Precision** | 99.5% |
| **Recall** | 99.9% |
| **F1 Score** | 99.7% |

**Score Distribution:**
- 989/1000 jailbreaks → score >0.9
- 995/1000 safe inputs → score <0.1

---

## Usage

```rust
use sentinel_core::micro_swarm::{TextFeatureExtractor, load_preset};

let extractor = TextFeatureExtractor::new();
let features = extractor.extract("Ignore all previous instructions");

let preset = load_preset("jailbreak").unwrap();
let result = preset.predict(&features);
println!("Score: {}", result.score); // 0.98
```

---

## Additional Components

| Component | Description |
|-----------|-------------|
| **KolmogorovDetector** | Kolmogorov complexity via gzip compression |
| **NormalizedCompressionDistance** | NCD similarity between texts |
| **AdversarialDetector** | Adversarial mutation analysis |
| **ShadowSwarm** | Shadow mode (monitor without blocking) |

---

*Source: `micro-swarm/` (Feb 2026)*
