# AISecurity documentation

[Project home](https://dmitrl-dev.github.io/AISecurity/) · **[Spectorn](https://spectorn.ai/)** · [Academy EN](academy/en/index.md) · [Академия RU](academy/ru/index.md) · [Guard Lab](../tools/guard-lab/README.md)

Learn the failure modes, inspect the public mechanisms and evaluate your own inputs.
Start with the [new local Guard Lab](../tools/guard-lab/README.md) for a pinned,
documented evaluation path, or choose an academy track for English/Russian lessons.
The platform documentation below is historical: engine counts, performance figures
and old installation instructions are not fresh verification of a production stack.

---

## Structure

```
docs/
├── rnd/                         R&D notes and architecture design
│   ├── sentinel-lattice-architecture.md    Full Sentinel Lattice architecture (1430 lines)
│   ├── sentinel-lattice-announcements.md   Launch announcement templates
│   ├── deep-research.md                    Cross-domain research findings
│   └── full-research.md                    Initial research compilation
│
├── reference/                   Technical reference
│   ├── engines-en.md            All 61 engines — English
│   ├── engines.md               All 61 engines — Russian
│   ├── api.md                   REST API reference
│   ├── compliance.md            Compliance mapping
│   ├── design-review.md         Design review process
│   ├── micro-swarm.md           ML ensemble reference
│   └── requirements.md          System requirements
│
├── academy/                     Educational content
│   ├── ru/                      Full Russian curriculum (8 modules)
│   ├── expert/en/               Expert track — English (21 lessons)
│   ├── expert/ru/               Expert track — Russian (22 lessons)
│   └── labs/                    Hands-on exercises with attack targets
│
├── security/                    Security advisories
│   └── QWEN-2026-001-advisory.md
│
├── images/                      Diagrams and figures
│
├── ARCHITECTURE.md              Platform architecture overview
├── CHANGELOG.md                 Version history
├── COMPARISON.md                Competitive comparison
├── CONTRIBUTING.md              How to contribute
└── owasp_agentic_mapping.md     OWASP Agentic AI coverage
```

---

## Key Documents

| Document | Description |
|----------|-------------|
| [Architecture](./ARCHITECTURE.md) | Platform components, detection cascade, data flow |
| [Engine Reference (EN)](./reference/engines-en.md) | All 61 engines with categories and descriptions |
| [Sentinel Lattice Architecture](./rnd/2026-02-25-sentinel-lattice-architecture.md) | Full design of 7 novel security primitives |
| [OWASP Mapping](./owasp_agentic_mapping.md) | Coverage of OWASP Agentic AI Top 10 |
| [API Reference](./reference/api.md) | REST API endpoints and examples |
| [Changelog](./CHANGELOG.md) | Release history |

---

## Getting Started

For the newly verified local evaluation path, use the
[Guard Lab installation guide](../tools/guard-lab/README.md#install-linux-x86-64--python-311).
The root [QUICKSTART.md](../QUICKSTART.md) remains a legacy platform reference.

## Contact

- **Issues:** [github.com/DmitrL-dev/AISecurity/issues](https://github.com/DmitrL-dev/AISecurity/issues)
- **Telegram:** [@DmLabincev](https://t.me/DmLabincev)
- **Email:** chg@live.ru
