# Sentinel Academy

Welcome to the **Sentinel Academy** — your path to mastering AI security.

## Choose Your Level

| Level | For Whom | Topics |
|-------|----------|--------|
| [**Beginner**](beginner/index.md) | Developers, students | Prompt injection, OWASP basics, first integration |
| [**Intermediate**](intermediate/index.md) | Security engineers | Attack vectors, agentic security, production deployment |
| [**Advanced**](advanced/index.md) | Researchers, contributors | TDA, formal methods, engine development, CVE analysis |
| [**Labs**](labs/index.md) | Everyone | Hands-on blue team & red team exercises |

## About Sentinel

Sentinel is an open-source AI security platform with **59 Rust detection engines** and **8 novel Sentinel Lattice primitives** — formal-methods security properties not found in any other tool.

- **1101 tests**, 0 failures
- **<1ms** per engine — Aho-Corasick pre-filter + compiled regex
- **OWASP LLM Top 10 + Agentic Top 10** coverage

## Getting Started

```bash
git clone https://github.com/DmitrL-dev/AISecurity.git
cd AISecurity/sentinel-core
cargo test
```

---

*[GitHub](https://github.com/DmitrL-dev/AISecurity) · [Engine Reference](../../reference/engines-en.md) · [arXiv Paper](../../papers/sentinel-lattice/main.pdf)*
