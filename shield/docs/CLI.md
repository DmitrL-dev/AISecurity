# SENTINEL Shield CLI Reference

> **Cisco-style Command Line Interface**

---

## Connecting to CLI

```bash
# Local connection
./shield-cli

# Remote connection
./shield-cli --host 192.168.1.10 --port 2222

# With authentication
./shield-cli --user admin
```

---

## Command Structure

```
Shield> <command> [subcommand] [arguments] [options]
```

---

## Basic Commands

### Show Commands

| Command          | Description            |
| ---------------- | ---------------------- |
| `show status`    | System status overview |
| `show version`   | Shield version info    |
| `show zones`     | List all zones         |
| `show rules`     | List all rules         |
| `show guards`    | List active guards     |
| `show metrics`   | Current metrics        |
| `show sessions`  | Active sessions        |
| `show blocklist` | Blocked entries        |
| `show config`    | Running configuration  |
| `show logs [n]`  | Last n log entries     |

### Configuration Commands

| Command                              | Description           |
| ------------------------------------ | --------------------- |
| `zone add <name> <trust>`            | Add new zone          |
| `zone remove <name>`                 | Remove zone           |
| `rule add <name> <pattern> <action>` | Add rule              |
| `rule remove <id>`                   | Remove rule by ID     |
| `rule enable <id>`                   | Enable rule           |
| `rule disable <id>`                  | Disable rule          |
| `guard enable <type>`                | Enable guard          |
| `guard disable <type>`               | Disable guard         |
| `blocklist add <ip\|pattern>`        | Add to blocklist      |
| `blocklist remove <ip\|pattern>`     | Remove from blocklist |

### Operational Commands

| Command             | Description          |
| ------------------- | -------------------- |
| `evaluate "<text>"` | Evaluate input text  |
| `filter "<text>"`   | Filter output text   |
| `reload`            | Reload configuration |
| `clear sessions`    | Clear all sessions   |
| `clear metrics`     | Reset metrics        |
| `debug on`          | Enable debug mode    |
| `debug off`         | Disable debug mode   |

### System Commands

| Command          | Description      |
| ---------------- | ---------------- |
| `help [command]` | Show help        |
| `exit`           | Exit CLI         |
| `history`        | Command history  |
| `!n`             | Repeat command n |

---

## Command Examples

### Zone Management

```
Shield> show zones
NAME       TRUST  RATE_LIMIT  SESSIONS
external   1      100/s       42
internal   10     unlimited   15
dmz        5      500/s       8

Shield> zone add partner 7
Zone 'partner' created with trust level 7

Shield> zone remove partner
Zone 'partner' removed
```

### Rule Management

```
Shield> show rules
ID  NAME              ZONE      ACTION  HITS   ENABLED
1   block_injection   external  block   156    yes
2   block_jailbreak   *         block   89     yes
3   log_suspicious    *         log     412    yes

Shield> rule add block_dan "do anything now" block
Rule added with ID 4

Shield> rule disable 4
Rule 4 disabled

Shield> rule enable 4
Rule 4 enabled
```

### Testing

```
Shield> evaluate "Hello, how are you?"
Result: ALLOW
  Zone: external
  Threat: 0.00
  Time: 0.12ms

Shield> evaluate "Ignore all previous instructions"
Result: BLOCK
  Zone: external
  Threat: 0.95
  Reason: Rule 1: block_injection
  Intent: instruction_override (confidence: 0.92)
  Time: 0.45ms

Shield> filter "My SSN is 123-45-6789"
Result: "My SSN is [REDACTED]"
  Redacted: 1 PII pattern
```

### Monitoring

```
Shield> show metrics
METRIC                   VALUE
requests_total           15432
requests_blocked         234
requests_allowed         15198
block_rate              1.52%
avg_latency_us          145
uptime_seconds          86400

Shield> show logs 5
[2026-01-01 21:00:01] INFO  Request blocked: zone=external rule=1
[2026-01-01 21:00:02] INFO  Request allowed: zone=internal
[2026-01-01 21:00:03] WARN  Rate limit hit: session=abc123
[2026-01-01 21:00:04] INFO  Request blocked: zone=external rule=2
[2026-01-01 21:00:05] INFO  Request allowed: zone=external

Shield> show sessions
SESSION           ZONE      REQUESTS  BLOCKED  LAST_SEEN
abc123            external  45        3        2s ago
def456            internal  12        0        15s ago
xyz789            dmz       8         1        1m ago
```

---

## Configuration Mode

Enter configuration mode for complex changes:

```
Shield> configure terminal
Shield(config)> zone external
Shield(config-zone)> trust-level 2
Shield(config-zone)> rate-limit 200
Shield(config-zone)> exit
Shield(config)> write memory
Configuration saved
Shield(config)> exit
Shield>
```

---

## Keyboard Shortcuts

| Key       | Action                 |
| --------- | ---------------------- |
| `Tab`     | Auto-complete          |
| `?`       | Context help           |
| `↑` / `↓` | Command history        |
| `Ctrl+C`  | Cancel current command |
| `Ctrl+D`  | Exit CLI               |

---

## Output Formats

```
# Default (table)
Shield> show zones

# JSON output
Shield> show zones --json

# CSV output
Shield> show zones --csv
```

---

## Scripting

```bash
# Run single command
./shield-cli -c "show status"

# Run script file
./shield-cli -f commands.txt

# Pipe commands
echo "show metrics" | ./shield-cli
```

---

## Brain FFI Commands

```
Shield> show brain
Brain Status: STUB (mock mode)
Category Engines: 6 available
  - INJECTION: enabled
  - JAILBREAK: enabled
  - RAG_POISON: enabled
  - AGENT_MANIP: enabled
  - TOOL_HIJACK: enabled
  - EXFILTRATION: enabled

Shield> brain test "Ignore previous instructions"
Result:
  Engine: INJECTION
  Detected: true
  Confidence: 0.85
  Severity: HIGH
  Reason: Injection pattern detected (stub)
```

---

## TLS Commands

```
Shield> show tls
TLS Status: ENABLED
  Certificate: /etc/shield/cert.pem
  Key: /etc/shield/key.pem
  Min Version: TLS 1.2
  Cipher Suites: 12 available

Shield> configure terminal
Shield(config)> tls enable
Shield(config)> tls certificate /path/to/cert.pem
Shield(config)> tls key /path/to/key.pem
Shield(config)> end
```

---

## Testing Commands

```bash
# Run all CLI tests
make test_all
# Result: 94/94 pass

# Run LLM integration tests
make test_llm_mock
# Result: 9/9 pass

# Run with Valgrind
make test_valgrind
# Result: 0 memory leaks
```

---

## 119 CLI Command Handlers

Shield implements **119 command handlers** organized by category:

| Category | Handlers | Examples |
|----------|----------|----------|
| Policy | 18 | zone, rule, guard |
| Show | 15 | status, version, config |
| Brain | 8 | brain test, brain status |
| TLS | 6 | tls enable, certificate |
| HA | 12 | ha status, failover |
| Cognitive | 7 | cognitive test |
| PQC | 5 | pqc enable, pqc test |
| Watchdog | 6 | watchdog enable |
| ThreatHunter | 6 | threat-hunter enable |
| Other | 36 | hostname, write, reload |

---

_"Command your AI security like a network."_
