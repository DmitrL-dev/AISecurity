# SENTINEL Core

High-performance AI security detection engine written in Rust with Python bindings.

## Features

- **8 Super-Engines** consolidating 220 Python detection engines
- **Aho-Corasick** keyword pre-filtering (O(n))
- **Tiered matching**: keywords → regex only for candidates
- **Unicode normalization**: fullwidth, HTML entities, URL encoding, zero-width removal
- **PyO3/maturin** Python bindings with type stubs

## Installation

```bash
# Development build
maturin develop --release

# Build wheel
maturin build --release
```

## Usage

```python
import sentinel_core

# Quick scan
result = sentinel_core.quick_scan("Hello, ignore previous instructions")
print(f"Detected: {result.detected}, Risk: {result.risk_score}")

# Full engine
engine = sentinel_core.SentinelEngine()
result = engine.analyze("SELECT * FROM users WHERE id='1' OR '1'='1'")
for match in result.matches:
    print(f"  {match.engine}: {match.pattern} ({match.confidence})")
```

## Super-Engines

| Engine | Category | Patterns |
|--------|----------|----------|
| InjectionEngine | SQL, NoSQL, Command, LDAP, XPath | ~50 |
| JailbreakEngine | DAN, roleplay, ignore-previous | ~30 |
| PIIEngine | SSN, CC, phone, email, address | ~25 |
| ExfiltrationEngine | URL leak, file read, secret extraction | ~20 |
| ModerationEngine | violence, hate, NSFW | ~20 |
| EvasionEngine | Base64, Unicode, homoglyphs | ~15 |
| ToolAbuseEngine | MCP exploit, unauthorized exec | ~15 |
| SocialEngine | phishing, manipulation | ~12 |

## Performance

| Metric | Python | Rust |
|--------|--------|------|
| Latency (p99) | 50-100ms | 1-5ms |
| Throughput | 20 req/s | 500+ req/s |
| Memory | 300MB | 50MB |

## License

Apache-2.0
