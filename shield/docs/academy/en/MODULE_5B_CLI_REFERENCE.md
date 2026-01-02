# SENTINEL Academy — Module 5B

## CLI Command Reference (194 Commands)

_SSA Level | Duration: 3 hours_

---

## Introduction

Shield CLI contains **194 commands** in Cisco IOS style, organized by categories:

| Category | Commands | Description |
|----------|----------|-------------|
| **show** | 19 | Display status |
| **config** | 28 | Configuration |
| **debug** | 28 | Debugging & diagnostics |
| **ha** | 14 | High Availability |
| **zone/rule** | 13 | Zones and rules |
| **guard** | 20 | Guards & security |
| **policy** | 19 | Policy Engine |
| **extended** | ~50 | Extended commands |

---

## 5B.1 Show Commands (19)

### System Information

```
show version              # Version and build info
show version detailed     # Extended information
show uptime               # System uptime
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
show access-lists         # ACLs
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
reload                    # Reload system
configure terminal        # Enter config mode
copy running-config startup-config   # Save
write memory              # = copy run start
ping <host>               # Ping
traceroute <host>         # Traceroute
```

---

## 5B.4 HA Commands (14)

### Standby

```
standby ip <virtual-ip>   # Virtual IP
standby priority <0-255>  # Priority
standby preempt           # Enable preempt
standby timers <hello> <hold>  # Timers
standby authentication <key>   # Auth key
standby track <object> <decr>  # Tracking
standby name <cluster>    # Cluster name
```

### Redundancy

```
redundancy mode <active-standby|active-active>
failover                  # Enable failover
failover lan interface <name>  # Failover interface
ha sync start             # Force sync
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
apply zone <name> in <acl> [out <acl>]  # Apply ACL
```

---

## 5B.6 Guard Commands (20)

### Enable/Disable

```
guard enable <llm|rag|agent|tool|mcp|api|all>
no guard enable <type>    # Disable guard
guard policy <type> <block|log|alert>
guard threshold <type> <0.0-1.0>
```

### Signatures

```
signature-set update      # Update signature DB
signature-set category enable <cat>  # Enable category
```

### Security

```
canary token add <token>  # Add canary
blocklist ip add <ip>     # Add IP to blocklist
rate-limit enable         # Enable rate limiting
rate-limit requests <count> per <seconds>
threat-intel enable       # Enable threat intel
alert destination <type> <target>
siem enable               # Enable SIEM
siem destination <host> <port>
siem format <cef|json|syslog>
```

---

## 5B.7 Policy Commands (19)

### Class Maps

```
class-map match-any <name>   # Create class-map (OR)
class-map match-all <name>   # Create class-map (AND)
```

#### Match Conditions

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
class <class-name>        # Add class
block                     # Block action
log                       # Log action
alert                     # Alert action
rate-limit <pps>          # Rate limit
```

### Service Policy

```
service-policy input <policy>   # Apply inbound
service-policy output <policy>  # Apply outbound
```

---

## Full Configuration Example

```
hostname SENTINEL-PROD-1
enable secret $6$encrypted

logging level info
logging host 192.168.1.100

api enable
api port 8080

standby ip 10.0.0.100
standby priority 100
standby preempt
failover

guard enable all
guard threshold llm 0.7

zone external
  type api
  provider openai
  trust-level 3
!

class-map match-any THREATS
  match injection
  match jailbreak
!

policy-map SECURITY-POLICY
  class THREATS
    block
    log
!

zone external
  service-policy input SECURITY-POLICY
!

end
```

---

## CLI Modes

| Mode | Prompt | How to Enter |
|------|--------|--------------|
| User EXEC | `Shield>` | Default |
| Privileged EXEC | `Shield#` | `enable` |
| Global Config | `Shield(config)#` | `configure terminal` |
| Zone Config | `Shield(config-zone)#` | `zone <name>` |
| Class-map | `Shield(config-cmap)#` | `class-map ...` |
| Policy-map | `Shield(config-pmap)#` | `policy-map ...` |

---

## Summary

- **194 commands** in Cisco IOS style
- 7 categories: show, config, debug, ha, zone, guard, policy
- Full Policy Engine (class-map + policy-map)
- Production-ready CLI

---

_"194 commands = full control over Shield."_
