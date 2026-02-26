# Tokenization и безопасность

> **Урок:** 01.2.2 - Tokenization  
> **Время:** 35 минут  
> **Пререквизиты:** Attention basics

---

## Цели обучения

К концу этого урока вы сможете:

1. Понимать как tokenization работает
2. Идентифицировать tokenization-based attack vectors
3. Exploit и защищаться от tokenization quirks
4. Проектировать token-aware security measures

---

## Что такое Tokenization?

Tokenization конвертирует текст в numerical tokens которые модели могут обрабатывать:

```
"Hello, world!" → [15496, 11, 995, 0]
                   Hello  ,   world !
```

| Tokenizer Type | Example |
|---------------|---------|
| **BPE** | Most GPT models |
| **WordPiece** | BERT, some others |
| **SentencePiece** | Many multilingual models |
| **Unigram** | XLNet, T5 |

---

## Security Implications

### 1. Token Boundaries Enable Attacks

```rust
// Word-level detection fails на split tokens
let keyword = "bomb"; // Blocked as keyword

// Но tokenizer может split иначе:
let evasion = format!("{}{}", "b", "omb"); // May tokenize as ["b", "omb"]
let evasion2 = format!("{}{}", "bo", "mb"); // May tokenize as ["bo", "mb"]

// Regex ищущий "bomb" пропускает split versions
```

### 2. Tokenization Inconsistency

```rust
use tokenizers::Tokenizer;

let tokenizer = Tokenizer::from_pretrained("gpt2", None).unwrap();

// Одно слово, разные tokenizations based on context
println!("{:?}", tokenizer.encode("bomb", false).unwrap().get_ids());      // [21901]
println!("{:?}", tokenizer.encode(" bomb", false).unwrap().get_ids());     // [6202]   (with space)
println!("{:?}", tokenizer.encode("Bomb", false).unwrap().get_ids());      // [33, 2381]  (capitalized)
println!("{:?}", tokenizer.encode("BOMB", false).unwrap().get_ids());      // [33, 2662, 33]  (all caps)

// Detection должен учитывать все variants!
```

---

## Token-Based Attacks

### 1. Token Splitting Evasion

```rust
use std::collections::HashMap;
use tokenizers::Tokenizer;

struct TokenSplitAttack {
    /// Evasion keyword detection через token splitting.
    tokenizer: Tokenizer,
}

impl TokenSplitAttack {
    fn new(tokenizer: Tokenizer) -> Self {
        Self { tokenizer }
    }

    fn find_evasive_spellings(&self, keyword: &str) -> Vec<serde_json::Value> {
        /// Найти spellings которые avoid keyword's token.
        let original_tokens = self.tokenizer.encode(keyword, false).unwrap().get_ids().to_vec();
        let mut evasions = Vec::new();

        // Try various splitting strategies
        for i in 1..keyword.len() {
            // Split с spaces
            let split = format!("{} {}", &keyword[..i], &keyword[i..]);
            let tokens = self.tokenizer.encode(split.as_str(), false).unwrap().get_ids().to_vec();
            if tokens != original_tokens {
                evasions.push(serde_json::json!({
                    "variant": split,
                    "tokens": tokens,
                    "strategy": "space_split"
                }));
            }

            // Split с zero-width characters
            let zwsp = "\u{200b}";
            let split_zwsp = format!("{}{}{}", &keyword[..i], zwsp, &keyword[i..]);
            let tokens = self.tokenizer.encode(split_zwsp.as_str(), false).unwrap().get_ids().to_vec();
            if tokens != original_tokens {
                evasions.push(serde_json::json!({
                    "variant": split_zwsp,
                    "tokens": tokens,
                    "strategy": "zero_width_split"
                }));
            }
        }

        evasions
    }

    fn find_homoglyph_evasions(&self, keyword: &str) -> Vec<serde_json::Value> {
        /// Найти homoglyph substitutions которые change tokens.
        let homoglyphs: HashMap<char, char> = [
            ('a', 'а'), ('e', 'е'), ('o', 'о'), ('p', 'р'),
            ('c', 'с'), ('x', 'х'), ('i', 'і'),
        ].into();

        let original_tokens = self.tokenizer.encode(keyword, false).unwrap().get_ids().to_vec();
        let mut evasions = Vec::new();

        for (i, ch) in keyword.chars().enumerate() {
            if let Some(&replacement) = homoglyphs.get(&ch.to_lowercase().next().unwrap()) {
                let variant: String = keyword.chars().enumerate().map(|(j, c)| {
                    if j == i { replacement } else { c }
                }).collect();
                let tokens = self.tokenizer.encode(variant.as_str(), false).unwrap().get_ids().to_vec();

                if tokens != original_tokens {
                    evasions.push(serde_json::json!({
                        "variant": variant,
                        "tokens": tokens,
                        "strategy": "homoglyph"
                    }));
                }
            }
        }

        evasions
    }
}
```

---

### 2. Token Boundary Manipulation

