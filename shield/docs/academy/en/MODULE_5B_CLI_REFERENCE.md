# SENTINEL Academy — Module 5B

## CLI Command Reference (194 Commands)

_SSA Level | Duration: 3 hours_

---

## Introduction

Shield CLI contains **194 commands** in Cisco IOS style, organized by categories:

| Category      | Commands | Description                |
| ------------- | -------- | -------------------------- |
| **show**      | 19       | Display state              |
| **config**    | 28       | Configuration              |
| **debug**     | 28       | Debugging and diagnostics  |
| **ha**        | 14       | High Availability          |
| **zone/rule** | 13       | Zones and rules            |
| **guard**     | 20       | Guards and security        |
| **policy**    | 19       | Policy Engine              |
| **extended**  | ~50      | Extended commands          |

---

## 5B.1 Show Commands (19)

### System Information

```
show version              # Version and build info
show version detailed     # Extended information
show uptime               # Uptime
show clock                # System time
show environment          # CPU, RAM, OS
```

### Configuration

```
show running-config       # Current configuration
show startup-config       # Saved configuration
show history              # Command history
```

### Resources

```
show memory               # Memory usage
show cpu                  # CPU load
show processes            # Active processes
show interfaces           # Network interfaces
```

### Shield State

```
show zones                # Zone list
show guards               # Guard status
show protocols            # Active protocols
show sessions             # Active sessions
show alerts               # Alerts
show metrics              # Metrics
show counters             # Counters
show access-lists         # ACL
show logging              # Logs
show debugging            # Debug status
show tech-support         # Full dump for support
show controllers          # Internal controllers
show inventory            # Component inventory
```

---

## 5B.2 Config Commands (28)

### Basic

```
hostname <name>           # Device name
enable secret <pass>      # Enable password
username <name> password <pass>  # User
banner motd <text>        # MOTD banner
```

### Logging

```
logging level <debug|info|warn|error>
logging console           # Console output
logging buffered <size>   # Log buffer
logging host <ip>         # Syslog server
```

### Time

```
ntp server <ip>           # NTP server
clock timezone <tz>       # Timezone
```

### Network

```
ip domain-name <domain>   # Domain
ip name-server <ip>       # DNS server
```

### Security

```
service password-encryption  # Password encryption
aaa authentication login <name> <method>  # AAA
snmp-server community <string> <ro|rw>
snmp-server host <ip>
```

### API

```
api enable                # Enable REST API
api port <port>           # API port
api token <token>         # API token
metrics enable            # Enable /metrics
metrics port <port>       # Metrics port
```

### Archiving

```
archive path <path>       # Archive path
archive maximum <count>   # Max copies
```

### Navigation

```
end                       # Exit to exec mode
do <command>              # Execute exec command
```

---

## 5B.3 Debug Commands (28)

### Component Debug

```
debug shield              # Shield core events
debug zone                # Zone events
debug rule                # Rule matching
debug guard               # Guard events
debug protocol            # Protocol messages
debug ha                  # HA events
debug all                 # All debug
undebug all               # Disable debug
no debug all              # Same
```

### Terminal

```
terminal monitor          # Enable monitoring
terminal no monitor       # Disable monitoring
```

### Clear Commands

```
clear counters            # Reset counters
clear logging             # Clear log buffer
clear statistics          # Reset statistics
clear sessions            # Clear sessions
clear alerts              # Clear alerts
clear blocklist           # Clear blocklist
clear quarantine          # Clear quarantine
```

### System

```
reload                    # Reload
configure terminal        # Enter config mode
configure memory          # Load startup-config
```

### Copy/Write

```
copy running-config startup-config   # Save
copy startup-config running-config   # Load
write memory              # = copy run start
write erase               # Erase startup
write terminal            # = show running
```

### Network Tools

```
ping <host>               # Ping
traceroute <host>         # Traceroute
```

---

## 5B.4 HA Commands (14)

### Standby

```
standby ip <virtual-ip>   # Virtual IP
standby priority <0-255>  # Priority
standby preempt           # Preempt enable
no standby preempt        # Preempt disable
standby timers <hello> <hold>  # Timers
standby authentication <key>   # Key
standby track <object> <decr>  # Tracking
standby name <cluster>    # Cluster name
```

### Redundancy

```
redundancy                # Enter redundancy mode
redundancy mode <active-standby|active-active>
```

### Failover

```
failover                  # Enable failover
no failover               # Disable failover
failover lan interface <name>  # Failover interface
ha sync start             # Force synchronization
```

---

## 5B.5 Zone/Rule Commands (13)

### Zones

```
zone <name>               # Create/enter zone
no zone <name>            # Delete zone
```

#### Zone Subcommands

```
type <llm|rag|agent|tool|mcp|api>  # Zone type
provider <name>           # Provider
description <text>        # Description
trust-level <0-10>        # Trust level
shutdown                  # Disable zone
no shutdown               # Enable zone
```

### Rules

```
shield-rule <num> <action> <direction> <zone-type> [match...]
no shield-rule <num>      # Delete rule
access-list <num>         # Create ACL
no access-list <num>      # Delete ACL
apply zone <name> in <acl> [out <acl>]  # Apply ACL
```

