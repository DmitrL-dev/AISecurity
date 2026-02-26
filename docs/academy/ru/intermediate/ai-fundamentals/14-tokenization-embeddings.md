# Tokenization и Embeddings

> **Урок:** 01.3.1 - Tokenization and Embeddings  
> **Время:** 35 минут  
> **Пререквизиты:** ML basics

---

## Цели обучения

К концу этого урока вы сможете:

1. Понимать tokenization algorithms
2. Объяснять embedding representations
3. Идентифицировать tokenization-related vulnerabilities
4. Применять embedding security techniques

---

## Tokenization Fundamentals

Tokenization конвертирует text в numerical tokens:

```rust
use tokenizers::Tokenizer;

fn main() {
    let tokenizer = Tokenizer::from_pretrained("gpt2", None).unwrap();

    let text = "Hello, world!";
    let encoding = tokenizer.encode(text, false).unwrap();
    let tokens = encoding.get_ids();
    // [15496, 11, 995, 0]  // Token IDs

    let decoded: Vec<String> = tokens.iter()
        .map(|t| tokenizer.decode(&[*t], true).unwrap())
        .collect();
    // ["Hello", ",", "world", "!"]
}
```

| Algorithm | Description | Used By |
|-----------|-------------|---------|
| **BPE** | Byte-Pair Encoding | GPT-2, GPT-3/4 |
| **WordPiece** | Word-level + subwords | BERT |
| **SentencePiece** | Unigram-based | T5, LLaMA |

---

## Security Implications of Tokenization

### 1. Token Boundary Attacks

```rust
use std::collections::HashMap;
use tokenizers::Tokenizer;

/// Exploit token boundaries для evasion.
struct TokenBoundaryAttack {
    tokenizer: Tokenizer,
}

impl TokenBoundaryAttack {
    fn new(tokenizer: Tokenizer) -> Self {
        Self { tokenizer }
    }

    /// Найти spellings которые split keyword на different tokens.
    fn find_split_evasions(&self, keyword: &str) -> Vec<HashMap<String, serde_json::Value>> {
        let original_tokens = self.tokenizer.encode(keyword, false).unwrap().get_ids().to_vec();
        let mut evasions = Vec::new();

        // Try space insertion
        for i in 1..keyword.len() {
            let variant = format!("{} {}", &keyword[..i], &keyword[i..]);
            let new_tokens = self.tokenizer.encode(variant.as_str(), false).unwrap().get_ids().to_vec();

            if new_tokens != original_tokens {
                let mut entry = HashMap::new();
                entry.insert("variant".into(), serde_json::json!(variant));
                entry.insert("original_tokens".into(), serde_json::json!(original_tokens));
                entry.insert("new_tokens".into(), serde_json::json!(new_tokens));
                evasions.push(entry);
            }
        }

        evasions
    }

    /// Использовать similar-looking characters чтобы change tokenization.
    fn homoglyph_evasion(&self, keyword: &str) -> Vec<HashMap<String, serde_json::Value>> {
        let homoglyphs: HashMap<char, char> = [
            ('a', '\u{0430}'), ('e', '\u{0435}'), ('o', '\u{043e}'), ('c', '\u{0441}'),
        ].into_iter().collect();

        let original_tokens = self.tokenizer.encode(keyword, false).unwrap().get_ids().to_vec();
        let mut evasions = Vec::new();

        for (i, ch) in keyword.chars().enumerate() {
            if let Some(&replacement) = homoglyphs.get(&ch.to_lowercase().next().unwrap()) {
                let variant: String = keyword.chars().enumerate()
                    .map(|(j, c)| if j == i { replacement } else { c })
                    .collect();
                let new_tokens = self.tokenizer.encode(variant.as_str(), false).unwrap().get_ids().to_vec();

                if new_tokens != original_tokens {
                    let mut entry = HashMap::new();
                    entry.insert("variant".into(), serde_json::json!(variant));
                    entry.insert("substituted".into(), serde_json::json!(ch.to_string()));
                    entry.insert("with".into(), serde_json::json!(replacement.to_string()));
                    evasions.push(entry);
                }
            }
        }

        evasions
    }
}
```

