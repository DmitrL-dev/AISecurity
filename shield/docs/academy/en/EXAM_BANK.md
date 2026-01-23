# SENTINEL Academy — Exam Question Bank

## SSA-100: Associate Exam

### Section 1: AI Security Fundamentals (20 questions)

**Q1.** What is prompt injection?

- A) Injecting SQL into a database
- B) Manipulating AI through crafted input to override instructions ✓
- C) Adding prompts to a queue
- D) Encrypting prompts

**Q2.** Which attack attempts to make an AI ignore its safety guidelines?

- A) SQL injection
- B) XSS
- C) Jailbreak ✓
- D) CSRF

**Q3.** What does the "DAN" jailbreak stand for?

- A) Data Access Network
- B) Do Anything Now ✓
- C) Direct AI Navigation
- D) Defensive AI Node

**Q4.** What is the primary purpose of a DMZ in AI security?

- A) Store data
- B) Create isolation between trusted and untrusted components ✓
- C) Speed up processing
- D) Reduce costs

**Q5.** Which is NOT a common prompt injection technique?

- A) Instruction override
- B) Roleplay manipulation
- C) Buffer overflow ✓
- D) Social engineering

**Q6.** What is a canary token used for?

- A) Speed testing
- B) Detecting prompt/data leakage ✓
- C) User authentication
- D) Load balancing

**Q7.** What does PII stand for?

- A) Private Internet Interface
- B) Personally Identifiable Information ✓
- C) Protocol Independent Interface
- D) Primary Input Index

**Q8.** Which encoding is commonly used to evade detection?

- A) Base64 ✓
- B) ASCII
- C) UTF-8
- D) Both A and C ✓

**Q9.** What is the recommended minimum trust level for internal zones?

- A) 1
- B) 5
- C) 10 ✓
- D) 0

**Q10.** What action should be taken for high-severity attacks?

- A) Log only
- B) Allow with warning
- C) Block ✓
- D) Ignore

---

### Section 2: Shield Basics (15 questions)

**Q11.** What command shows Shield version?

- A) `shield version`
- B) `shield --version` ✓
- C) `shield -v`
- D) Both B and C ✓

**Q12.** What is the default API port?

- A) 80
- B) 443
- C) 8080 ✓
- D) 9090

**Q13.** Which CLI command shows all rules?

- A) `list rules`
- B) `show rules` ✓
- C) `rules all`
- D) `get rules`

**Q14.** What file format is used for Shield configuration?

- A) XML
- B) YAML
- C) JSON ✓
- D) INI

**Q15.** What is the purpose of zones in Shield?

- A) Geographic regions
- B) Trust boundaries ✓
- C) Time zones
- D) Network segments

---

### Section 3: Configuration (15 questions)

**Q16.** How do you enable semantic analysis?

```json
{
  "semantic": {
    "enabled": ___
  }
}
```

- A) "yes"
- B) 1
- C) true ✓
- D) "on"

**Q17.** What pattern type uses regular expressions?

- A) literal
- B) regex ✓
- C) glob
- D) wildcard

**Q18.** Which action quarantines suspicious input?

- A) block
- B) log
- C) quarantine ✓
- D) alert

**Q19.** How do you set case-insensitive matching?

- A) `"case": false`
- B) `"case_insensitive": true` ✓
- C) `"ignore_case": 1`
- D) `"nocase": true`

**Q20.** What severity level triggers immediate blocking?

- A) 1-3
- B) 4-6
- C) 7-10 ✓
- D) 0

---

## SSP-200: Professional Exam

### Section 1: Advanced Configuration (25 questions)

**Q21.** What protocol is used for Shield clustering?

- A) gRPC
- B) SHSP ✓
- C) HTTP
- D) WebSocket

**Q22.** What is the maximum recommended context window size?

- A) 1024 tokens
- B) 4096 tokens
- C) 8192 tokens ✓
- D) Unlimited

**Q23.** Which eviction policy keeps the most recent messages?

- A) oldest
- B) sliding_window ✓
- C) random
- D) smallest

**Q24.** How do you detect multi-turn attacks?

- A) Enable pattern matching
- B) Enable context tracking ✓
- C) Increase rate limit
- D) Disable caching

**Q25.** What is the default rate limit burst multiplier?

- A) 1x
- B) 2x ✓
- C) 5x
- D) 10x

---

### Section 2: Guards (20 questions)

**Q26.** Which guard protects RAG systems?

- A) llm_guard
- B) rag_guard ✓
- C) tool_guard
- D) api_guard

