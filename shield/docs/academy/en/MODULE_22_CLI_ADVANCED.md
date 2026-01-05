# Module 22: Advanced CLI — 199 Commands

## Overview

SENTINEL Shield CLI is a full-featured command-line interface in Cisco IOS style. It contains ~199 commands for managing all aspects of the security system.

---

## CLI Modes

| Mode | Prompt | Access |
|------|--------|--------|
| User | `shield>` | Basic view |
| Privileged | `shield#` | After `enable` |
| Config | `shield(config)#` | After `configure terminal` |
| Zone | `shield(config-zone-X)#` | After `zone X` |

---

## Command Categories (~199 total)

### Core Commands (19)
`enable`, `disable`, `configure terminal`, `exit`, `show zones`, `show rules`, `show stats`, `write memory`

### Security Commands (21)
`threat-hunter enable`, `watchdog enable`, `cognitive enable`, `pqc enable`, `brain enable`

### System Commands (44)
`clear`, `copy`, `hostname`, `logging`, `ping`, `debug`, `reload`, `show version`

### Network Commands (49)
`ha enable`, `siem enable`, `rate-limit`, `blocklist`, `alerting`, `api enable`

### Guard Commands (20)
`guard enable llm/rag/agent/tool/mcp/api`, `show guards`

### Show Commands (16)
`show threat-hunter`, `show watchdog`, `show cognitive`, `show pqc`, `show all`

---

## Example Session

```
shield> enable
shield# configure terminal
shield(config)# hostname PROD-SHIELD
shield(config)# threat-hunter enable
shield(config)# threat-hunter sensitivity 0.8
shield(config)# guard enable llm
shield(config)# end
shield# write memory
```

---

## Questions

1. How many modes are in Shield CLI?
2. How to go from User mode to Config mode?
3. What command saves configuration?
4. How many commands are in Shield CLI?

---

→ [Back to ACADEMY.md](../../ACADEMY.md)