```rust
use tokenizers::Tokenizer;

struct TokenBoundaryManipulator {
    /// Exploit token boundaries для attacks.
    tokenizer: Tokenizer,
}

impl TokenBoundaryManipulator {
    fn new(tokenizer: Tokenizer) -> Self {
        Self { tokenizer }
    }

    fn fragment_instruction(&self, instruction: &str) -> String {
        /// Fragment instruction across token boundaries.

        // Find natural token breaks
        let encoding = self.tokenizer.encode(instruction, false).unwrap();
        let tokens = encoding.get_ids();
        let decoded_tokens: Vec<String> = tokens
            .iter()
            .map(|&t| self.tokenizer.decode(&[t], true).unwrap())
            .collect();

        // Insert characters которые change boundaries
        let mut fragmented = String::new();
        for (i, token_text) in decoded_tokens.iter().enumerate() {
            fragmented.push_str(token_text);
            if i < decoded_tokens.len() - 1 {
                // Insert boundary-breaking character
                fragmented.push('\u{200b}'); // Zero-width space
            }
        }

        fragmented
    }

    fn embed_in_tokens(&self, payload: &str, carrier: &str) -> String {
        /// Embed payload within carrier text tokens.

        // Strategy: insert payload где не будет detected
        // by token-level keyword matching

        let _carrier_tokens = self.tokenizer.encode(carrier, false).unwrap();
        let _payload_tokens = self.tokenizer.encode(payload, false).unwrap();

        // Find position где payload integrates smoothly
        // Это model-specific и requires experimentation

        format!("{}\n\n{}", carrier, payload)
    }
}
```

---

### 3. Glitch Tokens

```rust
use candle_core::{Tensor, Device};
use std::collections::HashMap;

// Некоторые tokenizers имеют "glitch tokens" - tokens которые cause unusual behavior

let glitch_tokens: HashMap<&str, Vec<&str>> = [
    ("gpt-2", vec![
        " petertodd",          // Known glitch token
        "SolidGoldMagikarp",   // Another example
    ]),
].into();

struct GlitchTokenExplorer {
    /// Explore glitch tokens в tokenizer.
    tokenizer: tokenizers::Tokenizer,
    model: Box<dyn EmbeddingModel>,
}

impl GlitchTokenExplorer {
    fn find_glitch_tokens(&self, sample_size: usize) -> Vec<serde_json::Value> {
        /// Найти tokens с unusual embedding properties.
        let vocab_size = self.tokenizer.get_vocab_size(false);
        let mut unusual = Vec::new();

        for token_id in 0..sample_size.min(vocab_size) {
            let token_text = self.tokenizer.decode(&[token_id as u32], true).unwrap();
            let token_tensor = Tensor::new(&[token_id as u32], &Device::Cpu).unwrap();
            let embedding = self.model.get_input_embeddings(&token_tensor);

            // Check для unusual embedding properties
            let norm = embedding.sqr().unwrap().sum_all().unwrap().sqrt().unwrap()
                .to_scalar::<f64>().unwrap();
            if norm > 100.0 || norm < 0.01 {
                unusual.push(serde_json::json!({
                    "token_id": token_id,
                    "text": token_text,
                    "embedding_norm": norm
                }));
            }
        }

        unusual
    }
}
```

---

## Defense Techniques

### 1. Token-Aware Keyword Detection

```rust
use std::collections::HashMap;
use tokenizers::Tokenizer;

struct TokenAwareDetector {
    /// Keyword detection который accounts for tokenization.
    tokenizer: Tokenizer,
    keyword_token_sets: HashMap<String, Vec<Vec<u32>>>,
}

impl TokenAwareDetector {
    fn new(tokenizer: Tokenizer, keywords: &[&str]) -> Self {
        // Pre-compute все token variants keywords
        let mut keyword_token_sets = HashMap::new();
        for &keyword in keywords {
            let variants = Self::get_all_variants(&tokenizer, keyword);
            keyword_token_sets.insert(keyword.to_string(), variants);
        }
        Self { tokenizer, keyword_token_sets }
    }

    fn get_all_variants(tokenizer: &Tokenizer, keyword: &str) -> Vec<Vec<u32>> {
        /// Get все token sequences для keyword variants.
        let mut variants = Vec::new();

        // Original
        variants.push(tokenizer.encode(keyword, false).unwrap().get_ids().to_vec());

        // With leading space
        let spaced = format!(" {}", keyword);
        variants.push(tokenizer.encode(spaced.as_str(), false).unwrap().get_ids().to_vec());

        // Capitalization variants
        variants.push(tokenizer.encode(&keyword.to_lowercase(), false).unwrap().get_ids().to_vec());
        variants.push(tokenizer.encode(&keyword.to_uppercase(), false).unwrap().get_ids().to_vec());
        let capitalized = format!("{}{}", &keyword[..1].to_uppercase(), &keyword[1..]);
        variants.push(tokenizer.encode(capitalized.as_str(), false).unwrap().get_ids().to_vec());

        // Deduplicate
        variants.sort();
        variants.dedup();
        variants
    }

    fn detect(&self, text: &str) -> serde_json::Value {
        /// Detect keywords accounting for tokenization.
        let tokens = self.tokenizer.encode(text, false).unwrap().get_ids().to_vec();

        let mut found = Vec::new();
        for (keyword, token_variants) in &self.keyword_token_sets {
            for variant in token_variants {
                if self.contains_subsequence(&tokens, variant) {
                    found.push(keyword.clone());
                    break;
                }
            }
        }

        serde_json::json!({
            "found_keywords": found,
            "is_suspicious": !found.is_empty()
        })
    }

    fn contains_subsequence(&self, sequence: &[u32], subseq: &[u32]) -> bool {
        /// Check содержит ли sequence subsequence.
        let (n, m) = (sequence.len(), subseq.len());
        if m > n { return false; }
        for i in 0..=(n - m) {
            if &sequence[i..i + m] == subseq {
                return true;
            }
        }
        false
    }
}
```

