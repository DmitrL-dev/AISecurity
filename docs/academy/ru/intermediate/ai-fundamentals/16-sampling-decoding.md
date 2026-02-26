# Sampling и Decoding

> **Уровень:** Beginner  
> **Время:** 35 минут  
> **Трек:** 01 — AI Fundamentals  
> **Модуль:** 01.3 — Key Concepts  
> **Версия:** 1.0

---

## Цели обучения

- [ ] Понять как модели выбирают следующий token
- [ ] Знать основные стратегии: greedy, top-k, top-p, temperature
- [ ] Понимать влияние параметров на output
- [ ] Связать sampling с reproducibility и security

---

## 1. От Logits к Tokens

### 1.1 Model Output: Logits

```rust
use candle_core::Tensor;

// Model возвращает logits для каждого token в vocabulary
let logits = model.forward(&input_ids)?;  // [batch, seq_len, vocab_size]
                                           // [1, 10, 50257] для GPT-2

// logits[-1] = scores для следующего token
let seq_len = logits.dim(1)?;
let next_logits = logits.narrow(1, seq_len - 1, 1)?.squeeze(1)?;  // [50257]
```

### 1.2 Softmax → Probabilities

```rust
use candle_core::{Tensor, D};
use candle_nn::ops::softmax;

let probs = softmax(&next_logits, D::Minus1)?;
// probs[i] = probability token i

// Example:
// probs[15496] = 0.15  // "Hello"
// probs[42] = 0.08     // "the"
// probs[...] = ...
```

---

## 2. Sampling Strategies

### 2.1 Greedy Decoding

**Идея:** Всегда выбирать token с максимальной probability.

```rust
use candle_core::{Tensor, D};

fn greedy(logits: &Tensor) -> candle_core::Result<Tensor> {
    logits.argmax(D::Minus1)
}

// Pros: Deterministic, fast
// Cons: Boring, repetitive output
```

### 2.2 Temperature

**Идея:** Контроль "sharpness" распределения.

```rust
use candle_core::{Tensor, D};
use candle_nn::ops::softmax;

fn sample_with_temperature(logits: &Tensor, temperature: f64) -> candle_core::Result<Tensor> {
    let scaled_logits = (logits / temperature)?;
    let probs = softmax(&scaled_logits, D::Minus1)?;
    probs.multinomial(1)
}

// temperature = 0.1: Almost greedy (confident)
// temperature = 1.0: Original distribution
// temperature = 2.0: More random (creative)
```

### 2.3 Top-K Sampling

**Идея:** Sample только из K most probable tokens.

```rust
use candle_core::{Tensor, D};
use candle_nn::ops::softmax;

fn top_k(logits: &Tensor, k: usize) -> candle_core::Result<Tensor> {
    let (values, indices) = logits.topk(k)?;
    let probs = softmax(&values, D::Minus1)?;
    let chosen_idx = probs.multinomial(1)?;
    indices.gather(&chosen_idx, D::Minus1)
}
```

### 2.4 Top-P (Nucleus) Sampling

**Идея:** Sample из minimum set tokens с cumulative probability >= p.

```rust
use candle_core::{Tensor, D};
use candle_nn::ops::softmax;

fn top_p(logits: &Tensor, p: f64) -> candle_core::Result<Tensor> {
    let (sorted_logits, sorted_indices) = logits.sort(D::Minus1, true)?; // descending
    let cumulative_probs = softmax(&sorted_logits, D::Minus1)?.cumsum(D::Minus1)?;

    // Find cutoff — zero everything after cumulative prob > p
    let mask = cumulative_probs.le(p)?;
    let neg_inf = f32::NEG_INFINITY;
    let sorted_logits = sorted_logits.where_cond(
        &mask,
        &Tensor::new(neg_inf, logits.device())?.broadcast_as(sorted_logits.shape())?,
    )?;
    let probs = softmax(&sorted_logits, D::Minus1)?;

    let chosen_idx = probs.multinomial(1)?;
    sorted_indices.gather(&chosen_idx, D::Minus1)
}
```

### 2.5 Сравнение стратегий

| Стратегия | Creativity | Coherence | Use Case |
|-----------|------------|-----------|----------|
| **Greedy** | Low | High | Code, facts |
| **Temp=0.3** | Low-Med | High | Balanced |
| **Temp=1.0** | Medium | Medium | Creative |
| **Top-k=50** | Medium | Good | General |
| **Top-p=0.9** | Adaptive | Good | Recommended |

---

## 3. Practical Usage

```rust
use candle_core::Device;
use tokenizers::Tokenizer;

fn main() -> candle_core::Result<()> {
    let device = Device::Cpu;
    let tokenizer = Tokenizer::from_pretrained("gpt2", None).unwrap();

    // let model = candle_transformers::models::gpt2::Model::load("gpt2", &device)?;

    // Different sampling strategies
    // let outputs = model.generate(
    //     &input_ids,
    //     50,          // max_new_tokens
    //     true,        // do_sample
    //     0.7,         // temperature
    //     50,          // top_k
    //     0.9,         // top_p
    //     1.1,         // repetition_penalty
    // )?;

    Ok(())
}
```

---

## 4. Security Implications

### 4.1 Reproducibility

```rust
// Problem: random sampling не reproducible
// Rust: используем seed для детерминированности
use rand::SeedableRng;

let mut rng1 = rand::rngs::StdRng::seed_from_u64(42);
// let output1 = model.generate_with_rng(&mut rng1, ...)?;

let mut rng2 = rand::rngs::StdRng::seed_from_u64(42);
// let output2 = model.generate_with_rng(&mut rng2, ...)?;

// output1 == output2 только если seed тот же!
```

### 4.2 Sampling Manipulation

```rust
// Temperature влияет на probability harmful outputs
// Low temp: Model follows training distribution
// High temp: Increases probability rare tokens

// Некоторые jailbreaks exploit high temperature
```

---

## 5. Summary

1. **Logits → Probabilities:** softmax conversion
2. **Greedy:** Deterministic, boring
3. **Temperature:** Control randomness
4. **Top-k/Top-p:** Limit vocabulary
5. **Security:** Reproducibility, manipulation

---

## Следующий урок

→ [Module README](README.md)

---

*AI Security Academy | Трек 01: AI Fundamentals | Модуль 01.3: Key Concepts*
