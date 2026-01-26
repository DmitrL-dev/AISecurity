# Mathematical Foundations

> **Подмодуль 06.3: Математика за AI Security**

---

## Обзор

Этот подмодуль предоставляет строгие математические основы для AI security. Понимание этих концепций позволяет анализировать эффективность атак, доказывать свойства защит и разрабатывать novel техники.

---

## Темы

| Тема | Применение |
|------|------------|
| **Information Theory** | Quantification leakage, entropy analysis |
| **Statistical Detection** | Optimal thresholds, hypothesis testing |
| **Adversarial Robustness** | Attack/defense bounds |
| **Complexity Theory** | Hardness of detection problems |

---

## Уроки

### 01. Information Theory for Security
**Время:** 45 минут | **Сложность:** �������

- Entropy и mutual information
- Information leakage metrics
- Channel capacity для атак
- Differential privacy foundations

### 02. Statistical Detection Theory
**Время:** 50 минут | **Сложность:** �������

- Hypothesis testing для атак
- ROC curves и threshold selection
- Применение Neyman-Pearson lemma
- CUSUM для change detection

### 03. Adversarial Robustness Theory
**Время:** 55 минут | **Сложность:** �������

- Attack success probability bounds
- Defense certification
- Lipschitz constraints
- Randomized smoothing

### 04. Computational Complexity
**Время:** 45 минут | **Сложность:** �������

- Hardness of detection problems
- Complexity of attack generation
- Reduction-based security arguments
- Practical implications

---

## Ключевые теоремы

### Detection Bounds
```
P(detect | attack) ≥ 1 - exp(-n · D(P_attack || P_benign))

Where D is KL divergence, n is sample size
```

### Robustness Certification
```
If ||x - x'|| < ε, then |f(x) - f(x')| < L · ε

For L-Lipschitz function f
```

---

## Предварительные требования

- Calculus (derivatives, integrals)
- Probability theory (distributions, expectations)
- Linear algebra (eigenvalues, SVD)
- Basic real analysis helpful

---

## Гид по нотации

| Symbol | Meaning |
|--------|---------|
| H(X) | Shannon entropy |
| I(X;Y) | Mutual information |
| D(P\|\|Q) | KL divergence |
| ε | Perturbation bound |
| δ | Failure probability |

---

## Навигация

| Предыдущий | Текущий | Следующий |
|------------|---------|-----------|
| [TDA Detection](../02-detection-tda/) | **Mathematical Foundations** | [Governance](../../07-governance/) |

---

*AI Security Academy | Подмодуль 06.3*
