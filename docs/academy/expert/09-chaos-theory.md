# 🌪️ Урок 2.5: Chaos Theory

> **Время: 45 минут** | Expert Module 2 — Strange Math™

---

## Introduction

**Chaos Theory** studies systems sensitive to initial conditions. Injections create "chaos" in otherwise stable text dynamics.

---

## Lyapunov Exponents

Measure how fast nearby trajectories diverge:

```python
def lyapunov_exponent(sequence: List[float]) -> float:
    """Compute Lyapunov exponent of sequence."""
    n = len(sequence)
    lyap = 0.0
    
    for i in range(n - 1):
        diff = abs(sequence[i+1] - sequence[i])
        if diff > 0:
            lyap += np.log(diff)
    
    return lyap / n
```

---

## Detection via Stability

```python
class ChaosDetector(BaseEngine):
    """Detect injections via chaotic dynamics."""
    
    def scan(self, text: str) -> ScanResult:
        # Convert text to time series (embedding trajectory)
        chunks = self.split_text(text)
        embeddings = [self.embed(c) for c in chunks]
        
        # Project to 1D for Lyapunov analysis
        trajectory = [e.mean() for e in embeddings]
        
        # Compute Lyapunov exponent
        lyap = self.lyapunov_exponent(trajectory)
        
        # High positive Lyapunov = chaotic = injection
        if lyap > self.chaos_threshold:
            return ScanResult(
                is_threat=True,
                confidence=min(lyap, 1.0),
                details=f"Lyapunov exponent: {lyap}"
            )
        
        return ScanResult(is_threat=False)
```

---

## Phase Space Reconstruction

```python
def reconstruct_phase_space(series, dim=3, tau=1):
    """Takens embedding for phase space reconstruction."""
    n = len(series) - (dim - 1) * tau
    return np.array([
        [series[i + j * tau] for j in range(dim)]
        for i in range(n)
    ])
```

---

## Следующий урок

→ [3.1: Adversarial ML](./10-adversarial-ml.md)
