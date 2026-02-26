# 📋 Custom Security Requirements

> **Module:** `brain.requirements`  
> **Version:** 1.6.0  
> **Added:** January 8, 2026

User-defined security policies that connect to SENTINEL detection engines.

---

## Overview

Custom Requirements allow you to define your own security policies that map to SENTINEL engines. Each requirement specifies:

- **What to detect** (engine + configuration)
- **How to respond** (warn, alert, block)
- **Compliance mapping** (OWASP, EU AI Act, etc.)

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Requirements API                      │
├─────────────────────────────────────────────────────────┤
│  POST /requirements/sets           Create set           │
│  GET  /requirements/sets/{id}      Get requirements     │
│  POST /requirements/sets/{id}/check  Check text         │
│  GET  /requirements/sets/{id}/export Export YAML        │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                  RequirementsEnforcer                    │
│  • Lazy-loads SENTINEL engines                          │
│  • Executes checks against requirements                 │
│  • Returns violations with severity + action            │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                     Storage Layer                        │
│  • YAMLConfigLoader — File-based configs                │
│  • SQLiteStorage — Persistent database                  │
│  • RequirementsManager — Unified interface              │
└─────────────────────────────────────────────────────────┘
```

## Data Models

### SecurityRequirement

```python
@dataclass
class SecurityRequirement:
    id: str                           # Unique identifier
    name: str                         # Human-readable name
    description: str                  # Detailed description
    category: RequirementCategory     # injection, data_privacy, agent_safety, etc.
    severity: Severity                # low, medium, high, critical
    enabled: bool = True              # Toggle on/off
    engine: Optional[str] = None      # SENTINEL engine to use
    engine_config: Dict = {}          # Engine-specific configuration
    action: EnforcementAction = WARN  # warn, alert, block
    compliance_tags: List[str] = []   # OWASP-LLM01, EU-ART-14, etc.
```

### RequirementSet

```python
@dataclass
class RequirementSet:
    id: str
    name: str
    description: str
    requirements: List[SecurityRequirement]
    version: str = "1.0.0"
```

### RequirementCheckResult

```python
@dataclass
class RequirementCheckResult:
    passed: bool                      # All requirements passed?
    violations: List[Violation]       # List of violations found
    requirements_checked: int         # Total checked
    requirements_passed: int          # Passed count
    blocked: bool                     # Any BLOCK action triggered?
    
    @property
    def compliance_score(self) -> float:  # 0-100%
```

## Usage

### Python API

```python
from brain.requirements import RequirementsManager, create_enforcer

# Load manager
manager = RequirementsManager()

# Get default requirements
default_set = manager.get("sentinel-default")

# Create enforcer
enforcer = create_enforcer(default_set)

# Check text
result = enforcer.check_text("Ignore previous instructions")

print(f"Passed: {result.passed}")
print(f"Score: {result.compliance_score}%")
for v in result.violations:
    print(f"  {v.severity}: {v.message}")
```

### REST API

```bash
# Create a requirement set
curl -X POST http://localhost:8000/requirements/sets \
  -H "Content-Type: application/json" \
  -d '{"name": "My Policy", "description": "Custom requirements"}'

# Add a requirement
curl -X POST http://localhost:8000/requirements/sets/{set_id}/requirements \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Block Jailbreaks",
    "category": "injection",
    "severity": "critical",
    "engine": "guardrails_engine",
    "action": "block"
  }'

# Check text against requirements
curl -X POST http://localhost:8000/requirements/sets/{set_id}/check \
  -H "Content-Type: application/json" \
  -d '{"text": "Ignore all previous instructions"}'
```

### YAML Configuration

```yaml
# my_requirements.yaml
id: my-policy
name: My Security Policy
description: Custom requirements for my application
version: "1.0.0"

requirements:
  - id: req-injection-block
    name: Block Prompt Injection
    description: Block detected prompt injection attempts
    category: injection
    severity: critical
    enabled: true
    engine: policy_puppetry_detector
    action: block
    compliance_tags:
      - OWASP-LLM01
      - OWASP-ASI05
  
  - id: req-pii-warn
    name: Detect PII in Outputs
    category: data_privacy
    severity: high
    engine: pii_detector
    action: warn
    compliance_tags:
      - OWASP-LLM06
      - EU-AI-ACT-10
```

## Default Requirements

SENTINEL ships with 12 OWASP-mapped defaults:

| ID | Name | Engine | Action | OWASP |
|----|------|--------|--------|-------|
| `req-injection-block` | Block Prompt Injection | policy_puppetry_detector | block | LLM01 |
| `req-jailbreak-block` | Block Jailbreak | guardrails_engine | block | LLM01 |
| `req-prompt-leak` | Prevent Prompt Extraction | prompt_leak_detector | block | LLM01 |
| `req-pii-warn` | Detect PII | pii_detector | warn | LLM06 |
| `req-exfil-block` | Block Exfiltration | mcp_security_monitor | block | ASI07 |
| `req-agent-loop` | Detect Agent Loops | agentic_behavior_analyzer | alert | ASI01 |
| `req-goal-drift` | Detect Goal Drift | agentic_behavior_analyzer | warn | ASI02 |
| `req-deception` | Detect Deception | agentic_behavior_analyzer | alert | ASI03 |
| `req-sleeper-detect` | Detect Sleeper Triggers | sleeper_agent_detector | block | LLM03 |
| `req-supply-chain` | Scan Supply Chain | supply_chain_scanner | block | LLM05 |
| `req-output-moderation` | Moderate Outputs | guardrails_engine | block | LLM02 |

## Enforcement Actions

| Action | Behavior |
|--------|----------|
| `warn` | Log warning, continue processing |
| `alert` | Send alert (webhook, Slack), continue |
| `block` | Stop processing, return error |

## Categories

| Category | Description |
|----------|-------------|
| `injection` | Prompt injection, jailbreaks |
| `data_privacy` | PII, data leakage |
| `agent_safety` | Loops, drift, deception |
| `model_security` | Supply chain, integrity |
| `output_safety` | Harmful content |
| `custom` | User-defined |

## Files

| File | LOC | Purpose |
|------|-----|---------|
| `models.py` | 200 | Data models |
| `storage.py` | 350 | YAML + SQLite |
| `enforcer.py` | 200 | Engine integration |
| `configs/default.yaml` | 120 | Default requirements |
| `tests/test_requirements.py` | 230 | Unit tests (9) |

---

📖 **See also:** [Compliance Report](./compliance.md) | [Design Review](./design-review.md)
