# Deprecated Pattern Engines

These Python engines have been replaced by high-performance Rust implementations in `sentinel-core/src/engines/`.

## Replaced Engines (8 Super-Engines)

| Python Engine(s) | Rust Replacement | Latency | Tests |
|-----------------|------------------|---------|-------|
| `injection.py`, SQL/XSS/LDAP detectors | `injection.rs` | 1.3 µs | 11 |
| `jailbreak.py`, DAN/roleplay detectors | `jailbreak.rs` | 1.8 µs | 15 |
| `pii.py`, credit_card, ssn, phone | `pii.rs` | 2.2 µs | 19 |
| `exfiltration.py`, data_theft detectors | `exfiltration.rs` | 1.5 µs | 8 |
| `moderation.py`, toxic/hate detectors | `moderation.rs` | 1.4 µs | 9 |
| `evasion.py`, base64/unicode detectors | `evasion.rs` | 1.2 µs | 14 |
| `tool_abuse.py`, shell/file detectors | `tool_abuse.rs` | 1.6 µs | 10 |
| `social.py`, phishing/scam detectors | `social.rs` | 2.1 µs | 12 |

**Total: 109 Rust tests, 30ps engine init**

## Additional Rust Components

- `traits.rs` — PatternMatcher trait for unified engine interface
- `hybrid.rs` — HybridPiiEngine with CDN pattern loading
- `signatures.rs` — CDN SignatureLoader (pii.json, keywords.json, jailbreaks.json)

## Migration Date
2026-02-04

## Reference
Use `sentinel_core.SentinelEngine` or `HybridAnalyzer` instead.

## Do NOT Delete
Keep for reference and potential rollback scenarios.