### 2. Glitch Tokens

```rust
use std::collections::HashMap;
use candle_core::{Device, Tensor};

// Некоторые tokenizers имеют "glitch tokens" с unusual behavior
fn known_glitch_tokens() -> HashMap<&'static str, Vec<&'static str>> {
    let mut map = HashMap::new();
    map.insert("gpt2", vec![
        " SolidGoldMagikarp",  // Known anomaly token
        " petertodd",          // Another example
    ]);
    map
}

/// Detect tokens с anomalous embeddings.
fn detect_glitch_tokens(
    tokenizer: &tokenizers::Tokenizer,
    model: &dyn Module,
    device: &Device,
) -> Vec<HashMap<String, serde_json::Value>> {
    let mut anomalies = Vec::new();
    let vocab_size = tokenizer.get_vocab_size(true).min(50000);

    for token_id in 0..vocab_size as u32 {
        let id_tensor = Tensor::new(&[token_id], device).unwrap();
        let embedding = model.get_input_embeddings(&id_tensor).unwrap();
        let norm: f64 = embedding.sqr().unwrap().sum_all().unwrap().sqrt().unwrap()
            .to_scalar().unwrap();

        // Extremely high или low norms suspicious
        if norm > 100.0 || norm < 0.001 {
            let mut entry = HashMap::new();
            entry.insert("token_id".into(), serde_json::json!(token_id));
            entry.insert("text".into(), serde_json::json!(
                tokenizer.decode(&[token_id], true).unwrap_or_default()
            ));
            entry.insert("embedding_norm".into(), serde_json::json!(norm));
            anomalies.push(entry);
        }
    }

    anomalies
}
```

---

## Embedding Security

### 1. Semantic Understanding

```rust
use ndarray::{Array1, ArrayView1};

/// Analyze embeddings для security applications.
struct EmbeddingSecurityAnalyzer {
    model: Box<dyn EmbeddingModel>,
}

impl EmbeddingSecurityAnalyzer {
    fn new(model: Box<dyn EmbeddingModel>) -> Self {
        Self { model }
    }

    /// Compute semantic similarity.
    fn semantic_similarity(&self, text1: &str, text2: &str) -> f64 {
        let emb1 = self.model.encode(text1);
        let emb2 = self.model.encode(text2);

        let dot: f64 = emb1.iter().zip(emb2.iter()).map(|(a, b)| a * b).sum();
        let norm1: f64 = emb1.iter().map(|x| x * x).sum::<f64>().sqrt();
        let norm2: f64 = emb2.iter().map(|x| x * x).sum::<f64>().sqrt();

        dot / (norm1 * norm2)
    }

    /// Detect attack через embedding similarity.
    fn detect_semantic_attack(
        &self,
        input_text: &str,
        attack_references: &[String],
        threshold: f64,
    ) -> std::collections::HashMap<String, serde_json::Value> {
        let input_emb = self.model.encode(input_text);

        for reference in attack_references {
            let ref_emb = self.model.encode(reference);

            let dot: f64 = input_emb.iter().zip(ref_emb.iter()).map(|(a, b)| a * b).sum();
            let norm_i: f64 = input_emb.iter().map(|x| x * x).sum::<f64>().sqrt();
            let norm_r: f64 = ref_emb.iter().map(|x| x * x).sum::<f64>().sqrt();
            let similarity = dot / (norm_i * norm_r);

            if similarity > threshold {
                let mut result = std::collections::HashMap::new();
                result.insert("is_attack".into(), serde_json::json!(true));
                result.insert("matched_reference".into(), serde_json::json!(reference));
                result.insert("similarity".into(), serde_json::json!(similarity));
                return result;
            }
        }

        let mut result = std::collections::HashMap::new();
        result.insert("is_attack".into(), serde_json::json!(false));
        result
    }
}
```

