# Module 22: Advanced CLI — 199 Commands

## Overview

SENTINEL Shield CLI is a full-featured command-line interface in Cisco IOS style. It contains ~199 commands for managing all aspects of the security system.

---

## CLI Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        CLI Interface                         │
├───────────────┬───────────────┬───────────────┬─────────────┤
│    User       │   Privileged  │    Config     │   Zone      │
│    Mode       │     Mode      │    Mode       │   Config    │
│   shield>     │   shield#     │   (config)#   │  (zone)#    │
├───────────────┴───────────────┴───────────────┴─────────────┤
│                    Command Registration                      │
│                  cli_register_command()                      │
├─────────────────────────────────────────────────────────────┤
│                     shield_state_t                           │
│                   (Global State Backend)                     │
└─────────────────────────────────────────────────────────────┘
```

---

## CLI Modes

| Mode | Prompt | Access |
|------|--------|--------|
| User | `shield>` | Basic viewing |
| Privileged | `shield#` | After `enable` |
| Config | `shield(config)#` | After `configure terminal` |
| Zone | `shield(config-zone-X)#` | After `zone X` |

---

## Command Categories (~199)

### 1. Core Commands (commands.c) — 19

| Command | Description |
|---------|-------------|
| `enable` | Enter privileged mode |
| `disable` | Exit privileged mode |
| `configure terminal` | Enter config mode |
| `exit` / `end` | Exit mode |
| `show zones` | Show all zones |
| `show rules` | Show all rules |
| `show stats` | Show statistics |
| `show config` | Show configuration |
| `show version` | Show version |
| `zone <name>` | Create/enter zone |
| `shield-rule <id>` | Create rule |
| `apply` | Apply configuration |
| `write` / `write memory` | Save configuration |
| `clear` | Clear screen/stats |
| `debug` | Debug mode |
| `help` / `?` | Help |

### 2. Security Commands (cmd_security.c) — 21

| Command | Description |
|---------|-------------|
| `threat-hunter enable/disable` | ThreatHunter |
| `threat-hunter sensitivity <N>` | Sensitivity |
| `threat-hunter test "<text>"` | Test |
| `watchdog enable/disable` | Watchdog |
| `watchdog auto-recovery` | Auto-recovery |
| `watchdog check` | Health check |
| `cognitive enable/disable` | Cognitive Signatures |
| `cognitive test "<text>"` | Test for cognitive attacks |
| `pqc enable/disable` | Post-Quantum Crypto |
| `pqc test` | PQC self-test |
| `secure-comm enable` | Secure Communication |
| `brain enable/disable` | Brain Integration |
| `brain url <URL>` | Brain API URL |

### 3. System Commands (cmd_system.c) — 44

| Command | Description |
|---------|-------------|
| `clear screen` | Clear screen |
| `clear stats` | Reset statistics |
| `copy running-config startup-config` | Save config |
| `copy startup-config running-config` | Load config |
| `terminal length <N>` | Terminal length |
| `terminal width <N>` | Terminal width |
| `hostname <name>` | Hostname |
| `logging level <level>` | Logging level |
| `ping <host>` | Ping |
| `traceroute <host>` | Traceroute |
| `nslookup <host>` | DNS lookup |
| `debug all` | Enable all debugging |
| `debug guard <type>` | Debug guard |
| `no debug all` | Disable debugging |
| `config max-connections <N>` | Max connections |
| `config timeout <N>` | Timeout |
| `show running-config` | Running config |
| `show startup-config` | Startup config |
| `show version` | Shield version |
| `show uptime` | Uptime |
| `show memory` | Memory usage |
| `show cpu` | CPU usage |
| `reload` | Reload |

### 4. Network Commands (cmd_network.c) — 49

| Command | Description |
|---------|-------------|
| `ha enable/disable` | High Availability |
| `ha mode active/standby` | HA mode |
| `ha peer <URL>` | Peer URL |
| `ha status` | HA status |
| `siem enable/disable` | SIEM integration |
| `siem endpoint <URL>` | SIEM endpoint |
| `siem test` | Test SIEM connection |
| `rate-limit enable/disable` | Rate limiting |
| `rate-limit max <N>` | Max requests |
| `rate-limit window <sec>` | Time window |
| `blocklist enable/disable` | Blocklist |
| `blocklist add <IP/pattern>` | Add to blocklist |
| `blocklist remove <IP/pattern>` | Remove from blocklist |
| `blocklist show` | Show blocklist |
| `threat-intel enable/disable` | Threat intelligence |
| `threat-intel source <URL>` | TI source |
| `alerting enable/disable` | Alerting |
| `alerting webhook <URL>` | Webhook URL |
| `canary enable/disable` | Canary tokens |
| `canary create <name>` | Create canary |
| `api enable/disable` | REST API |
| `api port <N>` | API port |
| `api auth enable/disable` | API auth |