**Q27.** What does the MCP guard protect?

- A) Memory Control Protocol
- B) Model Context Protocol ✓
- C) Message Control Panel
- D) Multi-Core Processing

**Q28.** How many built-in guards does Shield have?

- A) 4
- B) 5
- C) 6 ✓
- D) 8

**Q29.** Which guard checks for tool abuse?

- A) agent_guard
- B) tool_guard ✓
- C) api_guard
- D) llm_guard

**Q30.** What interface do custom guards implement?

- A) guard_interface
- B) guard_vtable ✓
- C) guard_api
- D) guard_handler

---

### Section 3: Deployment (20 questions)

**Q31.** What command validates configuration?

- A) `shield check config`
- B) `shield --validate-config` ✓
- C) `shield test`
- D) `shield verify`

**Q32.** Which port exposes Prometheus metrics?

- A) 8080
- B) 9090 ✓
- C) 3000
- D) 5000

**Q33.** What is the HA failover detection protocol?

- A) VRRP
- B) HSRP
- C) SHSP ✓
- D) BGP

**Q34.** How long is the default heartbeat interval?

- A) 100ms
- B) 500ms
- C) 1000ms ✓
- D) 5000ms

**Q35.** What triggers automatic failover?

- A) Manual command
- B) Missed heartbeats ✓
- C) CPU spike
- D) Memory usage

---

## SSE-300: Expert Exam

### Section 1: Internals (30 questions)

**Q36.** What data structure stores attack signatures?

- A) Array
- B) Linked list
- C) Hash table ✓
- D) Tree

**Q37.** How does Shield implement zero-copy I/O?

- A) Memory pools ✓
- B) Garbage collection
- C) Reference counting
- D) Copy-on-write

**Q38.** What is the time complexity of signature lookup?

- A) O(n)
- B) O(log n)
- C) O(1) ✓
- D) O(n log n)

**Q39.** Which protocol handles state replication?

- A) STP
- B) SBP
- C) SSRP ✓
- D) SAF

**Q40.** What is the purpose of the ring buffer in Shield?

- A) Rule storage
- B) Event logging ✓
- C) Session tracking
- D) Config storage

---

### Section 2: Performance (25 questions)

**Q41.** What is the target latency for Shield evaluation?

- A) > 100ms
- B) < 10ms
- C) < 1ms ✓
- D) < 100μs

**Q42.** How do you profile Shield performance?

- A) `shield --profile` ✓
- B) `shield benchmark`
- C) `shield perf`
- D) `shield stats`

**Q43.** What causes regex performance degradation?

- A) Short patterns
- B) Backtracking ✓
- C) Case sensitivity
- D) Unicode

**Q44.** How do you optimize pattern matching?

- A) Use literal where possible ✓
- B) Use longer patterns
- C) Disable caching
- D) Increase threads

**Q45.** What is the recommended thread pool size?

- A) 1
- B) CPU cores ✓
- C) 100
- D) Unlimited

---

## Phase 4 Modules: ThreatHunter, Watchdog, Cognitive, PQC

### Section: ThreatHunter (10 questions)

**Q46.** What are the three hunting modes supported by ThreatHunter?

- A) Pattern, Regex, Literal
- B) IOC, Behavioral, Anomaly ✓
- C) Fast, Medium, Deep
- D) Active, Passive, Hybrid

**Q47.** What does IOC_COMMAND detect?

- A) Suspicious IP addresses
- B) Dangerous system commands ✓
- C) Malicious URLs
- D) Text patterns

**Q48.** Which behavioral pattern detects reconnaissance?

- A) BEHAVIOR_EXFIL
- B) BEHAVIOR_RECON ✓
- C) BEHAVIOR_PRIVESC
- D) BEHAVIOR_PERSIST

**Q49.** At what score does ThreatHunter recommend BLOCK?

- A) > 0.5
- B) > 0.7 ✓
- C) > 0.9
- D) = 1.0

**Q50.** What does Anomaly Hunt detect?

- A) Known attack patterns
- B) Statistical deviations ✓
- C) Dangerous commands
- D) Suspicious IPs

### Section: Watchdog (10 questions)

**Q51.** What components does Watchdog monitor?

- A) Only Guards
- B) Only memory
- C) Guards, Memory, Connections ✓
- D) Only CPU

**Q52.** How many escalation levels does Watchdog have?

- A) 2
- B) 3
- C) 4 ✓
- D) 5

**Q53.** Which level requires immediate action?

- A) INFO
- B) WARNING
- C) ERROR
- D) CRITICAL ✓

