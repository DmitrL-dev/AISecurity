# AISecurity

**Free, open tools to learn how AI applications get attacked, test a guard on your own data, and check what
a security test result can actually prove.** Academy in English and Russian.

Protecting a live application? **[Spectorn](https://spectorn.ai/)** is the maintained product from the same team.

![AISecurity — Understand the attack. Build the defense. Learn, inspect, evaluate.](docs/images/aisecurity-banner.webp)

[![CI](https://github.com/DmitrL-dev/AISecurity/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/DmitrL-dev/AISecurity/actions/workflows/ci.yml?query=branch%3Amain)
[![eval-bounds](https://github.com/DmitrL-dev/AISecurity/actions/workflows/eval-bounds.yml/badge.svg?branch=main)](https://github.com/DmitrL-dev/AISecurity/actions/workflows/eval-bounds.yml?query=branch%3Amain)
[![License](https://img.shields.io/github/license/DmitrL-dev/AISecurity)](LICENSE)

## Start with what you need

| You want to | Start here | What it takes |
| --- | --- | --- |
| Understand prompt injection, RAG, agent and memory attacks | [Academy in English](docs/academy/en/index.md) · [Академия на русском](docs/academy/ru/index.md) | A browser |
| Decide whether an agent may act on content it retrieved | [60-second decision room](https://dmitrl-dev.github.io/AISecurity/agent-action-room.html) | One minute |
| Know whether «none of 50 attacks got through» proves anything | [eval-bounds](tools/eval-bounds/README.md) | One command, Python only |
| Measure a guard on your own labelled prompts | [Guard Lab](tools/guard-lab/README.md#install-linux-x86-64--python-311) | Linux x86-64, Python 3.11 |
| Protect a live application | [Spectorn](https://spectorn.ai/) | The maintained product |

## Try it now

```console
$ python3 tools/eval-bounds/rate_bounds.py claim 0 50 --tau 0.01
0/50 = 0.0000%; one-sided 95% bounds [0.0000%, 5.8155%]; tau 1.0000%: INCONCLUSIVE (with no event, 299 independent trials reach tau)
```

Fifty clean runs are compatible with a 5.8% bypass rate. Before anyone quotes «blocks 99%», ask how many
independent attacks stood behind it. [eval-bounds](tools/eval-bounds/README.md) gives the exact bound, the
sample size a claim needs, and a paired test for «did the fix help».

## Learn the failure modes

AI security is the boundary between untrusted content, model behavior, tools, memory and the actions an
application can take. The academy walks it from prompt injection and the OWASP lists to agent loops, tool
permissions, RAG, detection engineering and research, with exercises beside the source.

| Boundary | English | Русский |
| --- | --- | --- |
| Instructions hidden in data | [Prompt injection](docs/academy/en/beginner/01-prompt-injection.md) | [Prompt injection](docs/academy/ru/beginner/01-prompt-injection.md) |
| Documents retrieved into context | [RAG security](docs/academy/en/beginner/09-rag-security.md) | [Безопасность RAG](docs/academy/ru/beginner/09-rag-security.md) |
| Model output becoming an action | [Tool-using agents](docs/academy/en/intermediate/agentic/tool-using-agents.md) | [Агенты с инструментами](docs/academy/ru/intermediate/agentic/tool-using-agents.md) |
| Context stored for future use | [Agent memory](docs/academy/en/intermediate/agentic/memory.md) | [Память агентов](docs/academy/ru/intermediate/agentic/memory.md) |

[Hands-on labs](docs/academy/en/labs/index.md) · [Agent action evaluation checklist](docs/agent-action-evaluation.md)

## Test a guard on your own data

**Guard Lab** takes labelled JSONL and reports misses, false positives and execution failures separately.
Reports omit input text, text hashes and matched excerpts, and an error never quietly becomes a benign
prediction. No account, API key or GPU; after installation, evaluations stay on your machine.

```bash
guard-lab --demo
```

The demo checks the plumbing on four synthetic inputs; it is not a benchmark. Replace it with your own
labelled prompts and read coverage and errors alongside the confusion counts. Guard Lab uses eight public
pattern engines, not current Spectorn engines. [Install and run →](tools/guard-lab/README.md)

## Protect a live application

**[Spectorn](https://spectorn.ai/)** is the maintained protection layer from the same team. It sits around
prompts, model responses and agent actions, decides on every request, and records each verdict in a
content-free audit. Choose your region on the site to see the current protection scope and access options.

This repository is not a download of the commercial platform, its private corpora or its current detectors.
It is where we teach the problem and publish the tools to check anyone's claims about it, ours included.

**[Open Spectorn →](https://spectorn.ai/)**

## What is in this repository

| Part | Status |
| --- | --- |
| [Academy](docs/academy/en/index.md), English and Russian | Maintained |
| [eval-bounds](tools/eval-bounds/README.md) | New, maintained, tested in CI |
| [Guard Lab](tools/guard-lab/README.md) | Maintained |
| [Public core 2.0.1](sentinel-core/) | Frozen legacy snapshot; 48 authored regression cases, not a detection benchmark |
| Engine catalogue, research notes, older articles | Historical; earlier figures are not current performance claims |

<details>
<summary>Scope, provenance and safe use</summary>

- Guard Lab evaluates inputs through the pinned, already-public `EngineRegistry.analyze_patterns` endpoint. It
  is not a hosted gateway, an output guard or an evaluation of the full legacy engine catalogue.
- The native worker has process and resource limits; it is not a sandbox for untrusted native code. Read the
  [full contract](tools/guard-lab/README.md).
- Older detection percentages, performance comparisons and installation routes in the archive have not been
  revalidated. Treat them as historical reports.
- Use labs and red-team tools only on systems you own or are explicitly authorized to test. Do not post real
  secrets, customer prompts or private corpora in issues.
- Earlier Syntrex-era material and the [GoMCP organization](https://github.com/syntrex-lab/gomcp) remain
  discoverable for historical context.

</details>

## Contribute

Useful contributions are concrete: a clearer lesson, a reproducible installation bug, an incorrect number, or
a minimal synthetic test case. Say what you expected, what happened and the smallest safe example that
reproduces it. Start with the [contribution guide](docs/CONTRIBUTING.md) and
[open an issue](https://github.com/DmitrL-dev/AISecurity/issues).

**[Documentation](docs/README.md)** · [Security reports](SECURITY.md) · [Code of conduct](CODE_OF_CONDUCT.md) · [How to cite](CITATION.cff) · [License](LICENSE)
