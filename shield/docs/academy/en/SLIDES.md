# SENTINEL Academy — Presentation Slides

## Slide Decks for Instructors

---

## Deck 1: Introduction to AI Security

### Slide 1: Title
**SENTINEL Shield**  
_The DMZ Your AI Deserves_

### Slide 2: The Problem
- AI systems trust input blindly
- Natural language = attack surface
- No security layer = breach waiting to happen

### Slide 3: Attack Types
- Prompt Injection
- Jailbreaking
- Data Exfiltration
- RAG Poisoning
- Agent Abuse

### Slide 4: The Solution
Shield sits between users and AI:
```
User → Shield → AI → Shield → Response
```

### Slide 5: Why Shield?
- Pure C (< 1ms latency)
- 6 specialized guards
- 20 protocols
- 194 CLI commands

---

## Deck 2: Architecture

### Slide 1: 8-Layer Model
```
Layer 8: API
Layer 7: CLI (194 commands)
Layer 6: Guards (6)
Layer 5: Zone Management
Layer 4: Rule Engine
Layer 3: Analysis
Layer 2: Protocols (20)
Layer 1: Core
```

### Slide 2: Guards
| Guard | Protects |
|-------|----------|
| LLM | Language models |
| RAG | Retrieval systems |
| Agent | Autonomous agents |
| Tool | External tools |
| MCP | MCP protocol |
| API | API endpoints |

### Slide 3: Zones
- External (trust=1)
- DMZ (trust=5)
- Internal (trust=10)

### Slide 4: Rule Engine
```
shield-rule 10 deny inbound any match injection
shield-rule 100 permit any any
```

---

## Deck 3: CLI Deep Dive

### Slide 1: Modes
```
User EXEC    → Shield>
Privileged   → Shield#
Config       → Shield(config)#
Zone         → Shield(config-zone)#
Class-map    → Shield(config-cmap)#
Policy-map   → Shield(config-pmap)#
```

### Slide 2: Key Commands
```
show version
show zones
guard enable all
class-map match-any THREATS
policy-map SECURITY
```

### Slide 3: 194 Commands
| Category | Count |
|----------|-------|
| show | 19 |
| config | 28 |
| debug | 28 |
| ha | 14 |
| zone | 13 |
| guard | 20 |
| policy | 19 |

---

## Deck 4: Enterprise Features

### Slide 1: 20 Protocols
| Category | Protocols |
|----------|-----------|
| Discovery | ZDP, ZRP, ZHP |
| Traffic | STP, SPP, SQP, SRP |
| Analytics | SAF, STT, SEM, SLA |
| HA | SHSP, SSRP, SMRP |
| Integration | SBP, SGP, SIEM |
| Security | STLS, SZAA, SSigP |

### Slide 2: High Availability
- Active-Standby
- Automatic failover
- State replication

### Slide 3: eBPF
- Kernel-level filtering
- < 1μs latency
- 10M+ pps

---

## Deck 5: Integration

### Slide 1: C Integration
```c
shield_evaluate(&ctx, input, len, zone, &result);
if (result.action == ACTION_BLOCK) { ... }
```

### Slide 2: REST API
```bash
curl -X POST localhost:8080/v1/evaluate
```

### Slide 3: Docker
```yaml
services:
  shield:
    image: sentinel/shield
```

---

## Usage Notes

- Each deck: ~15-20 minutes
- Include live demos
- Use LABS.md for exercises after each deck

---

_"A picture is worth a thousand words."_
