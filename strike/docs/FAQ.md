# ❓ FAQ

> **Frequently Asked Questions about SENTINEL Strike**

---

## General

### What is SENTINEL Strike?

SENTINEL Strike is a red team testing platform for AI applications and web services. It's the "offensive" part of the SENTINEL AI Security Platform.

---

### Is this legal?

**Yes, under these conditions:**

✅ Testing your own systems  
✅ Testing with written permission  
✅ Bug bounty programs (within scope)

❌ Attacking systems without permission  
❌ Malicious use

---

### Is it free?

**SENTINEL Strike Community Edition is free** for:

- Personal use
- Educational purposes
- Non-commercial projects

For commercial use — contact for licensing.

---

## Technical

### Which AI models are supported for planning?

| Model          | Status | Note                   |
| -------------- | ------ | ---------------------- |
| Gemini 3 Flash | ✅     | Recommended            |
| GPT-4          | ✅     | Via API                |
| Claude 3       | ✅     | Via API                |
| Ollama (local) | ✅     | For air-gapped         |
| OpenRouter     | ✅     | Proxy for various LLMs |

---

### Do I need an API key?

**No, Strike works without API keys.** Keys are optional:

- **Without keys:** Basic functionality
- **With Gemini:** AI attack planning
- **With ScraperAPI:** Residential proxy

---

### What attacks are supported?

**Web (12 types):**
SQLi, XSS, CMDi, SSTI, NoSQL, LFI, SSRF, XXE, Dir Enum, Auth Bypass, IDOR, JWT

**LLM (30+ types):**
Jailbreak, DAN, Roleplay, Crescendo, Direct/Indirect Injection, System Prompt Extract, MCP Tool Inject, RAG Poison, and many more.

---

### How long does a scan take?

| Mode                       | ~Time     | Requests |
| -------------------------- | --------- | -------- |
| Quick (--max-payloads 100) | 2-5 min   | ~100     |
| Standard                   | 15-30 min | ~1000    |
| Full                       | 1-2 hours | ~10000   |
| Deep Recon + Full          | 3-5 hours | ~50000   |

---

### How to avoid being blocked?

1. **Enable Stealth Mode:**

   ```bash
   python -m strike -t URL --stealth
   ```

2. **Increase delay:**

   ```bash
   --delay 2000 --jitter 50
   ```

3. **Use Geo Rotation:**

   ```bash
   --geo DE
   ```

4. **Change Browser Profile:**
   ```bash
   --browser safari17
   ```

---

### Can I use custom payloads?

**Yes:**

```bash
python -m strike -t URL --payload-file my_payloads.txt
```

Format: one payload per line.

---

### Does it work air-gapped?

**Yes:**

1. Use Ollama for local AI
2. Disable auto-update: `--no-update`
3. Pre-load payload database

---

## Reports

### What report formats available?

| Format   | Extension | Use Case            |
| -------- | --------- | ------------------- |
| Markdown | .md       | Docs, GitHub        |
| HTML     | .html     | Presentations       |
| JSON     | .json     | Automation, CI/CD   |
| MITRE    | —         | Added to any format |

---

### How to read the report?

**Structure:**

1. **Summary** — overall stats
2. **Critical Findings** — critical vulnerabilities
3. **High/Medium/Low** — by severity
4. **Technical Details** — payloads and responses
5. **Recommendations** — how to fix

---

### CI/CD integration?

See [Integration Examples](./INTEGRATION.md#github-actions)

---

## Comparison

### Strike vs Lakera Red?

|                 | Strike          | Lakera Red |
| --------------- | --------------- | ---------- |
| **Open Source** | ✅              | ❌         |
| **Self-hosted** | ✅              | ❌         |
| **Web + LLM**   | ✅              | LLM only   |
| **Payloads**    | 39K+            | ~10K       |
| **Price**       | Free/Enterprise | SaaS only  |

---

### Strike vs Garak?

|                        | Strike         | Garak    |
| ---------------------- | -------------- | -------- |
| **UI**                 | ✅ Web Console | CLI only |
| **Web attacks**        | ✅             | ❌       |
| **Stealth**            | ✅             | ❌       |
| **Active development** | ✅             | ✅       |

---

## Contact

📧 **Email:** chg@live.ru  
💬 **Telegram:** [@DmLabincev](https://t.me/DmLabincev)  
🌐 **GitHub:** [DmitrL-dev/AISecurity](https://github.com/DmitrL-dev/AISecurity)

---

_SENTINEL Strike v3.0 — Test your AI before attackers do!_
