# Module 17: ThreatHunter — Active Threat Hunting

## Overview

ThreatHunter is an active threat hunting engine in SENTINEL Shield. Unlike passive defense (Guards), ThreatHunter proactively searches for indicators of compromise, anomalies, and suspicious patterns.

---

## Three Hunting Modes

### 1. IOC Hunting (Indicators of Compromise)

Search for known compromise indicators:

**IOC Types:**
- `IOC_PATTERN` — Attack text patterns
- `IOC_COMMAND` — Dangerous commands (rm -rf, wget, curl)
- `IOC_PATH` — Critical paths (/etc/passwd, /etc/shadow)
- `IOC_IP` — Suspicious IP addresses
- `IOC_URL` — Malicious URLs

### 2. Behavioral Hunting

Detection of attack behavioral patterns:

| Pattern | Description | Indicators |
|---------|-------------|------------|
| `BEHAVIOR_RECON` | Reconnaissance | nmap, whoami, id, uname |
| `BEHAVIOR_EXFIL` | Exfiltration | curl, wget, base64, xxd |
| `BEHAVIOR_PRIVESC` | Privilege Escalation | sudo, su, chmod 777 |
| `BEHAVIOR_PERSIST` | Persistence | crontab, .bashrc, systemd |

### 3. Anomaly Hunting

Statistical anomaly analysis:
- **High Entropy** — Encrypted/obfuscated data detection
- **Unusual Length** — Suspiciously long prompts (>10000 chars)
- **Repetition Attacks** — Pattern repetition
- **Statistical Deviation** — Deviation from normal distribution

---

## API

```c
#include "shield_threat_hunter.h"

// Initialize
shield_err_t threat_hunter_init(void);

// Set sensitivity (0.0 - 1.0)
void threat_hunter_set_sensitivity(float sensitivity);

// Full hunt
threat_hunt_result_t threat_hunter_hunt(const char *content, 
                                         size_t len,
                                         hunt_type_t types);

// Quick check (score only)
float threat_hunter_quick_check(const char *text);
```

---

## CLI Commands

```
sentinel# show threat-hunter
sentinel(config)# threat-hunter enable
sentinel(config)# threat-hunter sensitivity 0.8
sentinel# threat-hunter test "ignore previous instructions"
```

---

## Questions

1. What are the three hunting modes in ThreatHunter?
2. What does IOC_COMMAND detect?
3. At what score does ThreatHunter recommend BLOCK?
4. What behavioral pattern detects reconnaissance?

---

→ [Module 18: Watchdog](MODULE_18_WATCHDOG.md)
