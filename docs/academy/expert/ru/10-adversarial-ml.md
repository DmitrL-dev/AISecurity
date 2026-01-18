# ⚔️ Урок 3.1: Adversarial ML

> **Время: 50 минут** | Expert Module 3

---

## Adversarial Examples

Inputs designed to fool ML models:

```python
# Original: "Hello" → Safe
# Adversarial: "H​e​l​l​o" (zero-width chars) → Still safe, but bypasses detection
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

```python
def fgsm_attack(model, x, y, epsilon=0.1):
    """Fast Gradient Sign Method attack."""
    x.requires_grad = True
    output = model(x)
    loss = F.cross_entropy(output, y)
    loss.backward()
    
    perturbation = epsilon * x.grad.sign()
    x_adv = x + perturbation
    
    return x_adv
```

---

## Defense: Adversarial Training

```python
def adversarial_training(model, data_loader, epsilon=0.1):
    for x, y in data_loader:
        # Generate adversarial examples
        x_adv = fgsm_attack(model, x, y, epsilon)
        
        # Train on both clean and adversarial
        loss_clean = F.cross_entropy(model(x), y)
        loss_adv = F.cross_entropy(model(x_adv), y)
        
        loss = 0.5 * loss_clean + 0.5 * loss_adv
        loss.backward()
        optimizer.step()
```

---

## Следующий урок

→ [3.2: Robustness](./11-robustness.md)
