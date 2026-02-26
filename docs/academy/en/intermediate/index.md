# Intermediate Track

Production-ready AI security knowledge. For security engineers and senior developers.

!!! info "Prerequisites"
    Complete the [Beginner track](../beginner/index.md) or have equivalent experience.

## Modules

### AI Fundamentals
Deep understanding of the models you're defending.

- [Transformers](ai-fundamentals/01-transformers.md) · [Encoder-Only](ai-fundamentals/02-encoder-only.md) · [Decoder-Only](ai-fundamentals/03-decoder-only.md) · [Vision Transformers](ai-fundamentals/05-vision-transformers.md) · [MoE](ai-fundamentals/07-mixture-of-experts.md) · [Training](ai-fundamentals/12-finetuning-rlhf.md) · [Tokenization](ai-fundamentals/14-tokenization-embeddings.md)

### Threat Landscape
OWASP standards in depth — every vulnerability with real examples.

- [LLM01–LLM10](threats/LLM01-prompt-injection.md) — Full OWASP LLM Top 10
- [ASI01](threats/ASI01-agentic-injection.md) — Agentic AI Top 10

### Attack Vectors
Hands-on understanding of how attacks work.

- [Direct Injection](attacks/prompt-injection-direct.md) · [Indirect Injection](attacks/prompt-injection-indirect.md) · [Invisible Prompts](attacks/invisible-prompts.md)
- [DAN](attacks/jailbreak-dan.md) · [Crescendo](attacks/jailbreak-crescendo.md) · [Policy Puppetry](attacks/jailbreak-policy-puppetry.md) · [Time Bandit](attacks/jailbreak-time-bandit.md)
- [Data Extraction](attacks/model-data-extraction.md) · [Adversarial Examples](attacks/model-adversarial-examples.md) · [MCP Threats](attacks/mcp-security-threats.md)

### Agentic Security
Securing AI agents, tools, and multi-agent systems.

- [Architectures](agentic/react-pattern.md) · [Multi-Agent](agentic/multi-agent.md) · [Memory](agentic/memory.md) · [Trust Zones](agentic/trust-zones.md)
- [MCP](agentic/mcp.md) · [A2A](agentic/a2a.md) · [OpenAI Functions](agentic/openai-functions.md) · [Authorization](agentic/authorization.md)

### Defense Strategies
Detection, guardrails, and Sentinel integration.

- [Pattern Matching](defense/pattern-matching.md) · [Behavioral Analysis](defense/behavioral-analysis.md) · [Guardrails](defense/guardrails-frameworks.md)
- [Sentinel Architecture](defense/sentinel-engine-architecture.md) · [Practical Integration](defense/sentinel-practical-integration.md)

### Production
Deploy, scale, monitor, comply.

- [Architecture](production/architecture.md) · [Docker](production/docker.md) · [Kubernetes](production/kubernetes.md)
- [SIEM](production/siem-integration.md) · [SOAR](production/soar-playbooks.md) · [Monitoring](production/monitoring.md) · [Performance](production/performance.md)

### Red Teaming
Offensive security with STRIKE.

- [STRIKE Deep Dive](red-team/strike.md) · [Custom Payloads](red-team/payloads.md) · [Automated Pentesting](red-team/pentesting.md)

## What's Next?

Ready for research-level content? Move to [**Advanced →**](../advanced/index.md) for TDA, formal methods, and engine development.