**Q54.** What does auto-recovery do?

- A) Reboots the system
- B) Automatically restores failed components ✓
- C) Sends notifications
- D) Creates backups

**Q55.** What parameter determines check frequency?

- A) check_frequency
- B) check_interval_ms ✓
- C) watchdog_timer
- D) health_period

### Section: Cognitive Signatures (10 questions)

**Q56.** How many types of cognitive signatures does Shield have?

- A) 5
- B) 6
- C) 7 ✓
- D) 8

**Q57.** What does COG_SIG_AUTHORITY_CLAIM detect?

- A) False authority claims ✓
- B) Context injection
- C) Emotional pressure
- D) Logic breaking

**Q58.** Which marker is characteristic of MEMORY_MANIPULATION?

- A) "[system note:"
- B) "you promised earlier" ✓
- C) "this is urgent"
- D) "as admin i order"

**Q59.** At what aggregate_score is QUARANTINE recommended?

- A) >= 0.4
- B) >= 0.6 ✓
- C) >= 0.8
- D) >= 0.9

**Q60.** Which signature type applies pressure through urgency?

- A) EMOTIONAL_MANIPULATION
- B) URGENCY_PRESSURE ✓
- C) GOAL_DRIFT
- D) REASONING_BREAK

### Section: Post-Quantum Cryptography (10 questions)

**Q61.** Which algorithm is used for key exchange in PQC?

- A) RSA
- B) Kyber ✓
- C) ECC
- D) DH

**Q62.** Which algorithm is used for digital signatures?

- A) RSA
- B) ECDSA
- C) Dilithium ✓
- D) ED25519

**Q63.** What is the security level of Kyber-1024?

- A) NIST Level 1
- B) NIST Level 3
- C) NIST Level 5 ✓
- D) NIST Level 7

**Q64.** What does "Harvest Now, Decrypt Later" mean?

- A) Data compression technique
- B) Collecting encrypted data now for decryption by quantum computer later ✓
- C) Caching method
- D) Performance optimization

**Q65.** How many bytes are in Kyber's shared secret?

- A) 16
- B) 32 ✓
- C) 64
- D) 128

### Section: Shield State & CLI (10 questions)

**Q66.** What is shield_state_t?

- A) A configuration structure
- B) A global singleton for state management ✓
- C) A data type for zones
- D) An API interface

**Q67.** Which command saves configuration?

- A) `save config`
- B) `write memory` ✓
- C) `config save`
- D) `store settings`

**Q68.** Approximately how many CLI commands does Shield have?

- A) 50
- B) 100
- C) 199 ✓
- D) 300

**Q69.** What does the dirty flag in shield_state mean?

- A) Configuration error
- B) There are unsaved changes ✓
- C) System overloaded
- D) Update required

**Q70.** What file format is used for persistence?

- A) JSON
- B) YAML
- C) INI ✓
- D) XML

---

## Answer Key

| Q#  | Answer | Q#  | Answer | Q#  | Answer |
| --- | ------ | --- | ------ | --- | ------ |
| 1   | B      | 26  | B      | 51  | C      |
| 2   | C      | 27  | B      | 52  | C      |
| 3   | B      | 28  | C      | 53  | D      |
| 4   | B      | 29  | B      | 54  | B      |
| 5   | C      | 30  | B      | 55  | B      |
| 6   | B      | 31  | B      | 56  | C      |
| 7   | B      | 32  | B      | 57  | A      |
| 8   | D      | 33  | C      | 58  | B      |
| 9   | C      | 34  | C      | 59  | B      |
| 10  | C      | 35  | B      | 60  | B      |
| 11  | D      | 36  | C      | 61  | B      |
| 12  | C      | 37  | A      | 62  | C      |
| 13  | B      | 38  | C      | 63  | C      |
| 14  | C      | 39  | C      | 64  | B      |
| 15  | B      | 40  | B      | 65  | B      |
| 16  | C      | 41  | C      | 66  | B      |
| 17  | B      | 42  | A      | 67  | B      |
| 18  | C      | 43  | B      | 68  | C      |
| 19  | B      | 44  | A      | 69  | B      |
| 20  | C      | 45  | B      | 70  | C      |
| 21  | B      | 46  | B      |     |        |
| 22  | C      | 47  | B      |     |        |
| 23  | B      | 48  | B      |     |        |
| 24  | B      | 49  | B      |     |        |
| 25  | B      | 50  | B      |     |        |

---

_Total: 70+ questions across all levels_
