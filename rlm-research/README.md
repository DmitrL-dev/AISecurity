# RLM-Research

**Independent Research Lab for RLM-Toolkit**

> *"Not waiting for others to invent — inventing ourselves."*

## Structure

```
rlm-research/
├── benchmarks/          # RLM-Bench suite
│   ├── quality_position/    # Context position decay tests
│   ├── micro_model/         # Model efficiency metrics
│   └── retrieval/           # InfiniRetri accuracy tests
├── experiments/         # Active experiments
│   ├── semantic_hash/       # O(1) retrieval PoC
│   ├── persistent_ctx/      # Context immortality
│   └── model_routing/       # Task-aware routing
├── papers/              # Paper drafts
├── data/                # Datasets
└── notebooks/           # Research notebooks
```

## Current Focus: Phase 0

- [ ] RLM-Bench v0.1
- [ ] Semantic Hash PoC
- [ ] Quality-Position Test

## Quick Start

```bash
pip install -e ".[research]"
python -m rlm_research.bench quality_position
```

## Related

- [RLM-Toolkit](../rlm-toolkit/) — Main library
- [R&D Independence Plan](../../.gemini/antigravity/brain/.../rlm_rnd_independence_plan.md)
