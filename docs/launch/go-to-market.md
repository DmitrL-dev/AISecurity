# SENTINEL — Go-to-Market Launch Materials

## 1. Product Hunt Listing

### Tagline
**AdBlock for AI prompts — stop jailbreaks before they happen**

### Description
SENTINEL Guard is like an ad blocker, but for dangerous AI prompts. It sits between you and ChatGPT/Claude/Gemini, scanning every prompt for injection attacks, jailbreaks, and PII leaks in real-time.

**🛡️ What it does:**
- Scans every prompt before it reaches AI — in under 1ms
- Blocks prompt injection (Pliny, DAN, AIM, DevMode)
- Detects PII leaks (SSN, credit cards, passwords)
- Works on ChatGPT, Claude, Gemini, Perplexity
- Open-source, Rust-powered, 36 detection engines

**⚡ Why it's different:**
1. **Speed**: Sub-1ms latency. You won't even notice it's there
2. **Browser-native**: Chrome Extension — install and forget
3. **Open-source**: 100% transparent. No black boxes
4. **Free tier**: 10K scans/month free forever

**🔧 For developers:**
- Python SDK: `pip install sentinel-shield`
- REST API: `POST /analyze`
- FastAPI/LangChain/OpenAI middleware examples included

### Topics
AI, Security, Chrome Extensions, Developer Tools, Open Source

### Pricing
- Personal: Free (10K scans/mo)
- Developer: $29/mo (100K scans, API access)
- Team: $99/mo (1M scans, SSO, dashboard)
- Enterprise: Custom (on-prem, SLA)

---

## 2. Chrome Web Store Listing

### Title
SENTINEL Guard — AI Firewall for ChatGPT & Claude

### Short Description
Protect your AI conversations from prompt injection, jailbreaks, and PII leaks. Works on ChatGPT, Claude, Gemini.

### Detailed Description
SENTINEL Guard is an AI security firewall that runs as a Chrome extension. It scans your prompts in real-time before they reach AI services, protecting you from:

🛡️ **Prompt Injection Attacks**
Detects and blocks known jailbreak patterns (Pliny, DAN, AIM, DevMode) before they can bypass AI safety filters.

🔒 **PII Leaks** 
Warns you when your prompt contains sensitive information like social security numbers, credit card numbers, or passwords.

📊 **Threat Dashboard**
Track your security stats — total scans, blocked threats, and risk levels — right from the extension popup.

⚡ **Zero Latency**
Powered by 36 Rust detection engines with sub-1ms response time. You won't notice any delay.

🌐 **Multi-Platform**
Works on ChatGPT, Claude, Gemini, and Perplexity.

🔓 **Open Source**
100% transparent and auditable. See exactly what's being checked.

### Category
Productivity > Security

---

## 3. Hacker News — Show HN Post

### Title
Show HN: SENTINEL – Open-source AI firewall (AdBlock for prompts)

### Body
Hi HN,

I built SENTINEL — an open-source AI security firewall. Think of it as AdBlock for AI prompts.

**The problem**: Prompt injection attacks are getting more sophisticated. Jailbreaks like Pliny and DAN can bypass safety filters in seconds. And users accidentally paste SSNs and credit cards into ChatGPT every day.

**The solution**: SENTINEL sits between the user and the AI, scanning every prompt in real-time:

- 36 Rust-powered detection engines
- Sub-1ms latency (you won't notice it)
- Chrome extension for ChatGPT/Claude/Gemini
- Python SDK: `pip install sentinel-shield`
- REST API with 10K free scans/month

**Architecture**:
```
User prompt → SENTINEL (36 engines, <1ms) → Safe? → Forward to AI
                                            → Threat? → Block + notify
```

**What's different from Lakera/Rebuff**:
1. Open-source (Apache 2.0) — no black boxes
2. Rust-native — 10x faster than Python-based solutions  
3. Browser extension — protects end users, not just developers
4. 36 specialized engines vs. single-model approach

Tech stack: Rust core + Python Shield API + Chrome Extension (Manifest V3)

GitHub: https://github.com/anthropic-security/sentinel-community
Chrome: [Chrome Web Store link]
SDK: `pip install sentinel-shield`

Would love feedback on the detection engine architecture and the browser extension UX.

---

## 4. Twitter/X Launch Thread

### Thread (6 tweets)

**1/6** 🚀 Launching SENTINEL — an open-source AI firewall.

Think AdBlock, but for dangerous prompts.

It scans every ChatGPT/Claude/Gemini prompt for:
→ Prompt injection (Pliny, DAN)
→ Jailbreak attempts
→ PII leaks (SSN, credit cards)

In under 1ms. ⚡

**2/6** How it works:

Your prompt → SENTINEL (36 Rust engines) → Safe? ✅ Forward → Threat? ⛔ Block

No delay. No cloud dependency. Open source.

Tested against 10,000+ known jailbreak patterns.

**3/6** The Chrome Extension is the killer feature.

Install it once. It protects every AI conversation automatically.

→ ChatGPT ✓
→ Claude ✓
→ Gemini ✓
→ Perplexity ✓

No config needed. Just install and forget.

**4/6** For developers, there's a Python SDK:

```python
from sentinel_shield import Shield

shield = Shield(api_key="sk-...")
result = shield.scan("ignore previous instructions")
# result.verdict = "block" 🛡️
```

pip install sentinel-shield

**5/6** Why we built this open-source:

AI security shouldn't be a black box.
You should see every rule.
You should audit every engine.
You should run it on your own infra.

Apache 2.0. Forever.

**6/6** Try it:

🔗 GitHub: [link]
🧩 Chrome Extension: [link]
📦 pip install sentinel-shield

Free tier: 10K scans/month.

Star the repo if you believe AI security should be open ⭐

---

## 5. README Hero Section (for mono-repo root)

```markdown
<div align="center">

# 🛡️ SENTINEL

### Open-Source AI Security Firewall

**Protect AI conversations from prompt injection, jailbreaks, and PII leaks.**
**36 Rust-powered engines. Sub-1ms latency. Apache 2.0.**

[Chrome Extension](link) · [Python SDK](link) · [API Docs](link) · [Dashboard](link)

![GitHub stars](badge) ![License](badge) ![Tests](badge)

</div>
```
