# ⚔️ Урок 3.1: Adversarial ML

> **Время: 50 минут** | Expert Module 3

---

## Adversarial Examples

Inputs designed to fool ML models:

```rust
// Original: "Hello" → Safe
// Adversarial: "H​e​l​l​o" (zero-width chars) → Still safe, but bypasses detection
```

---

## Attack Types

| Attack | Goal | Method |
|--------|------|--------|
| **Evasion** | Bypass detector | Perturbation |
| **Poisoning** | Corrupt training | Malicious data |
| **Extraction** | Steal model | Query access |

---

## FGSM Attack

```rust
use candle_core::Tensor;

fn fgsm_attack(
    model: &dyn Model,
    x: &Tensor,
    y: &Tensor,
    epsilon: f64,
) -> Tensor {
    /// Fast Gradient Sign Method attack.
    let output = model.forward(x);
    let loss = cross_entropy(&output, y);
    let grad = loss.backward(x);

    let perturbation = grad.sign().affine(epsilon, 0.0);
    let x_adv = x.add(&perturbation).unwrap();

    x_adv
}
```

---

## Defense: Adversarial Training

```rust
fn adversarial_training(
    model: &mut dyn Model,
    data_loader: &DataLoader,
    epsilon: f64,
) {
    for (x, y) in data_loader.iter() {
        // Generate adversarial examples
        let x_adv = fgsm_attack(model, &x, &y, epsilon);

        // Train on both clean and adversarial
        let loss_clean = cross_entropy(&model.forward(&x), &y);
        let loss_adv = cross_entropy(&model.forward(&x_adv), &y);

        let loss = (loss_clean * 0.5 + loss_adv * 0.5).unwrap();
        loss.backward();
        optimizer.step();
    }
}
```

---

## Следующий урок

→ [3.2: Robustness](./11-robustness.md)
