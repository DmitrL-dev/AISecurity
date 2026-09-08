# AISecurity — Guard Lab and legacy archive

## New: local input evaluation with Guard Lab

[Guard Lab](tools/guard-lab/README.md) evaluates your labelled JSONL inputs with
the pinned, already-public AISecurity pattern endpoint. It reports TP/TN/FP/FN
and execution errors without including input text. Linux / Python 3.11 first;
no account, API key, hosted inference or GPU required.

Start with the [installation and synthetic demo](tools/guard-lab/README.md#install-linux-x86-64--python-311).
This is a bounded evaluation tool, **not** a new production guardrail or a
release of current Spectorn engines. The synthetic demo is not a benchmark.
The older components and installation routes below remain legacy material;
their presence does not imply that they have been revalidated by this work.

---

## SYNTREX Legacy Archive (2024-2026)

> The earlier platform in this repository is legacy material. Guard Lab above
> is a separate, narrow contribution. Platform development moved to Syntrex AI SOC.
>
> 👉 **New Home:** [github.com/syntrex-lab](https://github.com/syntrex-lab)
> 👉 **Core Component:** [github.com/syntrex-lab/gomcp](https://github.com/syntrex-lab/gomcp)
> 👉 **Website:** [syntrex.pro](https://syntrex.pro)

---

## 🚀 Where to find the active components?
### 1. GoMCP (Open Source Core)
🔗 **[github.com/syntrex-lab/gomcp](https://github.com/syntrex-lab/gomcp)**
*   ✅ Apache 2.0 License
*   ✅ MCP Protocol Support

### 2. Syntrex AI SOC (Enterprise Platform)
🔗 **[spectorn.ai](https://spectorn.ai)**

---
**Status:** Guard Lab contribution + legacy platform archive | **Platform successor:** [Syntrex AI SOC](https://syntrex.pro)