### 5. Guard Commands (cmd_guard.c) — 20

| Command | Description |
|---------|-------------|
| `guard enable llm` | Enable LLM Guard |
| `guard enable rag` | Enable RAG Guard |
| `guard enable agent` | Enable Agent Guard |
| `guard enable tool` | Enable Tool Guard |
| `guard enable mcp` | Enable MCP Guard |
| `guard enable api` | Enable API Guard |
| `no guard enable <type>` | Disable guard |
| `show guard <type>` | Show guard status |
| `show guards` | Show all guards |

### 6. Show Commands (cmd_show.c) — 16

| Command | Description |
|---------|-------------|
| `show threat-hunter` | ThreatHunter status |
| `show watchdog` | Watchdog status |
| `show cognitive` | Cognitive status |
| `show pqc` | PQC status |
| `show brain` | Brain status |
| `show rate-limit` | Rate limit status |
| `show blocklist` | Blocklist status |
| `show siem` | SIEM status |
| `show ha` | HA status |
| `show api` | API status |
| `show all` | All modules status |

---

## Example Session

```
shield> enable
Password: ******

shield# show version
SENTINEL Shield v1.2.0
Build: Jan 5, 2026 16:30
Compiler: GCC 13.2.0

shield# configure terminal
Enter configuration commands, one per line. End with 'end'.

shield(config)# hostname PROD-SHIELD-01
Hostname set to PROD-SHIELD-01

PROD-SHIELD-01(config)# threat-hunter enable
ThreatHunter enabled

PROD-SHIELD-01(config)# threat-hunter sensitivity 0.8
ThreatHunter sensitivity set to 0.80

PROD-SHIELD-01(config)# guard enable llm
LLM Guard enabled

PROD-SHIELD-01(config)# end

PROD-SHIELD-01# write memory
Building configuration...
Configuration saved to shield.conf
[OK]

PROD-SHIELD-01# show running-config
!
! SENTINEL Shield Configuration
! Generated: 2026-01-05 16:45:00
!
hostname PROD-SHIELD-01
!
threat-hunter enable
threat-hunter sensitivity 0.80
!
watchdog enable
watchdog auto-recovery
!
guard enable llm
guard enable rag
guard enable agent
guard enable tool
guard enable mcp
guard enable api
!
end
```

---

## Command Registration

Each module registers its commands:

```c
void register_security_commands(cli_context_t *ctx)
{
    shield_state_get();  // Init state
    
    for (int i = 0; security_commands[i].name != NULL; i++) {
        cli_register_command(ctx, &security_commands[i]);
    }
}
```

---

## Lab Exercise LAB-220

### Objective
Master all CLI command categories.

### Task 1: Basic Navigation
```bash
shield> ?
shield> enable
shield# ?
shield# configure terminal
shield(config)# ?
shield(config)# end
```

### Task 2: Full Configuration
```bash
shield# configure terminal
shield(config)# hostname MY-SHIELD
shield(config)# threat-hunter enable
shield(config)# threat-hunter sensitivity 0.7
shield(config)# watchdog enable
shield(config)# cognitive enable
shield(config)# pqc enable
shield(config)# guard enable llm
shield(config)# guard enable rag
shield(config)# rate-limit enable
shield(config)# rate-limit max 1000
shield(config)# end
shield# write memory
```

### Task 3: Diagnostics
```bash
shield# show all
shield# show stats
shield# watchdog check
shield# threat-hunter test "ignore previous"
```

---

## Self-Check Questions

1. How many modes does Shield CLI have?
2. How do you go from User mode to Config mode?
3. Which command saves configuration?
4. How do you enable all Guards with one command?
5. What does `copy running-config startup-config` do?

---

## Conclusion

This module concludes the new Academy modules added for Phase 4 SENTINEL Shield functionality.

**Complete list of new modules:**
- MODULE_17: ThreatHunter
- MODULE_18: Watchdog
- MODULE_19: Cognitive Signatures
- MODULE_20: Post-Quantum Cryptography
- MODULE_21: Shield State
- MODULE_22: Advanced CLI (this module)

---

→ [Return to ACADEMY.md](../../ACADEMY.md)
