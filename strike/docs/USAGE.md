# 📖 SENTINEL Strike — User Guide

> **Complete documentation for the AI red teaming platform**

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [API Key Configuration](#api-key-configuration)
4. [Dashboard Interface](#dashboard-interface)
5. [Attack Modes](#attack-modes)
6. [Web Attack Vectors](#web-attack-vectors)
7. [LLM Attack Vectors](#llm-attack-vectors)
8. [Stealth Settings](#stealth-settings)
9. [Recommendations](#recommendations)

---

## Overview

SENTINEL Strike is a platform for testing the security of AI applications and web services.

**Features:**

- 🎯 **39,000+ Payloads** — SQLi, XSS, Jailbreak, Prompt Injection
- 🐉 **HYDRA Architecture** — 9 parallel attack heads
- 🤖 **AI Integration** — Gemini, OpenAI, Anthropic for planning
- 🛡️ **WAF Bypass** — 25+ evasion techniques
- 📊 **Reports** — HTML, Markdown, JSON, MITRE ATT&CK

---

## Quick Start

### Launch Web Console

```bash
cd strike/dashboard
python strike_console.py
```

Open in browser: **http://localhost:5000**

### Launch CLI

```bash
cd strike
python -m strike --target https://example.com/chat
```

---

## API Key Configuration

### Method 1: Environment Variables (Recommended)

**Windows PowerShell:**

```powershell
$env:GEMINI_API_KEY = "your-gemini-key"
$env:OPENAI_API_KEY = "your-openai-key"
$env:SCRAPERAPI_KEY = "your-scraperapi-key"
```

**Windows CMD:**

```cmd
set GEMINI_API_KEY=your-gemini-key
set OPENAI_API_KEY=your-openai-key
set SCRAPERAPI_KEY=your-scraperapi-key
```

**Linux/macOS:**

```bash
export GEMINI_API_KEY="your-gemini-key"
export OPENAI_API_KEY="your-openai-key"
export SCRAPERAPI_KEY="your-scraperapi-key"
```

### Method 2: Web Interface

1. Open dashboard: http://localhost:5000
2. Go to **⚙️ Settings** section (right panel)
3. Find fields:
   - **Gemini API Key** — for AI attack planning
   - **ScraperAPI Key** — for residential proxies
4. Enter keys and click **Save**

### Method 3: Configuration File

Create `strike/config.yaml`:

```yaml
api:
  gemini_key: "your-key"
  openai_key: "your-key"
  scraperapi_key: "your-key"

defaults:
  timeout: 30
  max_concurrent: 9
  stealth_mode: true
```

### Getting API Keys

| Service        | URL                                    | Purpose             |
| -------------- | -------------------------------------- | ------------------- |
| **Gemini**     | https://aistudio.google.com/app/apikey | AI attack planning  |
| **OpenAI**     | https://platform.openai.com/api-keys   | Alternative AI      |
| **ScraperAPI** | https://www.scraperapi.com             | Residential proxies |

---

## Dashboard Interface

### Left Panel — Attack Configuration

#### Target URL

Field for entering the target URL.

```
https://api.example.com/chat
```

**Buttons below field:**

- **🔍 Scan** — launch Deep Recon (endpoint discovery)
- **📂 Load Cache** — load previously saved recon results

#### ☐ Scan IP Range

When enabled, scans the entire IP range (ASN) of the target domain.

⚠️ **Warning:** significantly increases scan time!

#### Attack Mode

Select attack type:

| Mode          | Description                                               |
| ------------- | --------------------------------------------------------- |
| **🌐 Web**    | Classic web vulnerabilities (SQLi, XSS, LFI)              |
| **🤖 LLM/AI** | Attacks on LLM applications (Jailbreak, Prompt Injection) |
| **⚡ Hybrid** | Combined attacks (Web + LLM)                              |

---

### Center Panel — Console

Displays real-time attack execution log:

| Color     | Message Type         |
| --------- | -------------------- |
| 🔵 Blue   | Informational        |
| 🟢 Green  | Successful operation |
| 🟡 Yellow | Warning              |
| 🔴 Red    | Error                |
| 💜 Purple | Bypass detected!     |
| 🩵 Cyan    | Stealth operation    |

---

### Right Panel — Stats & Findings

#### Statistics

- **Requests** — requests sent
- **Bypasses** — successful bypasses
- **Success Rate** — success percentage
- **Avg Response Time** — average response time

#### Findings

List of discovered vulnerabilities with severity level:

- 🔴 **Critical** — immediate fix required
- 🟠 **High** — high priority
- 🔵 **Medium** — medium priority

---

## Attack Modes

### 🌐 Web Mode

Classic web attacks for testing traditional web applications.

### 🤖 LLM/AI Mode

Specialized attacks for AI/LLM applications:

- Chatbots
- AI assistants
- RAG systems
- Agentic systems

### ⚡ Hybrid Mode

Combination of Web and LLM attacks. Recommended for:

- APIs with AI components
- Web applications with integrated AI
- Comprehensive audits

---

## Web Attack Vectors

### 💉 Injection

| Vector    | Description                                   |
| --------- | --------------------------------------------- |
| **SQLi**  | SQL Injection (UNION, Blind, Error-based)     |
| **XSS**   | Cross-Site Scripting (Reflected, Stored, DOM) |
| **CMDi**  | Command Injection (OS command execution)      |
| **SSTI**  | Server-Side Template Injection                |
| **NoSQL** | NoSQL Injection (MongoDB, CouchDB)            |

### 📂 File/Path

| Vector   | Description                                 |
| -------- | ------------------------------------------- |
| **LFI**  | Local File Inclusion (/etc/passwd, win.ini) |
| **SSRF** | Server-Side Request Forgery                 |
| **XXE**  | XML External Entity Injection               |

### 🔍 Enumeration

| Vector        | Description            |
| ------------- | ---------------------- |
| **Dir Enum**  | Directory enumeration  |
| **Subdomain** | Subdomain discovery    |
| **Endpoints** | API endpoint discovery |

### 🔓 Auth/Access

| Vector          | Description                                 |
| --------------- | ------------------------------------------- |
| **Auth Bypass** | Authentication bypass                       |
| **IDOR**        | Insecure Direct Object Reference            |
| **JWT**         | JWT vulnerabilities (none alg, weak secret) |

---

## LLM Attack Vectors

### 🔓 Jailbreak

| Vector        | Description                                 |
| ------------- | ------------------------------------------- |
| **Jailbreak** | Classic jailbreak prompts (DAN, Evil, etc.) |
| **DAN Mode**  | "Do Anything Now" mode                      |
| **Roleplay**  | Role-playing scenarios for bypass           |
| **Crescendo** | Gradual escalation of requests              |

### 💉 Injection

| Vector             | Description                      |
| ------------------ | -------------------------------- |
| **Direct**         | Direct prompt injections         |
| **Indirect (RAG)** | Injections through RAG documents |
| **Encoding**       | Base64, Hex, ROT13 encoding      |
| **Unicode**        | Unicode obfuscation              |

### 🔍 Exfiltration

| Vector            | Description                      |
| ----------------- | -------------------------------- |
| **System Prompt** | System prompt extraction         |
| **PII Extract**   | Personal data extraction         |
| **Training Data** | Attempt to extract training data |

### 🤖 Agentic

| Vector              | Description                 |
| ------------------- | --------------------------- |
| **MCP Tool Inject** | MCP tool injection          |
| **A2A Poison**      | Agent-to-Agent poisoning    |
| **RAG Poison**      | RAG context poisoning       |
| **Capability Esc**  | Agent capability escalation |

### 🔢 Strange Math

| Vector            | Description               |
| ----------------- | ------------------------- |
| **TDA Bypass**    | TDA detector bypass       |
| **Sheaf Confuse** | Sheaf-confusion attacks   |
| **Chaos Trigger** | Chaotic behavior triggers |

### 🎭 Doublespeak

| Vector            | Description        |
| ----------------- | ------------------ |
| **Doublespeak**   | Ambiguous requests |
| **Semantic Trap** | Semantic traps     |

### 🖼️ VLM / Multimodal

| Vector              | Description            |
| ------------------- | ---------------------- |
| **Visual Inject**   | Image-based injections |
| **Cross-Modal**     | Cross-modal attacks    |
| **Adversarial Img** | Adversarial images     |

### 🔗 Protocol

| Vector           | Description          |
| ---------------- | -------------------- |
| **MCP Protocol** | MCP protocol attacks |
| **A2A Protocol** | A2A protocol attacks |
| **Agent Card**   | Agent Card spoofing  |

### ☠️ Data Poisoning

| Vector            | Description         |
| ----------------- | ------------------- |
| **Bootstrap**     | Bootstrap poisoning |
| **Temporal**      | Temporal poisoning  |
| **Synthetic Mem** | Synthetic memory    |

### 🧠 Deep Learning

| Vector           | Description               |
| ---------------- | ------------------------- |
| **Activation**   | Activation attacks        |
| **Hidden State** | Hidden state manipulation |
| **Gradient**     | Gradient-based attacks    |

---

## Stealth Settings

### 🌍 Geo Rotation

Select country for IP rotation via ScraperAPI:

| Flag | Country        | Code |
| ---- | -------------- | ---- |
| 🇺🇸   | USA            | US   |
| 🇬🇧   | United Kingdom | UK   |
| 🇩🇪   | Germany        | DE   |
| 🇫🇷   | France         | FR   |
| 🇯🇵   | Japan          | JP   |
| 🇦🇺   | Australia      | AU   |
| 🇨🇦   | Canada         | CA   |
| 🇳🇱   | Netherlands    | NL   |
| 🇸🇬   | Singapore      | SG   |
| 🇧🇷   | Brazil         | BR   |

### 🌐 Browser Profile

User browser emulation:

| Profile         | User-Agent              |
| --------------- | ----------------------- |
| **Chrome 120**  | Latest Chrome (Windows) |
| **Firefox 121** | Latest Firefox          |
| **Safari 17**   | Safari macOS            |
| **Edge 120**    | Microsoft Edge          |
| **Mobile**      | Chrome Mobile Android   |

### ⏱️ Timing

| Setting    | Description                 |
| ---------- | --------------------------- |
| **Delay**  | Delay between requests (ms) |
| **Jitter** | Random deviation (%)        |
| **Burst**  | Request batch size          |

---

## Recommendations

### ✅ Best Practices

1. **Start with Recon**

   - Always use 🔍 Scan before attacking
   - This discovers hidden endpoints

2. **Use Stealth Mode**

   - Enable Geo Rotation
   - Select Browser Profile
   - Set reasonable Delay (500-2000 ms)

3. **Gradual Escalation**

   - Start with few vectors
   - Add more as bypasses are discovered

4. **Save Results**
   - Export reports regularly
   - Use Load Cache to continue

### ⚠️ Warnings

1. **Authorization Only!**

   - Test only your own systems
   - Or with written permission

2. **Don't Use on Production**

   - Staging/test environments only
   - Risk of service disruption

3. **Comply with Laws**
   - CFAA (USA), Computer Misuse Act (UK)
   - Local legislation

### 📊 Interpreting Results

| Metric                | Good    | Bad      |
| --------------------- | ------- | -------- |
| **Bypass Rate**       | < 5%    | > 20%    |
| **Response Time**     | < 500ms | > 5000ms |
| **Critical Findings** | 0       | > 0      |

---

## Support

📧 **Email:** chg@live.ru  
💬 **Telegram:** [@DmLabincev](https://t.me/DmLabincev)  
🌐 **GitHub:** [DmitrL-dev/AISecurity](https://github.com/DmitrL-dev/AISecurity)

---

_SENTINEL Strike v3.0 — Test your AI before attackers do!_