### 2. Embedding Anomaly Detection

```rust
/// Detect anomalous inputs через embeddings.
struct EmbeddingAnomalyDetector {
    model: Box<dyn EmbeddingModel>,
    baseline: Option<Vec<f64>>,
    threshold: Option<f64>,
}

impl EmbeddingAnomalyDetector {
    fn new(model: Box<dyn EmbeddingModel>) -> Self {
        Self { model, baseline: None, threshold: None }
    }

    /// Fit на normal samples.
    fn fit(&mut self, normal_samples: &[String]) {
        let embeddings: Vec<Vec<f64>> = normal_samples.iter()
            .map(|s| self.model.encode(s))
            .collect();

        let dim = embeddings[0].len();
        let n = embeddings.len() as f64;
        let mut mean = vec![0.0f64; dim];
        for emb in &embeddings {
            for (i, v) in emb.iter().enumerate() {
                mean[i] += v / n;
            }
        }
        self.baseline = Some(mean.clone());

        let mut distances: Vec<f64> = embeddings.iter().map(|e| {
            e.iter().zip(mean.iter()).map(|(a, b)| (a - b).powi(2)).sum::<f64>().sqrt()
        }).collect();
        distances.sort_by(|a, b| a.partial_cmp(b).unwrap());
        let idx = (distances.len() as f64 * 0.95) as usize;
        self.threshold = Some(distances[idx.min(distances.len() - 1)]);
    }

    /// Detect anomaly.
    fn detect(&self, text: &str) -> std::collections::HashMap<String, serde_json::Value> {
        let embedding = self.model.encode(text);
        let baseline = self.baseline.as_ref().unwrap();
        let distance: f64 = embedding.iter().zip(baseline.iter())
            .map(|(a, b)| (a - b).powi(2)).sum::<f64>().sqrt();
        let threshold = self.threshold.unwrap();

        let mut result = std::collections::HashMap::new();
        result.insert("is_anomaly".into(), serde_json::json!(distance > threshold));
        result.insert("distance".into(), serde_json::json!(distance));
        result.insert("threshold".into(), serde_json::json!(threshold));
        result
    }
}
```

### 3. Adversarial Embedding Defense

```rust
/// Defend против embedding-level attacks.
struct EmbeddingDefense {
    model: Box<dyn EmbeddingModel>,
}

impl EmbeddingDefense {
    fn new(model: Box<dyn EmbeddingModel>) -> Self {
        Self { model }
    }

    /// Robust similarity через augmentation.
    fn robust_similarity(&self, text1: &str, text2: &str, n_augments: usize) -> f64 {
        let augments1 = self.augment(text1, n_augments);
        let augments2 = self.augment(text2, n_augments);

        let mut similarities = Vec::new();
        for a1 in &augments1 {
            for a2 in &augments2 {
                let emb1 = self.model.encode(a1);
                let emb2 = self.model.encode(a2);
                let dot: f64 = emb1.iter().zip(emb2.iter()).map(|(a, b)| a * b).sum();
                let n1: f64 = emb1.iter().map(|x| x * x).sum::<f64>().sqrt();
                let n2: f64 = emb2.iter().map(|x| x * x).sum::<f64>().sqrt();
                similarities.push(dot / (n1 * n2));
            }
        }

        // Использовать median для robustness
        similarities.sort_by(|a, b| a.partial_cmp(b).unwrap());
        similarities[similarities.len() / 2]
    }

    /// Simple text augmentations.
    fn augment(&self, text: &str, n: usize) -> Vec<String> {
        let mut augments = vec![text.to_string()];

        // Lowercase
        augments.push(text.to_lowercase());

        // Remove extra spaces
        augments.push(text.split_whitespace().collect::<Vec<_>>().join(" "));

        // Truncation
        let words: Vec<&str> = text.split_whitespace().collect();
        if words.len() > 3 {
            augments.push(words[..words.len() - 1].join(" "));
            augments.push(words[1..].join(" "));
        }

        augments.truncate(n);
        augments
    }
}
```

