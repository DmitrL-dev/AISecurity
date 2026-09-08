# AISecurity Academy

**[Русская версия](../ru/index.md)** · [Project home](https://dmitrl-dev.github.io/AISecurity/) · [Spectorn](https://spectorn.ai/)

**Learn where an AI system crosses a trust boundary — and what can go wrong there.**

Start with a concrete failure mode, follow the references into the public source,
then explore the exercises. You do not need to install anything to read the academy.

## Pick your first boundary

| Start here | What you will study |
| --- | --- |
| [Prompt injection](beginner/01-prompt-injection.md) | How instructions cross a data boundary |
| [RAG and untrusted documents](beginner/09-rag-security.md) | What retrieval can bring into the context |
| [Tool-using agents](intermediate/agentic/tool-using-agents.md) | Where model output becomes an action |
| [Agent memory](intermediate/agentic/memory.md) | How stored context becomes an attack surface |

## Follow a track

| Level | For whom | Topics |
| --- | --- | --- |
| [Beginner](beginner/index.md) | Developers and students | Prompt injection, OWASP basics, integration concepts |
| [Intermediate](intermediate/index.md) | Security engineers | Attack vectors, agent security, deployment patterns |
| [Advanced](advanced/index.md) | Researchers and contributors | TDA, formal methods, detection engineering, CVE analysis |
| [Labs](labs/index.md) | Readers ready to experiment | Blue-team and red-team exercises |

## Put a question to the public core

When you are ready to evaluate labelled inputs, use
[Guard Lab's installation and demo guide](../../../tools/guard-lab/README.md#install-linux-x86-64--python-311).
It reports misses, false positives and execution errors separately, with no input
text in the report. Start on Linux x86-64 with Python 3.11; installation builds
native code and downloads dependencies. No account, API key or GPU is required.
The small synthetic demo checks execution, **not detection quality**.

## Read the archive with context

These lessons were developed as **Sentinel Academy** and are preserved as
historical learning and research material. Engine names, performance reports,
installation commands and product references inside older lessons have not been
revalidated by this entry-page update. They are not current Spectorn engines or
a certified production configuration. The public code remains available to study;
[Spectorn](https://spectorn.ai/) is the separate current product.

Run exercises only on systems you own or are explicitly authorized to test.
Use synthetic examples when sharing findings; never post real secrets or private
customer content. For responsible disclosure, follow the [security policy](../../../SECURITY.md).

[Engine reference](../../reference/engines-en.md) · [Sentinel Lattice paper (PDF)](../../../papers/sentinel-lattice/main.pdf) · [Public source](../../../sentinel-core/README.md) · [Contribute](../../CONTRIBUTING.md)
