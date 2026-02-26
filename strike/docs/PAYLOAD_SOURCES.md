# 📦 Payload Sources

> **Where SENTINEL Strike gets its attack payloads**

---

## Overview

SENTINEL Strike uses **39,000+ payloads** from 13 professional sources, automatically updated daily.

---

## Sources

### 1. SecLists

- **URL:** https://github.com/danielmiessler/SecLists
- **Payloads:** ~15,000
- **Types:** SQLi, XSS, LFI, passwords, fuzzing
- **License:** MIT

### 2. PayloadsAllTheThings

- **URL:** https://github.com/swisskyrepo/PayloadsAllTheThings
- **Payloads:** ~5,000
- **Types:** All web vectors + methodology
- **License:** MIT

### 3. Lakera Gandalf

- **URL:** https://gandalf.lakera.ai
- **Payloads:** ~1,000 (crowdsourced)
- **Types:** LLM jailbreaks
- **Source:** Community submissions

### 4. HackTricks

- **URL:** https://book.hacktricks.xyz
- **Payloads:** ~2,000
- **Types:** Pentesting techniques
- **License:** CC-BY-NC

### 5. OWASP Testing Guide

- **URL:** https://owasp.org/www-project-web-security-testing-guide/
- **Payloads:** ~500
- **Types:** Standardized test cases
- **License:** CC-BY-SA

### 6. Garak (NVIDIA)

- **URL:** https://github.com/NVIDIA/garak
- **Payloads:** ~800
- **Types:** LLM probes
- **License:** Apache 2.0

### 7. PromptInject

- **URL:** https://github.com/agencyenterprise/PromptInject
- **Payloads:** ~300
- **Types:** Prompt injection
- **License:** MIT

### 8. JailbreakBench

- **URL:** https://github.com/JailbreakBench
- **Payloads:** ~500
- **Types:** Academic jailbreaks
- **License:** Apache 2.0

### 9. HarmBench

- **URL:** https://github.com/centerforaisafety/HarmBench
- **Payloads:** ~400
- **Types:** Harmful content testing
- **License:** MIT

### 10. ArXiv 2024-2025 Papers

- **Sources:** PAIR, GCG, AutoDAN, TAP research
- **Payloads:** ~200
- **Types:** State-of-the-art attacks
- **Updated:** Weekly

### 11. WAF Bypass Database

- **URL:** Internal + community
- **Payloads:** ~3,000
- **Types:** Encoding, obfuscation, evasion
- **Updated:** Daily

### 12. Custom SENTINEL Research

- **Payloads:** ~2,000
- **Types:** Proprietary techniques
- **Source:** Internal R&D

### 13. Bug Bounty Reports

- **Sources:** HackerOne, Bugcrowd (public)
- **Payloads:** ~500
- **Types:** Real-world exploits
- **Updated:** Weekly

---

## Payload Categories

### Web Attack Vectors

| Category           | Count  | Sources                        |
| ------------------ | ------ | ------------------------------ |
| SQL Injection      | ~5,000 | SecLists, PayloadsAllTheThings |
| XSS                | ~4,000 | SecLists, HackTricks           |
| Command Injection  | ~1,000 | SecLists, OWASP                |
| SSTI               | ~500   | PayloadsAllTheThings           |
| LFI/Path Traversal | ~2,000 | SecLists                       |
| SSRF               | ~500   | HackTricks                     |
| XXE                | ~300   | OWASP                          |
| Auth Bypass        | ~1,000 | Custom                         |

### LLM Attack Vectors

| Category         | Count  | Sources                 |
| ---------------- | ------ | ----------------------- |
| Jailbreaks       | ~3,000 | Gandalf, JailbreakBench |
| DAN/Roleplay     | ~500   | Community               |
| Prompt Injection | ~1,000 | PromptInject, Garak     |
| Exfiltration     | ~300   | Custom                  |
| MCP/Protocol     | ~200   | ArXiv 2025              |
| RAG Poisoning    | ~200   | HarmBench               |

---

## Auto-Update

Strike automatically downloads fresh payloads:

```bash
# Manual update
python -m strike --update-payloads

# Check last update
python -m strike --payload-info
```

### Update Schedule

| Source     | Frequency |
| ---------- | --------- |
| SecLists   | Weekly    |
| Gandalf    | Daily     |
| ArXiv      | Weekly    |
| WAF Bypass | Daily     |
| Bug Bounty | Weekly    |

---

## Custom Payloads

### Add Your Own

```bash
# From file
python -m strike -t URL --payload-file my_payloads.txt

# Single payload
python -m strike -t URL --payload "your_custom_payload"
```

### Payload File Format

```text
# Comments start with #
' OR 1=1 --
<script>alert(1)</script>
{{7*7}}
```

---

## Statistics

```
Total Payloads: 39,247
Web Vectors: 14,300
LLM Vectors: 5,947
WAF Bypass: 19,000

Last Updated: 2025-12-24
```

---

_SENTINEL Strike v3.0_