---

## 5B.6 Guard Commands (20)

### Enable/Disable

```
guard enable <llm|rag|agent|tool|mcp|api|all>
no guard enable <type>    # Disable guard
```

### Configuration

```
guard policy <type> <block|log|alert>
guard threshold <type> <0.0-1.0>
```

### Signatures

```
signature-set update      # Update signature base
signature-set category enable <cat>  # Enable category
```

### Canary Tokens

```
canary token add <token>  # Add canary
no canary token <token>   # Remove canary
```

### Blocklist

```
blocklist ip add <ip>     # Add IP to blocklist
no blocklist ip <ip>      # Remove IP
blocklist pattern add <pattern>  # Add pattern
```

### Rate Limiting

```
rate-limit enable         # Enable rate limiting
rate-limit requests <count> per <seconds>  # Configure
```

### Threat Intelligence

```
threat-intel enable       # Enable threat intel
threat-intel feed add <url>  # Add feed
```

### Alerting

```
alert destination <webhook|email|syslog> <target>
alert threshold <info|warn|critical>
```

### SIEM

```
siem enable               # Enable SIEM export
siem destination <host> <port>
siem format <cef|json|syslog>
```

---

## 5B.7 Policy Commands (19)

### Class Maps

```
class-map match-any <name>   # Create class-map (OR)
class-map match-all <name>   # Create class-map (AND)
no class-map <name>          # Delete class-map
```

#### Match Conditions (in class-map)

```
match injection           # Prompt injection
match jailbreak           # Jailbreak attempt
match exfiltration        # Data exfiltration
match pattern <regex>     # Regex pattern
match contains <string>   # Contains string
match size greater-than <bytes>  # Size >
match entropy-high        # High entropy
```

### Policy Maps

```
policy-map <name>         # Create policy-map
no policy-map <name>      # Delete policy-map
```

#### Policy Actions (in policy-map)

```
class <class-name>        # Add class
block                     # Block
log                       # Log
alert                     # Alert
rate-limit <pps>          # Rate limit
```

### Service Policy

```
service-policy input <policy>   # Apply to input
service-policy output <policy>  # Apply to output
```

---

## Full Configuration Example

```
! SENTINEL Shield Configuration

hostname SENTINEL-PROD-1
enable secret $6$encrypted

! Logging
logging level info
logging host 192.168.1.100
logging buffered 8192

! API
api enable
api port 8080
api token secret-token-123

! Metrics
metrics enable
metrics port 9090

! HA
standby ip 10.0.0.100
standby priority 100
standby preempt
failover
failover lan interface eth1

! Guards
guard enable all
guard threshold llm 0.7
guard policy llm block

! Signatures
signature-set update
signature-set category enable injection
signature-set category enable jailbreak

! Zones
zone external
  type api
  provider openai
  trust-level 3
  no shutdown
!
zone internal
  type llm
  trust-level 8
!

! Class Maps
class-map match-any THREATS
  match injection
  match jailbreak
  match exfiltration
!

! Policy Maps
policy-map SECURITY-POLICY
  class THREATS
    block
    log
    alert
!

! Rules
shield-rule 10 deny inbound any match injection
shield-rule 20 permit inbound llm
shield-rule 100 permit any any

! Apply
zone external
  service-policy input SECURITY-POLICY
!

! SIEM
siem enable
siem destination splunk.company.com 514
siem format cef

end
```

---

## CLI Navigation

| Shortcut | Action                       |
| -------- | ---------------------------- |
| `?`      | Help on available commands   |
| `Tab`    | Auto-completion              |
| `Ctrl+C` | Interrupt command            |
| `Ctrl+Z` | Exit to exec mode            |
| `exit`   | Exit current mode            |
| `end`    | Exit to exec (from any level)|

---

## CLI Modes

| Mode            | Prompt                 | How to Enter          |
| --------------- | ---------------------- | --------------------- |
| User EXEC       | `Shield>`              | Default               |
| Privileged EXEC | `Shield#`              | `enable`              |
| Global Config   | `Shield(config)#`      | `configure terminal`  |
| Zone Config     | `Shield(config-zone)#` | `zone <name>`         |
| Class-map       | `Shield(config-cmap)#` | `class-map ...`       |
| Policy-map      | `Shield(config-pmap)#` | `policy-map ...`      |

---

## Practice

### Exercise 1: Basic Setup

Configure Shield:

- hostname: SHIELD-LAB-1
- API on port 8080
- Logging to 192.168.1.50

### Exercise 2: Security Policy

Create a policy:

- class-map for injection + jailbreak
- policy-map with block + alert
- Apply to zone external

### Exercise 3: HA Configuration

Configure HA cluster:

- Virtual IP: 10.0.0.100
- Priority: 150
- Preempt enabled
- Hello: 1s, Hold: 3s

---

## Module 5B Summary

- **194 commands** in Cisco IOS style
- 7 categories: show, config, debug, ha, zone, guard, policy
- Full-featured Policy Engine (class-map + policy-map)
- Production-ready CLI

---

_"194 commands = complete control over Shield."_
