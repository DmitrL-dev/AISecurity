# SENTINEL Academy — Exam Bank

## Practice Questions

---

## SSA Level

### Module 0-1: Concepts

1. What is prompt injection?
   - A) SQL injection for LLMs
   - B) Malicious instructions in prompts ✓
   - C) Memory corruption
   - D) Buffer overflow

2. What is the main difference between AI and traditional software security?
   - A) AI uses more memory
   - B) AI takes natural language input ✓
   - C) AI is faster
   - D) AI is slower

3. What is jailbreaking?
   - A) Breaking out of containers
   - B) Bypassing safety restrictions ✓
   - C) Stealing API keys
   - D) DDoS attack

### Module 2-3: Architecture

4. How many layers does Shield have?
   - A) 4
   - B) 6
   - C) 8 ✓
   - D) 10

5. What language is Shield written in?
   - A) Python
   - B) Rust
   - C) Go
   - D) C ✓

6. How many guards does Shield have?
   - A) 4
   - B) 6 ✓
   - C) 8
   - D) 10

### Module 4-5: Rules

7. What is the default rule action if no match?
   - A) Allow
   - B) Deny ✓
   - C) Log
   - D) Alert

8. Rules are evaluated in what order?
   - A) Alphabetical
   - B) Random
   - C) Sequence number ✓
   - D) Priority

---

## SSP Level

### Module 6: Guards

9. Which guard protects RAG systems?
   - A) LLM Guard
   - B) RAG Guard ✓
   - C) Agent Guard
   - D) API Guard

10. What does Agent Guard check?
    - A) API rate limits
    - B) Loop and privilege ✓
    - C) SQL injection
    - D) XSS

### Module 7: Protocols

11. How many protocols does Shield have?
    - A) 6
    - B) 10
    - C) 20 ✓
    - D) 30

12. Which protocol handles HA?
    - A) STP
    - B) SHSP ✓
    - C) SBP
    - D) SAF

### Module 8-9: HA & Monitoring

13. What triggers automatic failover?
    - A) Manual command
    - B) Heartbeat timeout ✓
    - C) High CPU
    - D) Low memory

14. Default metrics port?
    - A) 8080
    - B) 9090 ✓
    - C) 443
    - D) 80

---

## SSE Level

### Module 11-14: Advanced

15. What is memory pool advantage?
    - A) More memory
    - B) O(1) allocation ✓
    - C) Compression
    - D) Encryption

16. Guard interface requires which functions?
    - A) init only
    - B) init, check, destroy ✓
    - C) start, stop
    - D) run, halt

17. What is target P99 latency?
    - A) 10ms
    - B) 5ms
    - C) 1ms ✓
    - D) 100ms

---

## Phase 4: ThreatHunter, Watchdog, Cognitive, PQC

### ThreatHunter

18. What three hunting modes does ThreatHunter support?
    - A) Pattern, Regex, Literal
    - B) IOC, Behavioral, Anomaly ✓
    - C) Fast, Medium, Deep
    - D) Active, Passive, Hybrid

19. What does BEHAVIOR_RECON detect?
    - A) Data exfiltration
    - B) Reconnaissance activity ✓
    - C) Privilege escalation
    - D) Persistence mechanisms

### Watchdog

20. What does Watchdog auto-recovery do?
    - A) Restart the system
    - B) Automatically restore failed components ✓
    - C) Send notifications only
    - D) Create backups

21. How many alert escalation levels?
    - A) 2
    - B) 3
    - C) 4 ✓
    - D) 5

### Cognitive Signatures

22. How many cognitive signature types in Shield?
    - A) 5
    - B) 6
    - C) 7 ✓
    - D) 8

23. What does AUTHORITY_CLAIM detect?
    - A) False authority claims ✓
    - B) Context injection
    - C) Emotional pressure
    - D) Logic break

### Post-Quantum Cryptography

24. Which algorithm is used for key exchange in PQC?
    - A) RSA
    - B) Kyber ✓
    - C) ECC
    - D) DH

25. What security level is Kyber-1024?
    - A) NIST Level 1
    - B) NIST Level 3
    - C) NIST Level 5 ✓
    - D) NIST Level 7

### Shield State & CLI

26. How many CLI commands are in Shield?
    - A) 50
    - B) 100
    - C) 199 ✓
    - D) 300

27. What command saves configuration?
    - A) save config
    - B) write memory ✓
    - C) config save
    - D) store settings

---

## Answers Quick Reference

| Q | A | Q | A | Q | A |
|---|---|---|---|---|---|
| 1 | B | 7 | B | 13 | B |
| 2 | B | 8 | C | 14 | B |
| 3 | B | 9 | B | 15 | B |
| 4 | C | 10 | B | 16 | B |
| 5 | D | 11 | C | 17 | C |
| 6 | B | 12 | B | | |

---

_"Practice makes perfect."_
