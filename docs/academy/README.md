# AI Security Academy

> **SENTINEL** — The pytest of AI Security

Comprehensive curriculum for AI security professionals. Available in English and Russian.

## 🎯 Learning Paths

### 🟢 Beginner (0-2 months)
Start here if you're new to AI security.

| Week | Topic | EN | RU |
|------|-------|----|----|
| 1-2 | AI Fundamentals | [01-fundamentals](en/01-ai-fundamentals/) | [01-fundamentals](ru/01-ai-fundamentals/) |
| 3-4 | Threat Landscape (OWASP LLM) | [02-threats](en/02-threat-landscape/) | [02-threats](ru/02-threat-landscape/) |

### 🟡 Intermediate (2-4 months)
Build practical security skills.

| Week | Topic | EN | RU |
|------|-------|----|----|
| 5-6 | Attack Vectors | [03-attacks](en/03-attack-vectors/) | [03-attacks](ru/03-attack-vectors/) |
| 7-8 | Agentic Security | [04-agentic](en/04-agentic-security/) | [04-agentic](ru/04-agentic-security/) |
| 9-10 | Defense Strategies | [05-defense](en/05-defense-strategies/) | [05-defense](ru/05-defense-strategies/) |

### 🔴 Advanced (4-6 months)
Master advanced techniques.

| Week | Topic | EN | RU |
|------|-------|----|----|
| 11-12 | Advanced Topics (TDA, Red Team) | [06-advanced](en/06-advanced/) | [06-advanced](ru/06-advanced/) |
| 13-14 | Governance & Compliance | [07-governance](en/07-governance/) | [07-governance](ru/07-governance/) |

---

## 🧪 Labs

Hands-on practice with real vulnerable targets.

### Red Team (STRIKE)

| Lab | Description | EN | RU |
|-----|-------------|----|----|
| 001 | Basic Injection | [lab-001](en/08-labs/strike-red-team/lab-001-basic-injection.md) | [lab-001](ru/08-labs/strike-red-team/lab-001-basic-injection.md) |
| 002 | Indirect Injection | [lab-002](en/08-labs/strike-red-team/lab-002-indirect-injection.md) | [lab-002](ru/08-labs/strike-red-team/lab-002-indirect-injection.md) |
| 003 | Jailbreak Techniques | [lab-003](en/08-labs/strike-red-team/lab-003-jailbreak-techniques.md) | [lab-003](ru/08-labs/strike-red-team/lab-003-jailbreak-techniques.md) |
| 004 | Agent Attacks | [lab-004](en/08-labs/strike-red-team/lab-004-agent-attacks.md) | [lab-004](ru/08-labs/strike-red-team/lab-004-agent-attacks.md) |

### Blue Team (SENTINEL)

| Lab | Description | EN | RU |
|-----|-------------|----|----|
| 001 | Installation | [lab-001](en/08-labs/sentinel-blue-team/lab-001-installation.md) | [lab-001](ru/08-labs/sentinel-blue-team/lab-001-installation.md) |
| 002 | Attack Detection | [lab-002](en/08-labs/sentinel-blue-team/lab-002-attack-detection.md) | [lab-002](ru/08-labs/sentinel-blue-team/lab-002-attack-detection.md) |
| 003 | Custom Rules | [lab-003](en/08-labs/sentinel-blue-team/lab-003-custom-rules.md) | [lab-003](ru/08-labs/sentinel-blue-team/lab-003-custom-rules.md) |
| 004 | Production Monitoring | [lab-004](en/08-labs/sentinel-blue-team/lab-004-production-monitoring.md) | [lab-004](ru/08-labs/sentinel-blue-team/lab-004-production-monitoring.md) |

### Lab Infrastructure

```bash
# Setup lab environment
cd docs/academy/labs
pip install -r requirements.txt

# Run targets
python -m targets.vulnerable_agent
python -m targets.target_chatbot
```

See [labs/README.md](labs/README.md) for details.

---

## 📜 Certification

Complete all labs with 70%+ score to earn certification.

| Certification | Requirements |
|---------------|--------------|
| **STRIKE Red Team** | Labs 001-004, 70% average |
| **SENTINEL Blue Team** | Labs 001-002, 70% average |
| **Full Certification** | All labs, 80% average |

---

## 📚 Curriculum Structure

```
academy/
├── en/                     # English content
├── ru/                     # Russian content (mirrored structure)
├── labs/                   # Shared lab infrastructure
│   ├── targets/            # Vulnerable/secured targets
│   └── utils/              # Attack runner, scoring
├── _templates/             # Lesson templates
└── CURRICULUM.md           # Detailed curriculum
```

---

## 🔧 Using with SENTINEL

### Public API (Recommended)

All examples use the real SENTINEL API:

```python
from sentinel import scan, guard

# Scan input
result = scan("Ignore previous instructions")
print(f"Safe: {result.is_safe}")

# Guard decorator
@guard(engines=["injection", "pii"])
def my_llm_call(prompt):
    return openai.chat(prompt)
```

### Internal API (Advanced)

Some advanced lessons use internal APIs for extending SENTINEL:

```python
# For extending SENTINEL with custom engines (advanced)
from sentinel.brain.engines import BaseEngine
from sentinel.brain import SENTINELBrain
```

> [!NOTE]
> Internal APIs (`sentinel.brain.*`) are for advanced users building custom engines.
> Start with the public API (`sentinel.scan`, `sentinel.guard`) for most use cases.

---

*AI Security Academy — Part of the SENTINEL Framework*
