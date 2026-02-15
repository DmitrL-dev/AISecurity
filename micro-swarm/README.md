# micro-swarm

**Micro-Model Swarm** — lightweight ML ensemble framework. Pure Python, zero dependencies, <1ms inference.

## Install

```bash
pip install micro-swarm
```

## Quick Start

```python
from micro_swarm import load_preset

# Security — Prompt Injection Detection
swarm = load_preset("security")
result = swarm.predict({"entropy": 0.9, "special_char_ratio": 0.3})
print(f"Score: {result.final_score:.3f}")  # 0.0=safe, 1.0=threat

# Available presets: adtech, security, fraud, strike
```

## Architecture

Each preset = 3 domain-specialized micro-transformers (~1500 params each):
- **AdTech**: timing, geo, device
- **Security**: token_pattern, semantic_shift, behavioral
- **Fraud**: velocity, amount, pattern  
- **Strike**: stealth_timing, fingerprint, behavioral_mimicry

## License

MIT