---

## Token-Aware Detection

```rust
use std::collections::{HashMap, HashSet};
use tokenizers::Tokenizer;

/// Detection который accounts for tokenization.
struct TokenAwareDetector {
    tokenizer: Tokenizer,
    keyword_tokens: HashMap<String, HashSet<Vec<u32>>>,
}

impl TokenAwareDetector {
    fn new(tokenizer: Tokenizer, keywords: &[String]) -> Self {
        // Pre-compute все token variants
        let mut keyword_tokens = HashMap::new();
        for keyword in keywords {
            keyword_tokens.insert(
                keyword.clone(),
                Self::get_token_variants(&tokenizer, keyword),
            );
        }
        Self { tokenizer, keyword_tokens }
    }

    /// Get все token representations keyword.
    fn get_token_variants(tokenizer: &Tokenizer, keyword: &str) -> HashSet<Vec<u32>> {
        let mut variants = HashSet::new();

        // Plain
        variants.insert(tokenizer.encode(keyword, false).unwrap().get_ids().to_vec());

        // With leading space
        let spaced = format!(" {}", keyword);
        variants.insert(tokenizer.encode(spaced.as_str(), false).unwrap().get_ids().to_vec());

        // Case variants
        variants.insert(tokenizer.encode(&keyword.to_lowercase(), false).unwrap().get_ids().to_vec());
        variants.insert(tokenizer.encode(&keyword.to_uppercase(), false).unwrap().get_ids().to_vec());
        let capitalized = format!("{}{}", &keyword[..1].to_uppercase(), &keyword[1..]);
        variants.insert(tokenizer.encode(capitalized.as_str(), false).unwrap().get_ids().to_vec());

        variants
    }

    /// Detect keywords accounting for tokenization.
    fn detect(&self, text: &str) -> HashMap<String, serde_json::Value> {
        let text_tokens = self.tokenizer.encode(text, false).unwrap().get_ids().to_vec();

        let mut found = Vec::new();
        for (keyword, token_variants) in &self.keyword_tokens {
            for variant in token_variants {
                if Self::subsequence_in(variant, &text_tokens) {
                    found.push(keyword.clone());
                    break;
                }
            }
        }

        let mut result = HashMap::new();
        result.insert("is_suspicious".into(), serde_json::json!(!found.is_empty()));
        result.insert("found_keywords".into(), serde_json::json!(found));
        result
    }

    /// Check если subsequence в sequence.
    fn subsequence_in(subseq: &[u32], seq: &[u32]) -> bool {
        let (n, m) = (seq.len(), subseq.len());
        if m > n { return false; }
        for i in 0..=n - m {
            if seq[i..i + m] == *subseq {
                return true;
            }
        }
        false
    }
}
```

---

## Интеграция с SENTINEL

```rust
use sentinel_core::engines::{TokenGuard, EmbeddingGuard, configure};

fn main() {
    configure(
        true,  // tokenization_protection
        true,  // embedding_detection
    );

    let token_guard = TokenGuard::builder()
        .normalize_homoglyphs(true)
        .detect_glitch_tokens(true)
        .build();

    let embedding_guard = EmbeddingGuard::builder()
        .embedding_model("all-MiniLM-L6-v2")
        .anomaly_detection(true)
        .build();

    // Protected на обоих token и embedding level
    let result = token_guard.protect(|text| {
        embedding_guard.protect(|text| {
            llm.generate(text)
        }, text)
    }, input_text);
}
```

---

## Ключевые выводы

1. **Tokenization affects detection** — Одно слово, разные tokens
2. **Homoglyphs evade filters** — Normalize before matching
3. **Embeddings capture meaning** — Semantic attack detection
4. **Glitch tokens exist** — Monitor for anomalies
5. **Layer your defenses** — Token + embedding + pattern

---

*AI Security Academy | Урок 01.3.1*
