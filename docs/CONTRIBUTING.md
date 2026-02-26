# Contributing to Sentinel

## Quick Start

1. Fork the repository
2. Clone: `git clone https://github.com/YOUR_USERNAME/AISecurity.git`
3. Create branch: `git checkout -b feature/your-feature`
4. Make changes and test
5. Submit PR

## Development Setup

### Rust (sentinel-core)

```bash
cd sentinel-core
cargo build --release
cargo test --lib          # 1101 tests
```

### Python (brain, strike, micro-swarm)

```bash
pip install -r requirements.txt
pytest tests/ -v
```

## Creating a New Engine

All detection engines are in `sentinel-core/src/engines/`. Follow the existing pattern:

```rust
// sentinel-core/src/engines/my_engine.rs

use aho_corasick::AhoCorasick;
use once_cell::sync::Lazy;
use regex::Regex;
use super::MatchResult;

// 1. Fast keyword pre-filter
static HINTS: Lazy<AhoCorasick> = Lazy::new(|| {
    AhoCorasick::builder()
        .ascii_case_insensitive(true)
        .build(["keyword1", "keyword2"])
        .expect("hints")
});

// 2. Detailed regex patterns: (regex, name, confidence)
static PATTERNS: Lazy<Vec<(Regex, &'static str, f64)>> = Lazy::new(|| {
    vec![
        (Regex::new(r"(?i)your_pattern_here").expect("regex"), "pattern_name", 0.90),
    ]
});

// 3. Engine struct
pub struct MyEngine;
impl MyEngine {
    pub fn new() -> Self { Self }
    pub fn scan(&self, text: &str) -> Vec<MatchResult> {
        if text.is_empty() || !HINTS.is_match(text) {
            return Vec::new();
        }
        let mut matches = Vec::new();
        for (regex, name, confidence) in PATTERNS.iter() {
            for mat in regex.find_iter(text) {
                matches.push(MatchResult {
                    engine: "my_engine".to_string(),
                    pattern: name.to_string(),
                    confidence: *confidence,
                    start: mat.start(),
                    end: mat.end(),
                });
            }
        }
        matches
    }
}

// 4. Trait implementation
impl super::traits::PatternMatcher for MyEngine {
    fn name(&self) -> &'static str { "my_engine" }
    fn scan(&self, text: &str) -> Vec<MatchResult> { self.scan(text) }
    fn category(&self) -> super::traits::EngineCategory {
        super::traits::EngineCategory::Security
    }
}

// 5. Tests
#[cfg(test)]
mod tests {
    use super::*;
    use crate::engines::traits::PatternMatcher;

    #[test]
    fn test_detection() {
        let engine = MyEngine::new();
        let matches = engine.scan("text containing keyword1 pattern");
        assert!(!matches.is_empty());
    }

    #[test]
    fn test_benign() {
        let engine = MyEngine::new();
        assert!(engine.scan("normal safe text").is_empty());
    }

    #[test]
    fn test_empty() {
        let engine = MyEngine::new();
        assert!(engine.scan("").is_empty());
    }
}
```

Then register in `sentinel-core/src/engines/mod.rs` at 4 points:
1. `pub mod my_engine;`
2. Struct field: `my_engine: Option<my_engine::MyEngine>,`
3. In `new()`: `my_engine: Some(my_engine::MyEngine::new()),`
4. In `analyze()`: `run_engine!(self.my_engine);`

## Important Rules

- **No look-ahead/look-behind** in regex — Rust's `regex` crate doesn't support `(?!...)` or `(?=...)`
- **Tests required** — every engine must have tests for detection, benign input, and empty input
- **AhoCorasick pre-filter** — always include a fast keyword check before expensive regex
- Run `cargo test --lib` and verify 0 failures before submitting

## Code Standards

| Language | Standard | Verify |
|----------|----------|--------|
| Rust | `cargo clippy` | `cargo test --lib` |
| Python | PEP 8 | `pytest tests/ -v` |
| C | C11 strict | `make test` in shield/ |

## What to Contribute

| Area | Location | Description |
|------|----------|-------------|
| Detection engines | `sentinel-core/src/engines/` | New Rust detection engines |
| Attack payloads | `strike/` | New attack patterns for testing |
| Academy content | `docs/academy/` | Educational materials (EN/RU) |
| Tests | `sentinel-core/` | Expand test coverage |
| Bug fixes | Any | With tests |

## Questions?

- **Email:** chg@live.ru
- **Telegram:** [@DmLabincev](https://t.me/DmLabincev)
- **Issues:** [github.com/DmitrL-dev/AISecurity/issues](https://github.com/DmitrL-dev/AISecurity/issues)