---

### 2. Pre-Tokenization Normalization

```rust
use std::collections::HashMap;

struct TokenizationNormalizer {
    /// Normalize text до tokenization чтобы prevent evasion.
    invisible_chars: Vec<char>,
    homoglyphs: HashMap<char, char>,
}

impl TokenizationNormalizer {
    fn new() -> Self {
        // Zero-width characters для removal
        let invisible_chars = vec![
            '\u{200b}', '\u{200c}', '\u{200d}', '\u{2060}', '\u{feff}',
        ];

        // Homoglyph replacements
        let homoglyphs: HashMap<char, char> = [
            ('а', 'a'), ('е', 'e'), ('о', 'o'), ('р', 'p'),
            ('с', 'c'), ('х', 'x'), ('і', 'i'), ('у', 'y'),
        ].into();

        Self { invisible_chars, homoglyphs }
    }

    fn normalize(&self, text: &str) -> String {
        /// Normalize text к consistent form.
        let mut result = text.to_string();

        // Remove invisible characters
        for &ch in &self.invisible_chars {
            result = result.replace(ch, "");
        }

        // Replace homoglyphs
        result = result
            .chars()
            .map(|c| *self.homoglyphs.get(&c).unwrap_or(&c))
            .collect();

        // Normalize unicode (NFKC)
        unicode_normalization::UnicodeNormalization::nfkc(&*result).collect()
    }
}
```

---

### 3. Semantic Detection (Token-Agnostic)

```rust
use ndarray::Array1;

struct SemanticDetector {
    /// Detect harmful content regardless of tokenization.
    embed: Box<dyn Fn(&str) -> Array1<f64>>,
    harmful_embeddings: Vec<Array1<f64>>,
}

impl SemanticDetector {
    fn new(
        embed: Box<dyn Fn(&str) -> Array1<f64>>,
        harmful_examples: &[&str],
    ) -> Self {
        // Pre-compute embeddings для known harmful patterns
        let harmful_embeddings = harmful_examples.iter().map(|ex| embed(ex)).collect();
        Self { embed, harmful_embeddings }
    }

    fn detect(&self, text: &str, threshold: f64) -> serde_json::Value {
        /// Detect harmful content через semantic similarity.
        let text_emb = (self.embed)(text);

        let mut max_similarity: f64 = 0.0;
        let mut most_similar_idx: Option<usize> = None;

        for (i, harmful_emb) in self.harmful_embeddings.iter().enumerate() {
            let sim = self.cosine_similarity(&text_emb, harmful_emb);
            if sim > max_similarity {
                max_similarity = sim;
                most_similar_idx = Some(i);
            }
        }

        serde_json::json!({
            "is_harmful": max_similarity > threshold,
            "confidence": max_similarity,
            "matched_pattern": if max_similarity > threshold { most_similar_idx } else { None }
        })
    }

    fn cosine_similarity(&self, a: &Array1<f64>, b: &Array1<f64>) -> f64 {
        let dot: f64 = a.iter().zip(b.iter()).map(|(x, y)| x * y).sum();
        let norm_a: f64 = a.iter().map(|x| x * x).sum::<f64>().sqrt();
        let norm_b: f64 = b.iter().map(|x| x * x).sum::<f64>().sqrt();
        dot / (norm_a * norm_b)
    }
}
```

---

## Интеграция с SENTINEL

```rust
use sentinel_core::engines::{configure, TokenGuard};

configure(serde_json::json!({
    "tokenization_normalization": true,
    "token_aware_detection": true,
    "glitch_token_protection": true,
}));

let token_guard = TokenGuard::new(
    true, // normalize_before_detection
    true, // block_glitch_tokens
);

#[token_guard::protect]
fn process_input(text: &str) -> String {
    // Автоматически normalized и checked
    llm.generate(text)
}
```

---

## Ключевые выводы

1. **Tokenization affects detection** — Одно слово, different tokens
2. **Attackers exploit splits** — Bypass keyword filters
3. **Normalize before detection** — Remove invisible chars, homoglyphs
4. **Use semantic detection** — Token-agnostic более robust
5. **Test your tokenizer** — Know its quirks

---

*AI Security Academy | Урок 01.2.2*
