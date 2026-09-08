# AISecurity

**[Spectorn — live AI protection](https://spectorn.ai/)** · [Explore the project](https://dmitrl-dev.github.io/AISecurity/) · [Academy EN](docs/academy/en/index.md) · [Академия RU](docs/academy/ru/index.md) · [Guard Lab](tools/guard-lab/README.md)

![AISecurity — Understand the attack. Build the defense. Learn, inspect, evaluate.](docs/images/aisecurity-banner.webp)

**An open-source lab for AI security: learn the failure modes, inspect the defenses, and evaluate your own inputs.**

AI security is more than a filter on a prompt. It is the boundary between untrusted
content, model behavior, tools, memory and the actions an application can take.
AISecurity brings the learning material, public implementation and experiments
into one place — so you can study the problem and test the assumptions yourself.

## One lab. Three ways in.

### Learn the failure modes

Follow the **English or Russian academy** from prompt injection and OWASP basics
to agent loops, tool permissions, memory, RAG, detection engineering and research.
Explore the exercises alongside the source, not just a slide deck.

**[Start in English](docs/academy/en/index.md)** · **[Начать на русском](docs/academy/ru/index.md)** · [Hands-on labs](docs/academy/en/labs/index.md)

### Inspect the mechanisms

Read the public Rust implementation, trace its architecture, explore red-team
tooling and inspect the research behind the earlier platform. Use the code and
technical notes to understand how a defense works — and where its assumptions end.

**[Native core](sentinel-core/)** · [Architecture](docs/ARCHITECTURE.md) · [Research notes](docs/rnd/) · [STRIKE research tools](strike/)

### Evaluate your inputs

**Guard Lab is the new local evaluation path.** Give it labelled JSONL and inspect
misses, false positives and execution failures separately. Reports omit input text,
text hashes and matched excerpts; errors never quietly become benign predictions.

```text
Your labelled JSONL → validation + duplicate checks → pinned public core
                                                     ↓
                             confusion counts + coverage + explicit errors
```

**[Install Guard Lab and run the demo](tools/guard-lab/README.md#install-linux-x86-64--python-311)** · [Input format](tools/guard-lab/README.md#evaluate-your-data) · [Report contract](tools/guard-lab/README.md#read-the-report)

Linux x86-64 / Python 3.11 first. No account, API key or GPU. Installation downloads
dependencies and builds native code; subsequent evaluations are local. The small
synthetic demo checks plumbing — **not a benchmark** or a promise of detection quality.

## Need a live protection layer? Explore Spectorn.

**[Spectorn](https://spectorn.ai/)** is the current product for protection around
prompts, model responses and agent workflows. Visit the site, choose your region,
and check the current protection scope and access options.

Use AISecurity to learn, inspect and experiment. Explore Spectorn when you want a
maintained service around your AI application. This repository is not a download
of the commercial platform, its private corpora or its current detectors.

**[Open Spectorn →](https://spectorn.ai/)**

## Open source. Clear boundaries.

Guard Lab is the newly verified contribution. The academy, engines and research
remain available as historical resources. They are **not current Spectorn engines**
or a newly certified production stack.

<details>
<summary>Read scope, provenance and legacy notes</summary>

- Guard Lab evaluates inputs using **eight pattern engines** through the pinned,
  already-public `EngineRegistry.analyze_patterns` endpoint. It is not a hosted
  gateway, output guard or evaluation of the full legacy engine catalogue.
- Older detection percentages, performance comparisons and installation routes
  in the archive have not been revalidated by this contribution. Treat them as
  historical reports, not current performance claims.
- The native worker has process and resource limits; it is not a sandbox for
  untrusted native code. Read the [full contract](tools/guard-lab/README.md).
- Use labs and red-team tools only on systems you own or are explicitly authorized
  to test. Do not post real secrets, customer prompts or private corpora in issues.
- Earlier Syntrex-era material and the [GoMCP organization](https://github.com/syntrex-lab/gomcp)
  remain discoverable for historical context. The current product link is
  [Spectorn](https://spectorn.ai/).

</details>

## Build with us

Useful contributions are concrete: a clearer lesson, a reproducible installation
bug, an incorrect metric, or a minimal synthetic test case. Start with the
[contribution guide](docs/CONTRIBUTING.md) and
[open an issue](https://github.com/DmitrL-dev/AISecurity/issues).

**[Documentation](docs/README.md)** · [Security reports](SECURITY.md) · [License](LICENSE)
